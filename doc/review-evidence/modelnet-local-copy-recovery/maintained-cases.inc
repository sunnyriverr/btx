BOOST_AUTO_TEST_CASE(import_path_repairs_damaged_local_piece)
{
    const fs::path tmp = m_path_root / "local-copy-recovery";
    const fs::path catalog_dir = tmp / "catalog";
    const auto source = WriteTinyModel(tmp / "original", 0x95);
    modelnet::ModelCatalog cat{catalog_dir, 8 << 20};
    modelnet::CatalogEntry original;
    std::string err;
    BOOST_REQUIRE_MESSAGE(cat.ImportPath(fs::PathToString(source), true, original, err), err);
    const auto control = ImportTiny(cat, tmp / "control", 0x96, false);
    const uint64_t used = cat.Store().UsedBytes();
    const auto expected = TinySafeTensors(0x95);
    const auto replacement = WriteTinyModel(tmp / "recovery-copy", 0x95);
    fs::rename(source, tmp / "offline-source");
    // Simulate ordinary local disk damage without modifying the index or catalog.
    const fs::path piece_path = cat.Store().Root() / "artifacts" /
        original.artifact_id.Hex().c_str() / "0" / "0.piece";
    BOOST_REQUIRE(ReadFileBytes(piece_path) == expected);
    {
        std::fstream piece(piece_path, std::ios::in | std::ios::out | std::ios::binary);
        BOOST_REQUIRE(piece.good());
        piece.put(static_cast<char>(expected.front() ^ 1));
        piece.close();
        BOOST_REQUIRE(piece.good());
    }
    BOOST_CHECK(!cat.VerifyFileDigest(original.artifact_id, 0, original.core.files[0].sha384, err));

    modelnet::CatalogEntry recovered;
    BOOST_REQUIRE_MESSAGE(cat.ImportPath(fs::PathToString(replacement), false, recovered, err), err);
    BOOST_CHECK(recovered.model_id == original.model_id);
    BOOST_CHECK(recovered.artifact_id == original.artifact_id);
    BOOST_CHECK(recovered.pinned == original.pinned);
    BOOST_CHECK_EQUAL(cat.Store().UsedBytes(), used);
    BOOST_CHECK(ReadFileBytes(piece_path) == expected);

    fs::rename(replacement, tmp / "offline-recovery-copy");
    modelnet::ModelCatalog reopened{catalog_dir, 8 << 20};
    BOOST_REQUIRE(reopened.Find(original.model_id, recovered));
    BOOST_CHECK(recovered.pinned);
    BOOST_CHECK(reopened.Find(control.model_id, recovered));
    BOOST_CHECK_MESSAGE(reopened.MaterializeCheckout(original.model_id, tmp / "checkout", err), err);
    if (fs::exists(tmp / "checkout/model.safetensors")) {
        BOOST_CHECK(ReadFileBytes(tmp / "checkout/model.safetensors") == expected);
    }
}

