namespace {
struct ResumeQuotaFixture {
    fs::path base;
    modelnet::ModelCatalog host;
    modelnet::ModelCatalog receiver;
    modelnet::CatalogEntry entry;
    modelnet::VerifiedManifest manifest;
    std::vector<unsigned char> first;
    std::vector<modelnet::Digest48> proof;
    uint64_t size{0};

    explicit ResumeQuotaFixture(const fs::path& dir)
        : base(dir), host(dir / "host", 128 << 20), receiver(dir / "receiver", 128 << 20)
    {
        const uint64_t payload_size = 2 * modelnet::PIECE_SIZE + 7;
        const std::string header = "{\"t\":{\"dtype\":\"U8\",\"shape\":[" + std::to_string(payload_size) +
            "],\"data_offsets\":[0," + std::to_string(payload_size) + "]}}";
        std::vector<unsigned char> bytes(8 + header.size() + payload_size, 'x');
        WriteLE64(bytes.data(), header.size());
        std::memcpy(bytes.data() + 8, header.data(), header.size());
        const auto src = dir / "source";
        fs::create_directories(src);
        {
            std::ofstream out(src / "model.safetensors", std::ios::binary);
            out.write(reinterpret_cast<const char*>(bytes.data()), bytes.size());
            BOOST_REQUIRE(out.good());
        }
        std::string err;
        BOOST_REQUIRE_MESSAGE(host.ImportPath(fs::PathToString(src), true, entry, err), err);
        UniValue json;
        BOOST_REQUIRE(host.GetManifest(entry.model_id, json, err));
        BOOST_REQUIRE(modelnet::VerifyManifestAgainstRequest(json, entry.model_id, manifest, err));
        BOOST_REQUIRE(receiver.InstallFromManifest(json, err, false));
        BOOST_REQUIRE(host.GetVerifiedPiece(entry.artifact_id, 0, 0, first, proof, size, err));
        BOOST_REQUIRE(receiver.PutFetchedPiece(entry.artifact_id, 0, 0, first, proof, size,
                                               entry.core.files[0].pieces_root, err));
        receiver.BeginTransfer(entry.artifact_id);
        receiver.SetQuotaBytes(size);
    }
    void RestoreProof()
    {
        std::string err;
        BOOST_REQUIRE(receiver.Store().SavePieceProof(entry.artifact_id, 0, 0, size,
                                                      entry.core.files[0].pieces_root, proof, err));
    }
    fs::path PiecePath() const
    {
        return receiver.Store().Root() / "artifacts" / entry.artifact_id.Hex().c_str() / "0" / "0.piece";
    }
    fs::path ProofPath() const
    {
        return receiver.Store().Root() / "artifacts" / entry.artifact_id.Hex().c_str() / "0" / "0.proof.json";
    }
};
} // namespace

BOOST_AUTO_TEST_CASE(store_09_resume_quota_credits_verified_active_pieces)
{
    ResumeQuotaFixture f{m_path_root / "store-09"};
    std::string err;
    // The old full-size admission rejects this same fitting partial model.
    BOOST_CHECK(!f.receiver.EnforceQuota(f.size, err));
    BOOST_CHECK(err.find("quota") != std::string::npos);
    BOOST_REQUIRE_MESSAGE(f.receiver.EnforceDownloadQuota(f.manifest, err), err);
    BOOST_CHECK_EQUAL(f.receiver.Store().UsedBytes(), f.first.size());
    BOOST_REQUIRE(f.receiver.PinModel(f.entry.model_id, true, err));
    f.receiver.EndTransfer(f.entry.artifact_id);
    BOOST_CHECK(!f.receiver.EnforceDownloadQuota(f.manifest, err));
    f.receiver.BeginTransfer(f.entry.artifact_id);
    BOOST_REQUIRE(f.receiver.PinModel(f.entry.model_id, false, err));
    BOOST_REQUIRE(f.receiver.EnforceDownloadQuota(f.manifest, err));
    f.receiver.SetQuotaBytes(f.size - 1);
    BOOST_CHECK(!f.receiver.EnforceDownloadQuota(f.manifest, err));
    std::vector<unsigned char> kept;
    BOOST_REQUIRE(f.receiver.Store().GetPiece(f.entry.artifact_id, 0, 0, kept, err));
    BOOST_CHECK(kept == f.first);
    f.receiver.SetQuotaBytes(f.size);
    std::atomic<bool> stop{true};
    BOOST_CHECK(!f.receiver.EnforceDownloadQuota(f.manifest, err, &stop));
    BOOST_CHECK_EQUAL(err, "stopped");
    stop = false;
    BOOST_REQUIRE(f.receiver.EnforceDownloadQuota(f.manifest, err, &stop));
}

