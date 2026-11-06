// Copyright (c) 2025-present The Bitcoin Core developers
// Distributed under the MIT software license, see the accompanying
// file COPYING or http://www.opensource.org/licenses/mit-license.php.

#include <rpc/request.h>
#include <rpc/server.h>
#include <test/util/setup_common.h>
#include <univalue.h>
#include <wallet/rpc/util.h>
#include <wallet/test/wallet_test_fixture.h>

#include <boost/test/unit_test.hpp>

#include <optional>
#include <string>

namespace wallet {
static std::string TestWalletName(const std::string& endpoint, std::optional<std::string> parameter = std::nullopt)
{
    JSONRPCRequest req;
    req.URI = endpoint;
    return EnsureUniqueWalletName(req, parameter ? &*parameter : nullptr);
}

BOOST_FIXTURE_TEST_SUITE(wallet_rpc_tests, BasicTestingSetup)

BOOST_FIXTURE_TEST_CASE(wallet_rpc_argument_metadata_registration, WalletTestingSetup)
{
    size_t matching_handlers{0};
    for (const auto& entry : tableRPC.listCommandEntries()) {
        if (entry.method != "walletprocesspsbt") continue;
        ++matching_handlers;
        const auto metadata = entry.command->GetArgumentMetadata();
        BOOST_REQUIRE(metadata.status == CRPCCommand::ArgumentMetadata::Status::AVAILABLE);
        BOOST_REQUIRE(metadata.declaration.has_value());
        const auto& args = metadata.declaration->GetArgDefinitions();
        BOOST_REQUIRE(args.size() > 1);
        const auto& options = args[1];
        BOOST_CHECK(options.m_type == RPCArg::Type::OBJ_NAMED_PARAMS);
        bool found_adjust_timelocks{false};
        for (const auto& field : options.m_inner) {
            if (field.m_names != "adjust_timelocks") continue;
            found_adjust_timelocks = true;
            BOOST_CHECK(field.m_type == RPCArg::Type::BOOL);
            BOOST_CHECK(!field.m_opts.skip_type_check);
        }
        BOOST_CHECK(found_adjust_timelocks);

        // This is a copy of the actually registered wallet wrapper. Exercise
        // the sentinel once so a permanently disconnected counter cannot pass.
        CRPCCommand probe{*entry.command};
        size_t actor_calls{0};
        probe.actor = [&](const JSONRPCRequest&, UniValue&, bool) {
            ++actor_calls;
            return true;
        };
        UniValue unused;
        BOOST_CHECK(probe.actor(JSONRPCRequest{}, unused, true));
        BOOST_CHECK_EQUAL(actor_calls, 1);
        const auto copied_metadata = probe.GetArgumentMetadata();
        BOOST_CHECK(copied_metadata.status == CRPCCommand::ArgumentMetadata::Status::AVAILABLE);
        BOOST_CHECK_EQUAL(actor_calls, 1);
    }
    BOOST_CHECK(matching_handlers > 0);
}

BOOST_AUTO_TEST_CASE(ensure_unique_wallet_name)
{
    // EnsureUniqueWalletName should only return if exactly one unique wallet name is provided
    BOOST_CHECK_EQUAL(TestWalletName("/wallet/foo"), "foo");
    BOOST_CHECK_EQUAL(TestWalletName("/wallet/foo", "foo"), "foo");
    BOOST_CHECK_EQUAL(TestWalletName("/", "foo"), "foo");
    BOOST_CHECK_EQUAL(TestWalletName("/bar", "foo"), "foo");

    BOOST_CHECK_THROW(TestWalletName("/"), UniValue);
    BOOST_CHECK_THROW(TestWalletName("/foo"), UniValue);
    BOOST_CHECK_THROW(TestWalletName("/wallet/foo", "bar"), UniValue);
    BOOST_CHECK_THROW(TestWalletName("/wallet/foo", "foobar"), UniValue);
    BOOST_CHECK_THROW(TestWalletName("/wallet/foobar", "foo"), UniValue);
}

BOOST_AUTO_TEST_CASE(validate_wallet_bundle_archive_directory_name)
{
    BOOST_CHECK_EQUAL(ValidateWalletBundleArchiveDirectoryName("wallet.bundle"), "wallet.bundle");
    BOOST_CHECK_THROW(ValidateWalletBundleArchiveDirectoryName(""), UniValue);
    BOOST_CHECK_THROW(ValidateWalletBundleArchiveDirectoryName(".."), UniValue);
    BOOST_CHECK_THROW(ValidateWalletBundleArchiveDirectoryName("../wallet.bundle"), UniValue);
    BOOST_CHECK_THROW(ValidateWalletBundleArchiveDirectoryName("nested/wallet.bundle"), UniValue);
    BOOST_CHECK_THROW(ValidateWalletBundleArchiveDirectoryName("/tmp/wallet.bundle"), UniValue);
#ifdef WIN32
    // A drive without a root directory is not absolute on Windows.
    BOOST_CHECK_THROW(ValidateWalletBundleArchiveDirectoryName("C:"), UniValue);
#endif
}

BOOST_AUTO_TEST_CASE(validate_wallet_bundle_archive_relative_path)
{
    BOOST_CHECK_EQUAL(ValidateWalletBundleArchiveRelativePath("manifest.json"), "manifest.json");
    BOOST_CHECK_EQUAL(ValidateWalletBundleArchiveRelativePath("shielded_viewing_keys/./index.tsv"),
                      "shielded_viewing_keys/index.tsv");
    BOOST_CHECK_THROW(ValidateWalletBundleArchiveRelativePath(""), UniValue);
    BOOST_CHECK_THROW(ValidateWalletBundleArchiveRelativePath("../manifest.json"), UniValue);
    BOOST_CHECK_THROW(ValidateWalletBundleArchiveRelativePath("/tmp/manifest.json"), UniValue);
#ifdef WIN32
    // Neither is absolute on Windows, and both leave the directory they are appended to.
    BOOST_CHECK_THROW(ValidateWalletBundleArchiveRelativePath("\\manifest.json"), UniValue);
    BOOST_CHECK_THROW(ValidateWalletBundleArchiveRelativePath("C:manifest.json"), UniValue);
#endif
}

BOOST_AUTO_TEST_CASE(validate_wallet_bundle_archive_relative_paths_are_unique)
{
    BOOST_CHECK_NO_THROW(EnsureUniqueWalletBundleArchiveRelativePaths(
        {"manifest.json", "shielded.backup.dat", "shielded_viewing_keys/index.tsv"}));
    BOOST_CHECK_THROW(EnsureUniqueWalletBundleArchiveRelativePaths(
        {"manifest.json", "manifest.json"}), UniValue);
    BOOST_CHECK_THROW(EnsureUniqueWalletBundleArchiveRelativePaths(
        {"shielded_viewing_keys/index.tsv", "shielded_viewing_keys/./index.tsv"}), UniValue);
}

BOOST_AUTO_TEST_SUITE_END()
} // namespace wallet
