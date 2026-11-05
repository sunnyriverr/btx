#define BOOST_TEST_DYN_LINK
#define BOOST_TEST_MODULE provider_refresh_component
#include <boost/test/unit_test.hpp>
#include <modelnet/catalog.h>
#include <modelnet/helper.h>
#include <modelnet/identity.h>
#include <modelnet/protocol.h>
#include <modelnet/provider_route.h>
#include <util/fs.h>
#include <util/translation.h>
#include <univalue.h>
#include <chrono>
#include <fstream>
#include <thread>
#include <cstdlib>
const TranslateFn G_TRANSLATION_FUN{nullptr};
const fs::path m_path_root = fs::PathFromString(std::getenv("BTX_PROVIDER_TEST_ROOT"));
BOOST_AUTO_TEST_CASE(search_refreshes_signed_provider_observations)
{
    using namespace modelnet;
    const auto now_ms = [] {
        return std::chrono::duration_cast<std::chrono::milliseconds>(
            std::chrono::system_clock::now().time_since_epoch()).count();
    };
    for (const bool initially_complete : {false, true}) {
        const fs::path root = m_path_root / (initially_complete ? "refresh-complete" : "refresh-partial");
        fs::create_directories(root);
        const fs::path model = root / "refresh.safetensors";
        std::string header = R"({"weight":{"dtype":"F32","shape":[256],"data_offsets":[0,1024]}})";
        header.append((8 - header.size() % 8) % 8, ' ');
        {
            std::ofstream file(model, std::ios::binary);
            const uint64_t header_size = header.size();
            for (int i = 0; i < 8; ++i) file.put(static_cast<char>(header_size >> (8 * i)));
            file << header << std::string(1024, initially_complete ? '\x01' : '\x02');
            BOOST_REQUIRE(file.good());
        }
        ModelCatalog cat{root / "models", 1 << 20};
        CatalogEntry entry;
        std::string err;
        BOOST_REQUIRE_MESSAGE(cat.ImportPath(fs::PathToString(model), false, entry, err), err);
        BOOST_REQUIRE(cat.Seed(entry.model_id, false, err));
        auto rpc = [&](const std::string& method, const UniValue& params) {
            UniValue req(UniValue::VOBJ), result;
            req.pushKV("method", method);
            req.pushKV("params", params);
            std::string code;
            BOOST_REQUIRE_MESSAGE(DispatchHelperRpc(cat, req, result, code, err), code + ": " + err);
            return result;
        };
        auto native = [&](const std::string& route, const UniValue& body, int status) {
            NativeRequest req;
            req.method = "POST";
            req.path = std::string(MODEL_HTTP_ROOT) + "ext/providers/" + route;
            req.body = body.write();
            req.peer_addr = "signed-refresh-fixture";
            NativeResponse response;
            BOOST_REQUIRE(HandleNativeRequest(cat, req, response));
            BOOST_REQUIRE_MESSAGE(response.status == status, response.body);
            UniValue result;
            BOOST_REQUIRE(result.read(response.body));
            return result;
        };
        UniValue query(UniValue::VOBJ), search_params(UniValue::VARR), id_params(UniValue::VARR);
        query.pushKV("scope", "LOCAL");
        search_params.push_back(query);
        id_params.push_back(entry.model_id.Hex());
        rpc("searchmodels", search_params);
        BOOST_REQUIRE_EQUAL(rpc("getmodelproviders", id_params)["providers"].size(), 0);
        std::vector<unsigned char> pk, sk;
        BOOST_REQUIRE(GenerateMlDsa44(pk, sk, err));
        ProviderRecord record;
        record.resource = entry.model_id;
        record.pubkey = pk;
        record.seq = 10;
        record.complete = initially_complete;
        record.reachability_kind = "direct";
        record.endpoints = {"192.0.2.10:29447"};
        record.ranges = {{0, 1}};
        record.expiry_ms = now_ms() + 300000;
        auto put = [&](int status) {
            BOOST_REQUIRE(SignProviderRecord(record, Span<const unsigned char>{sk.data(), sk.size()}, err));
            return native("put", ProviderRecordToJson(record), status);
        };
        put(200);
        rpc("searchmodels", search_params);
        BOOST_REQUIRE_EQUAL(rpc("getmodelproviders", id_params)["providers"].size(), 1);
        BOOST_CHECK_EQUAL(rpc("getmodelproviders", id_params)["providers"][0]["complete"].get_bool(), initially_complete);
        record.seq = 11;
        record.complete = !initially_complete;
        record.reachability_kind = "relay";
        put(200);
        UniValue lookup(UniValue::VOBJ);
        lookup.pushKV("resource", entry.model_id.Hex());
        auto cached = native("get", lookup, 200);
        BOOST_REQUIRE_EQUAL(cached["records"].size(), 1);
        BOOST_CHECK_EQUAL(cached["records"][0]["seq"].getInt<int>(), 11);
        BOOST_CHECK_EQUAL(cached["records"][0]["complete"].get_bool(), !initially_complete);
        rpc("searchmodels", search_params);
        auto view = rpc("getmodelproviders", id_params);
        BOOST_REQUIRE_EQUAL(view["providers"].size(), 1);
        BOOST_CHECK_EQUAL(view["providers"][0]["complete"].get_bool(), !initially_complete);
        BOOST_CHECK(view["providers"][0]["relayed"].get_bool());
        BOOST_CHECK(!view["providers"][0]["direct"].get_bool());
        BOOST_CHECK_EQUAL(rpc("getmodelavailability", id_params)["providers_complete"].getInt<int>(), initially_complete ? 0 : 1);
        BOOST_CHECK_EQUAL(rpc("getmodelpeercount", id_params)["complete"].getInt<int>(), initially_complete ? 0 : 1);
        record.seq = 9;
        record.complete = initially_complete;
        const auto rejected = put(403);
        BOOST_CHECK(rejected.write().find("sequence rollback") != std::string::npos);
        cached = native("get", lookup, 200);
        BOOST_CHECK_EQUAL(cached["records"][0]["seq"].getInt<int>(), 11);
        rpc("searchmodels", search_params);
        BOOST_CHECK_EQUAL(rpc("getmodelproviders", id_params)["providers"][0]["complete"].get_bool(), !initially_complete);
        // Expired cache records are absent, but historical sightings survive.
        record.seq = 12;
        record.complete = !initially_complete;
        record.expiry_ms = now_ms() + 1000;
        put(200);
        rpc("searchmodels", search_params);
        std::this_thread::sleep_until(std::chrono::system_clock::time_point{
            std::chrono::milliseconds{record.expiry_ms + 1}});
        BOOST_REQUIRE_EQUAL(native("get", lookup, 200)["records"].size(), 0);
        rpc("searchmodels", search_params);
        view = rpc("getmodelproviders", id_params);
        BOOST_REQUIRE_EQUAL(view["providers"].size(), 1);
        BOOST_CHECK_EQUAL(view["providers"][0]["complete"].get_bool(), !initially_complete);
        BOOST_CHECK(view["providers"][0]["relayed"].get_bool());
    }
}
