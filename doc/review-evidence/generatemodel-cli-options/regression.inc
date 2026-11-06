BOOST_AUTO_TEST_CASE(rpc_convert_values_generatemodel_options)
{
    const std::string options{R"({"prompt":"hello=BTX \"quoted\"","max_new_tokens":8})"};
    UniValue expected;
    BOOST_REQUIRE(expected.read(options));
    for (const std::string id : {"btx://model/example", "123", "{\"literal\":true}"}) {
        const UniValue positional = RPCConvertValues("generatemodel", {id, options});
        BOOST_REQUIRE_EQUAL(positional.size(), 2U);
        BOOST_CHECK_EQUAL(positional[0].get_str(), id);
        BOOST_CHECK(positional[1].isObject());
        BOOST_CHECK_EQUAL(positional[1].write(), expected.write());

        const UniValue named = RPCConvertNamedValues("generatemodel", {"id=" + id, "opts=" + options});
        BOOST_CHECK_EQUAL(named["id"].get_str(), id);
        BOOST_CHECK(named["opts"].isObject());
        BOOST_CHECK_EQUAL(named["opts"].write(), expected.write());

        BOOST_CHECK_EQUAL(RPCConvertValues("generatemodel", {id})[0].get_str(), id);
        BOOST_CHECK_EQUAL(RPCConvertNamedValues("generatemodel", {"id=" + id})["id"].get_str(), id);
    }
}

BOOST_AUTO_TEST_CASE(rpc_convert_values_generatemodel_invalid_options)
{
    for (const std::string invalid : {"{", "plain prompt", "{\"prompt\":}"}) {
        BOOST_CHECK_THROW(RPCConvertValues("generatemodel", {"id", invalid}), std::runtime_error);
        BOOST_CHECK_THROW(RPCConvertNamedValues("generatemodel", {"id=id", "opts=" + invalid}), std::runtime_error);
    }
    // Generic JSON conversion retains the type; the RPC server enforces OBJ.
    for (const std::string other : {"[]", "true", "7", "\"prompt\""}) {
        UniValue expected;
        BOOST_REQUIRE(expected.read(other));
        BOOST_CHECK_EQUAL(RPCConvertValues("generatemodel", {"id", other})[1].write(), expected.write());
        BOOST_CHECK_EQUAL(RPCConvertNamedValues("generatemodel", {"opts=" + other})["opts"].write(), expected.write());
    }
}

