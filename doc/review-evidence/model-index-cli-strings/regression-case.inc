BOOST_AUTO_TEST_CASE(rpc_convert_modelindex_endpoints_are_strings)
{
    // These RPCs declare STR, so preserve endpoint/identity bytes even when
    // they resemble JSON. Ordinary shell quoting does not add JSON quotes.
    const std::vector<std::string> endpoints{
        "127.0.0.1:29447", "[::1]:29447", "index.example.invalid:29447",
        "peer=label", "1234", "true", "null", "{}", "[]", R"("quoted")", "",
    };
    for (const std::string method : {"addmodelindex", "removemodelindex"}) {
        for (const auto& endpoint : endpoints) {
            const auto check_string = [&](const auto& convert) {
                UniValue value;
                BOOST_CHECK_NO_THROW(value = convert());
                BOOST_CHECK(value.isStr());
                if (value.isStr()) BOOST_CHECK_EQUAL(value.get_str(), endpoint);
            };
            check_string([&] { return RPCConvertValues(method, {endpoint})[0]; });
            check_string([&] { return RPCConvertNamedValues(method, {"endpoint=" + endpoint})["endpoint"]; });
        }
    }

    // Adjacent object/union conversions keep their existing behavior.
    const auto search = RPCConvertValues("searchmodels", {R"({"scope":"LOCAL"})"});
    BOOST_REQUIRE(search[0].isObject());
    BOOST_CHECK_EQUAL(search[0]["scope"].get_str(), "LOCAL");
    const auto host = RPCConvertNamedValues("hostmodel", {"path=model.safetensors", R"(options={"publish":false})"});
    BOOST_REQUIRE(host["options"].isObject());
    BOOST_CHECK(!host["options"]["publish"].get_bool());
    const auto get = RPCConvertValues("getmodel", {"btx://fixture", "plan"});
    BOOST_REQUIRE(get[1].isStr());
    BOOST_CHECK_EQUAL(get[1].get_str(), "plan");
}
