// Join the saved campaign to its verified ciphertext bytes and its own key.
// Metadata or a primitive cipher round trip alone cannot prove this contract.
BOOST_AUTO_TEST_CASE(created_release_ciphertext_opens_with_its_own_campaign_secret)
{
    const fs::path root = m_path_root / "release-ciphertext-bytes";
    WriteTinySafeTensors(root / "a.dir", "{}");
    WriteTinySafeTensors(root / "b.dir", "{\"__metadata__\":{\"name\":\"different-model\"}}");
    ModelCatalog cat{root, 8 << 20};
    const fs::path helper_dir = cat.Store().Root().parent_path();
    const auto input_bytes = [&](const fs::path& path) {
        std::ifstream in(path, std::ios::binary);
        BOOST_REQUIRE(in.good());
        return std::vector<unsigned char>((std::istreambuf_iterator<char>(in)), std::istreambuf_iterator<char>());
    };
    const std::vector<std::vector<unsigned char>> original{
        input_bytes(root / "a.dir" / "toy.safetensors"),
        input_bytes(root / "b.dir" / "toy.safetensors")};
    BOOST_REQUIRE(original[0] != original[1]);
    const std::vector<std::vector<unsigned char>> secret{
        std::vector<unsigned char>(32, 0xaa), std::vector<unsigned char>(32, 0xbb)};
    std::vector<Digest48> ciphertext_ids;
    std::vector<std::string> release_ids;
    UniValue res;
    std::string code;
    for (size_t i = 0; i < original.size(); ++i) {
        const fs::path dir = root / (i == 0 ? "a.dir" : "b.dir");
        BOOST_REQUIRE_MESSAGE(CallHelper(cat, "hostmodel", OneParam(fs::PathToString(dir)), res, code), code);
        const std::string uri = res["uri"].get_str();
        BOOST_REQUIRE_MESSAGE(CallHelper(cat, "createmodelrelease", CreateParams(uri, i == 0 ? 'a' : 'b'), res, code), code);
        const std::string release_id = res["release_id"].get_str();
        release_ids.push_back(release_id);
        BOOST_REQUIRE_MESSAGE(CallHelper(cat, "getmodelrelease", UniValue(UniValue::VARR), res, code), code);
        bool found{false};
        for (const auto& campaign : res["campaigns"].getValues()) {
            if (campaign["release_id"].get_str() != release_id) continue;
            found = true;
            // The base silently points at the plaintext instead of storing ciphertext.
            BOOST_REQUIRE(campaign["ciphertext_artifact_id"].get_str() != campaign["artifact_id"].get_str());
            Digest48 ciphertext;
            std::string err;
            BOOST_REQUIRE_MESSAGE(Digest48::FromHex(campaign["ciphertext_artifact_id"].get_str(), ciphertext, err), err);
            ciphertext_ids.push_back(ciphertext);
        }
        BOOST_REQUIRE(found);
    }
    BOOST_REQUIRE_EQUAL(ciphertext_ids.size(), 2U);
    BOOST_REQUIRE(ciphertext_ids[0] != ciphertext_ids[1]);
    BOOST_REQUIRE(release_ids[0] != release_ids[1]);
    const auto check_stored = [&](ModelCatalog& store, size_t index) {
        CatalogEntry entry;
        BOOST_REQUIRE(store.Find(ciphertext_ids[index], entry));
        BOOST_REQUIRE_EQUAL(entry.core.files.size(), 1U);
        const auto& file = entry.core.files[0];
        BOOST_CHECK_EQUAL(file.path, "tmp-cipher.btxenc");
        BOOST_REQUIRE_GT(file.size, 0U);
        BOOST_REQUIRE_LE(file.size, RELEASE_WRAP_MAX_BYTES);
        std::vector<unsigned char> wrapped;
        std::string err;
        const uint32_t count = static_cast<uint32_t>((file.size + PIECE_SIZE - 1) / PIECE_SIZE);
        for (uint32_t piece_index = 0; piece_index < count; ++piece_index) {
            std::vector<unsigned char> piece;
            std::vector<Digest48> proof;
            uint64_t file_size{0};
            BOOST_REQUIRE_MESSAGE(store.GetVerifiedPiece(entry.artifact_id, 0, piece_index, piece, proof, file_size, err), err);
            BOOST_REQUIRE_EQUAL(file_size, file.size);
            wrapped.insert(wrapped.end(), piece.begin(), piece.end());
        }
        BOOST_REQUIRE_GE(wrapped.size(), static_cast<size_t>(file.size));
        wrapped.resize(static_cast<size_t>(file.size));
        BOOST_REQUIRE(LooksLikeBtxEnc2(wrapped));
        std::vector<unsigned char> plain;
        BOOST_REQUIRE_MESSAGE(UnwrapBtxEnc2(secret[index], wrapped, plain, err), err);
        BOOST_CHECK(plain == original[index]);
        std::vector<unsigned char> wrong;
        err.clear();
        BOOST_CHECK(!UnwrapBtxEnc2(secret[1 - index], wrapped, wrong, err));
        BOOST_CHECK(wrong.empty());
    };
    // Re-read the first ciphertext after creating the second release too.
    for (size_t i = 0; i < original.size(); ++i) check_stored(cat, i);
    // Fresh catalog metadata and pieces, without pretending to restart helper globals.
    ModelCatalog reloaded{root, 8 << 20};
    std::vector<ReleaseCampaign> campaigns;
    std::string err;
    BOOST_REQUIRE_MESSAGE(LoadCampaigns(helper_dir, campaigns, err), err);
    BOOST_REQUIRE_EQUAL(campaigns.size(), 2U);
    for (size_t i = 0; i < original.size(); ++i) {
        const auto saved = std::find_if(campaigns.begin(), campaigns.end(), [&](const ReleaseCampaign& c) {
            return c.release_id.Hex() == release_ids[i];
        });
        BOOST_REQUIRE(saved != campaigns.end());
        BOOST_CHECK(saved->ciphertext_artifact_id == ciphertext_ids[i]);
        check_stored(reloaded, i);
    }
}
