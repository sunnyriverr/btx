BOOST_AUTO_TEST_CASE(import_path_refreshes_verified_source_durably)
{
    for (const bool initially_pinned : {false, true}) {
        for (const bool request_pin : {false, true}) {
            const fs::path tmp = m_path_root / (std::string("rehost-") +
                (initially_pinned ? "pinned-" : "unpinned-") + (request_pin ? "pin" : "no-pin"));
            const fs::path catalog_dir = tmp / "catalog";
            modelnet::ModelCatalog cat{catalog_dir, 8 << 20};
            const auto original = ImportTiny(cat, tmp / "original", 0x91, initially_pinned);
            const auto replacement = WriteTinyModel(tmp / "replacement", 0x91);
            fs::rename(tmp / "original", tmp / "retained-original");
            modelnet::CatalogEntry refreshed;
            std::string err;
            BOOST_REQUIRE_MESSAGE(cat.ImportPath(fs::PathToString(replacement), request_pin, refreshed, err), err);
            BOOST_CHECK(refreshed.model_id == original.model_id);
            BOOST_CHECK(refreshed.artifact_id == original.artifact_id);
            BOOST_CHECK_EQUAL(refreshed.source_path, fs::PathToString(replacement));
            BOOST_CHECK_EQUAL(refreshed.pinned, initially_pinned || request_pin);
            BOOST_CHECK(refreshed.admission == (request_pin ? modelnet::AdmissionLevel::PINNED : original.admission));
            BOOST_CHECK_EQUAL(refreshed.bytes_verified, request_pin || original.bytes_verified);
            modelnet::ModelCatalog reopened{catalog_dir, 8 << 20};
            modelnet::CatalogEntry saved;
            BOOST_REQUIRE(reopened.Find(original.model_id, saved));
            BOOST_CHECK_EQUAL(saved.source_path, refreshed.source_path);
            BOOST_CHECK_EQUAL(saved.pinned, refreshed.pinned);
            BOOST_CHECK(saved.admission == refreshed.admission);
            BOOST_CHECK_EQUAL(saved.bytes_verified, refreshed.bytes_verified);

            // No mutation means no save is needed, even if saving is unavailable.
            fs::rename(catalog_dir / "catalog.json", catalog_dir / "retained.json");
            fs::create_directory(catalog_dir / "catalog.json");
            BOOST_REQUIRE_MESSAGE(cat.ImportPath(fs::PathToString(replacement), false, saved, err), err);
            BOOST_CHECK_EQUAL(saved.source_path, refreshed.source_path);
            BOOST_CHECK_EQUAL(saved.pinned, refreshed.pinned);
            fs::remove(catalog_dir / "catalog.json");
            fs::rename(catalog_dir / "retained.json", catalog_dir / "catalog.json");

            // Different valid bytes are a new model, not a source for the old one.
            const auto other = ImportTiny(cat, tmp / "other", 0x92, false);
            BOOST_CHECK(other.model_id != original.model_id);
            BOOST_REQUIRE(cat.Find(original.model_id, saved));
            BOOST_CHECK_EQUAL(saved.source_path, refreshed.source_path);
            const fs::path invalid = tmp / "invalid";
            fs::create_directories(invalid);
            { std::ofstream bad(invalid / "model.safetensors", std::ios::binary); bad << "invalid"; }
            BOOST_CHECK(!cat.ImportPath(fs::PathToString(invalid), true, saved, err));
            BOOST_REQUIRE(cat.Find(original.model_id, saved));
            BOOST_CHECK_EQUAL(saved.source_path, refreshed.source_path);
            BOOST_CHECK(saved.artifact_id == original.artifact_id);
            const fs::path checkout = tmp / "checkout";
            BOOST_REQUIRE_MESSAGE(cat.MaterializeCheckout(original.model_id, checkout, err), err);
            BOOST_CHECK(ReadFileBytes(checkout / "model.safetensors") == TinySafeTensors(0x91));
        }
    }
}

BOOST_AUTO_TEST_CASE(import_path_source_refresh_rolls_back_failed_save)
{
    for (const bool initially_pinned : {false, true}) {
        const fs::path tmp = m_path_root / (initially_pinned ? "rehost-rollback-pinned" : "rehost-rollback-unpinned");
        const fs::path catalog_dir = tmp / "catalog";
        modelnet::ModelCatalog cat{catalog_dir, 8 << 20};
        const auto original = ImportTiny(cat, tmp / "original", 0x93, initially_pinned);
        const auto replacement = WriteTinyModel(tmp / "replacement", 0x93);
        fs::rename(tmp / "original", tmp / "retained-original");
        const auto durable_before = ReadFileBytes(catalog_dir / "catalog.json");
        // A directory at the save destination forces the actual atomic save to fail.
        fs::rename(catalog_dir / "catalog.json", catalog_dir / "retained.json");
        fs::create_directory(catalog_dir / "catalog.json");
        modelnet::CatalogEntry entry;
        std::string err;
        BOOST_CHECK(!cat.ImportPath(fs::PathToString(replacement), true, entry, err));
        BOOST_CHECK(!err.empty());
        BOOST_REQUIRE(cat.Find(original.model_id, entry));
        BOOST_CHECK_EQUAL(entry.source_path, original.source_path);
        BOOST_CHECK_EQUAL(entry.pinned, original.pinned);
        BOOST_CHECK(entry.admission == original.admission);
        BOOST_CHECK_EQUAL(entry.bytes_verified, original.bytes_verified);
        BOOST_CHECK(ReadFileBytes(catalog_dir / "retained.json") == durable_before);
        fs::remove(catalog_dir / "catalog.json");
        fs::rename(catalog_dir / "retained.json", catalog_dir / "catalog.json");
        // An unrelated successful save must not persist the rejected source/pin.
        ImportTiny(cat, tmp / "other", 0x94, false);
        modelnet::ModelCatalog reopened{catalog_dir, 8 << 20};
        BOOST_REQUIRE(reopened.Find(original.model_id, entry));
        BOOST_CHECK_EQUAL(entry.source_path, original.source_path);
        BOOST_CHECK_EQUAL(entry.pinned, original.pinned);
        BOOST_CHECK(entry.admission == original.admission);
        BOOST_CHECK_EQUAL(entry.bytes_verified, original.bytes_verified);
        BOOST_REQUIRE_MESSAGE(cat.ImportPath(fs::PathToString(replacement), true, entry, err), err);
        modelnet::ModelCatalog retried{catalog_dir, 8 << 20};
        BOOST_REQUIRE(retried.Find(original.model_id, entry));
        BOOST_CHECK_EQUAL(entry.source_path, fs::PathToString(replacement));
        BOOST_CHECK(entry.pinned);
        BOOST_CHECK(entry.admission == modelnet::AdmissionLevel::PINNED);
        BOOST_CHECK(entry.bytes_verified);
        BOOST_CHECK(entry.artifact_id == original.artifact_id);
    }
}

