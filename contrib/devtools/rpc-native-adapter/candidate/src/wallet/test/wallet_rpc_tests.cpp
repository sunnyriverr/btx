// Copyright (c) 2025-present The Bitcoin Core developers
// Distributed under the MIT software license, see the accompanying
// file COPYING or http://www.opensource.org/licenses/mit-license.php.

#include <rpc/client.h>
#include <rpc/request.h>
#include <rpc/server.h>
#include <test/util/setup_common.h>
#include <univalue.h>
#include <wallet/rpc/util.h>
#include <wallet/test/wallet_test_fixture.h>

#include <boost/test/unit_test.hpp>

#include <cstdint>
#include <iostream>
#include <optional>
#include <set>
#include <stdexcept>
#include <string>
#include <vector>

namespace wallet {
static std::string TestWalletName(const std::string& endpoint, std::optional<std::string> parameter = std::nullopt)
{
    JSONRPCRequest req;
    req.URI = endpoint;
    return EnsureUniqueWalletName(req, parameter ? &*parameter : nullptr);
}

static std::string ArgumentComparisonTypeName(RPCArg::Type type)
{
    switch (type) {
    case RPCArg::Type::OBJ: return "OBJ";
    case RPCArg::Type::ARR: return "ARR";
    case RPCArg::Type::STR: return "STR";
    case RPCArg::Type::NUM: return "NUM";
    case RPCArg::Type::BOOL: return "BOOL";
    case RPCArg::Type::OBJ_NAMED_PARAMS: return "OBJ_NAMED_PARAMS";
    case RPCArg::Type::OBJ_USER_KEYS: return "OBJ_USER_KEYS";
    case RPCArg::Type::AMOUNT: return "AMOUNT";
    case RPCArg::Type::STR_HEX: return "STR_HEX";
    case RPCArg::Type::RANGE: return "RANGE";
    }
    throw std::runtime_error("Unknown RPC argument type in comparison record");
}

static UniValue ArgumentComparisonDefinition(const RPCArg& arg)
{
    UniValue record{UniValue::VOBJ};
    record.pushKV("names", arg.m_names);
    record.pushKV("type", ArgumentComparisonTypeName(arg.m_type));
    UniValue types{UniValue::VARR};
    for (const auto type : arg.m_type_per_name) types.push_back(ArgumentComparisonTypeName(type));
    record.pushKV("per_name_types", types);
    record.pushKV("skip", arg.m_opts.skip_type_check);
    record.pushKV("also_positional", arg.m_opts.also_positional);
    record.pushKV("hidden", arg.m_opts.hidden);
    record.pushKV("optional", arg.IsOptional());
    UniValue inner{UniValue::VARR};
    for (const auto& child : arg.m_inner) inner.push_back(ArgumentComparisonDefinition(child));
    record.pushKV("inner", inner);
    return record;
}

static std::string ArgumentComparisonStatusName(CRPCCommand::ArgumentMetadata::Status status)
{
    using Status = CRPCCommand::ArgumentMetadata::Status;
    switch (status) {
    case Status::AVAILABLE: return "AVAILABLE";
    case Status::MISSING: return "MISSING";
    case Status::ROUTING_MISMATCH: return "ROUTING_MISMATCH";
    case Status::FACTORY_ERROR: return "FACTORY_ERROR";
    }
    throw std::runtime_error("Unknown RPC metadata status in comparison record");
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

BOOST_FIXTURE_TEST_CASE(wallet_rpc_argument_comparison_records, WalletTestingSetup)
{
    // Declaration factories and client conversions only: never execute an RPC actor.
    const std::set<std::string> selected{"createmodelidentity", "getmodel", "getmodelevents", "getmodelreciprocity", "help", "hostmodel", "importmatmulattestations", "listmodelidentities", "searchmodels", "submitmatmulattestations", "walletprocesspsbt"};
    std::set<std::string> found;
    UniValue registrations{UniValue::VARR};
    for (const auto& entry : tableRPC.listCommandEntries()) {
        if (!selected.contains(entry.method)) continue;
        found.insert(entry.method);
        UniValue record{UniValue::VOBJ};
        record.pushKV("method", entry.method);
        record.pushKV("handler_index", uint64_t{entry.handler_index});
        record.pushKV("canonical", entry.command->name);
        const auto metadata = entry.command->GetArgumentMetadata();
        record.pushKV("status", ArgumentComparisonStatusName(metadata.status));
        UniValue routing{UniValue::VARR};
        for (const auto& [names, named_only] : entry.command->argNames) {
            UniValue route{UniValue::VARR};
            route.push_back(names);
            route.push_back(named_only);
            routing.push_back(route);
        }
        record.pushKV("routing", routing);
        UniValue arguments{UniValue::VNULL};
        if (metadata.status == CRPCCommand::ArgumentMetadata::Status::AVAILABLE) {
            BOOST_REQUIRE(metadata.declaration.has_value());
            arguments = UniValue{UniValue::VARR};
            for (const auto& arg : metadata.declaration->GetArgDefinitions()) {
                arguments.push_back(ArgumentComparisonDefinition(arg));
            }
        } else {
            BOOST_CHECK(!metadata.declaration.has_value());
        }
        record.pushKV("arguments", arguments);
        registrations.push_back(record);
    }
    BOOST_REQUIRE(found == selected);

    // These are the existing probe inputs, not their expected answers.
    UniValue inputs;
    BOOST_REQUIRE(inputs.read(R"RPC_INPUTS([
  {"method":"walletprocesspsbt","form":"named","selector":"adjust_timelocks","raw":"true"},
  {"method":"walletprocesspsbt","form":"named","selector":"adjust_timelocks","raw":"false"},
  {"method":"walletprocesspsbt","form":"positional","selector":1,"raw":"{\"adjust_timelocks\":true}"},
  {"method":"walletprocesspsbt","form":"named","selector":"options","raw":"{\"adjust_timelocks\":true}"},
  {"method":"hostmodel","form":"positional","selector":1,"raw":"{}"},
  {"method":"hostmodel","form":"named","selector":"options","raw":"{}"},
  {"method":"hostmodel","form":"positional","selector":1,"raw":"[]"},
  {"method":"hostmodel","form":"named","selector":"options","raw":"[]"},
  {"method":"hostmodel","form":"positional","selector":1,"raw":"true"},
  {"method":"hostmodel","form":"named","selector":"options","raw":"true"},
  {"method":"hostmodel","form":"positional","selector":1,"raw":"\"text\""},
  {"method":"hostmodel","form":"named","selector":"options","raw":"\"text\""},
  {"method":"hostmodel","form":"positional","selector":1,"raw":"plain-text"},
  {"method":"hostmodel","form":"named","selector":"options","raw":"plain-text"},
  {"method":"hostmodel","form":"positional","selector":1,"raw":"null"},
  {"method":"hostmodel","form":"named","selector":"options","raw":"null"},
  {"method":"importmatmulattestations","form":"positional","selector":0,"raw":"[]"},
  {"method":"importmatmulattestations","form":"named","selector":"attestations","raw":"[]"},
  {"method":"submitmatmulattestations","form":"positional","selector":0,"raw":"[]"},
  {"method":"submitmatmulattestations","form":"named","selector":"attestations","raw":"[]"},
  {"method":"getmodel","form":"positional","selector":1,"raw":"FREE_ONLY"},
  {"method":"getmodel","form":"named","selector":"mode","raw":"FREE_ONLY"},
  {"method":"getmodel","form":"positional","selector":1,"raw":"{}"},
  {"method":"getmodel","form":"named","selector":"mode","raw":"{}"},
  {"method":"help","form":"positional","selector":0,"raw":"true"},
  {"method":"help","form":"named","selector":"command","raw":"true"},
  {"method":"help","form":"positional","selector":0,"raw":"{\"key\":1}"},
  {"method":"help","form":"named","selector":"command","raw":"{\"key\":1}"},
  {"method":"walletprocesspsbt","form":"positional","selector":1,"raw":"false"},
  {"method":"walletprocesspsbt","form":"named","selector":"sign","raw":"false"},
  {"method":"createmodelidentity","form":"positional","selector":0,"raw":"true"},
  {"method":"createmodelidentity","form":"named","selector":"label","raw":"true"},
  {"method":"createmodelidentity","form":"positional","selector":0,"raw":"{\"key\":1}"},
  {"method":"createmodelidentity","form":"named","selector":"label","raw":"{\"key\":1}"},
  {"method":"searchmodels","form":"positional","selector":0,"raw":"llama 70m"},
  {"method":"searchmodels","form":"positional","selector":0,"raw":"{\"text\":\"llama\",\"limit\":5}"},
  {"method":"searchmodels","form":"named","selector":"query","raw":"llama 70m"},
  {"method":"searchmodels","form":"named","selector":"query","raw":"{\"text\":\"llama\",\"limit\":5}"},
  {"method":"searchmodels","form":"positional","selector":0,"raw":"true"},
  {"method":"searchmodels","form":"named","selector":"query","raw":"true"}
])RPC_INPUTS"));
    BOOST_REQUIRE(inputs.isArray());
    UniValue conversions{UniValue::VARR};
    for (const auto& input : inputs.getValues()) {
        const std::string method{input["method"].get_str()};
        const std::string form{input["form"].get_str()};
        const std::string raw{input["raw"].get_str()};
        BOOST_REQUIRE(selected.contains(method));
        UniValue result{UniValue::VOBJ};
        try {
            UniValue value;
            if (form == "positional") {
                const int index{input["selector"].getInt<int>()};
                BOOST_REQUIRE(index >= 0 && index < 16);
                std::vector<std::string> args(index + 1);
                args[index] = raw;
                value = RPCConvertValues(method, args)[index];
            } else {
                BOOST_REQUIRE_EQUAL(form, "named");
                const std::string name{input["selector"].get_str()};
                const auto values = RPCConvertNamedValues(method, {name + "=" + raw});
                BOOST_REQUIRE(values.exists(name));
                value = values[name];
            }
            result.pushKV("value", value);
            result.pushKV("type", int{value.getType()});
        } catch (const std::exception& error) {
            result.pushKV("error", std::string{error.what()});
        } catch (const UniValue& error) {
            result.pushKV("error", error.write());
        }
        UniValue record{UniValue::VOBJ};
        record.pushKV("method", method);
        record.pushKV("form", form);
        record.pushKV("selector", input["selector"]);
        record.pushKV("raw", raw);
        record.pushKV("result", result);
        conversions.push_back(record);
    }
    BOOST_REQUIRE_EQUAL(conversions.size(), inputs.size());
    UniValue output{UniValue::VOBJ};
    output.pushKV("schema", 1);
    output.pushKV("registrations", registrations);
    output.pushKV("conversions", conversions);
    std::cout << "RPC_ARGUMENT_COMPARISON_RECORDS " << output.write() << '\n';
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