BOOST_AUTO_TEST_CASE(store_10_resume_quota_preserves_unrelated_models)
{
    ResumeQuotaFixture f{m_path_root / "store-10"};
    const auto pinned = ImportTiny(f.receiver, f.base / "pinned-source", 0xB1, true);
    const auto active = ImportTiny(f.receiver, f.base / "active-source", 0xB2, false);
    f.receiver.BeginTransfer(active.artifact_id);
    std::string err;
    // The target alone fits, but unrelated protected models still consume quota.
    BOOST_CHECK(!f.receiver.EnforceDownloadQuota(f.manifest, err));
    modelnet::CatalogEntry kept;
    BOOST_CHECK(f.receiver.Find(pinned.model_id, kept));
    BOOST_CHECK(f.receiver.Find(active.model_id, kept));
    BOOST_CHECK(f.receiver.TransferActive(active.model_id));
    BOOST_CHECK(f.receiver.Find(f.entry.model_id, kept));
    for (const auto& entry : {pinned, active}) {
        std::vector<unsigned char> bytes;
        BOOST_REQUIRE(f.receiver.Store().GetPiece(entry.artifact_id, 0, 0, bytes, err));
        BOOST_CHECK(bytes == TinySafeTensors(entry.model_id == pinned.model_id ? 0xB1 : 0xB2));
    }
}

BOOST_AUTO_TEST_CASE(store_11_resume_quota_refuses_invalid_cached_credit)
{
    ResumeQuotaFixture f{m_path_root / "store-11"};
    std::string err;
    auto root = f.entry.core.files[0].pieces_root;
    root.data[0] ^= 1;
    BOOST_REQUIRE(f.receiver.Store().SavePieceProof(f.entry.artifact_id, 0, 0, f.size, root, f.proof, err));
    BOOST_CHECK(!f.receiver.EnforceDownloadQuota(f.manifest, err));
    BOOST_REQUIRE(f.receiver.Store().SavePieceProof(f.entry.artifact_id, 0, 0, f.size + 1,
                                                  f.entry.core.files[0].pieces_root, f.proof, err));
    BOOST_CHECK(!f.receiver.EnforceDownloadQuota(f.manifest, err));
    { std::ofstream out(f.ProofPath()); out << "{\"file_size\":\"invalid\",\"pieces_root\":0}"; }
    BOOST_CHECK(!f.receiver.EnforceDownloadQuota(f.manifest, err));
    fs::remove(f.ProofPath());
    BOOST_CHECK(!f.receiver.EnforceDownloadQuota(f.manifest, err));
    f.RestoreProof();
    {
        std::fstream out(f.PiecePath(), std::ios::in | std::ios::out | std::ios::binary);
        out.put(static_cast<char>(f.first[0] ^ 1));
    }
    BOOST_CHECK(!f.receiver.EnforceDownloadQuota(f.manifest, err));
    BOOST_REQUIRE(f.receiver.Store().DeletePiece(f.entry.artifact_id, 0, 0, err));
    BOOST_REQUIRE(f.receiver.PutFetchedPiece(f.entry.artifact_id, 0, 0, f.first, f.proof, f.size,
                                           f.entry.core.files[0].pieces_root, err));
    BOOST_REQUIRE_MESSAGE(f.receiver.EnforceDownloadQuota(f.manifest, err), err);
}
