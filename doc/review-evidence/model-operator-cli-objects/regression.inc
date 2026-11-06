BOOST_AUTO_TEST_CASE(rpc_convert_values_model_operator_requests)
{
    for (const std::string method : {"setmodelprofile", "setmodelmirror"}) {
        const std::string request = R"({"profile":"custom","storage_bytes":"4MiB","publisher_id":"publisher","keep_latest":2,"idempotency_key":"retry=key/01","automatic_spend_atoms":0})";
        UniValue expected;
        BOOST_REQUIRE(expected.read(request));
        const UniValue positional = RPCConvertValues(method, {" \t" + request + "\n"});
        const UniValue named = RPCConvertNamedValues(method, {"request=" + request});
        BOOST_REQUIRE_EQUAL(positional.size(), 1U);
        BOOST_CHECK(positional[0].isObject());
        BOOST_CHECK(named["request"].isObject());
        BOOST_CHECK_EQUAL(positional[0].write(), expected.write());
        BOOST_CHECK_EQUAL(named["request"].write(), expected.write());
        if (positional[0].isObject()) {
            BOOST_CHECK_EQUAL(positional[0]["idempotency_key"].get_str(), "retry=key/01");
        }
        BOOST_CHECK(RPCConvertValues(method, {"{}"})[0].isObject());
        BOOST_CHECK(RPCConvertNamedValues(method, {"request={}"})["request"].isObject());
        BOOST_CHECK(RPCConvertValues(method, {}).empty());
        BOOST_CHECK(RPCConvertNamedValues(method, {}).empty());

        // Only objects are converted. Bare profile presets and all other text
        // retain their original type, leaving validation to the helper.
        for (const std::string text : {"personal", "infrastructure", "mirror", "custom",
                                      "", "null", "true", "1", "[]", "[{}]", "\"custom\"", "{invalid"}) {
            const UniValue value = RPCConvertValues(method, {text});
            const UniValue arg = RPCConvertNamedValues(method, {"request=" + text});
            BOOST_CHECK(value[0].isStr());
            BOOST_CHECK(arg["request"].isStr());
            BOOST_CHECK_EQUAL(value[0].get_str(), text);
            BOOST_CHECK_EQUAL(arg["request"].get_str(), text);
        }
    }
}

