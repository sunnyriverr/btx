BOOST_AUTO_TEST_CASE(rpc_convert_model_identity_labels_are_literal)
{
    // Labels are strings, including text which also happens to be valid JSON.
    const std::vector<std::string> labels{
        "sunny-label", "true", "123", "null", R"({"team":"btx"})", "[1,2]",
        R"("quoted")", "", "sunny river=\xE5\x90\x8D",
    };
    for (const std::string& label : labels) {
        BOOST_TEST_CONTEXT(label) {
            UniValue positional;
            BOOST_CHECK_NO_THROW(positional = RPCConvertValues("createmodelidentity", {label}));
            BOOST_CHECK_EQUAL(positional.size(), 1U);
            if (positional.size() == 1) {
                BOOST_CHECK(positional[0].isStr());
                if (positional[0].isStr()) BOOST_CHECK_EQUAL(positional[0].get_str(), label);
            }
            UniValue named;
            BOOST_CHECK_NO_THROW(named = RPCConvertNamedValues("createmodelidentity", {"label=" + label}));
            BOOST_CHECK(named.exists("label"));
            if (named.exists("label")) {
                BOOST_CHECK(named["label"].isStr());
                if (named["label"].isStr()) BOOST_CHECK_EQUAL(named["label"].get_str(), label);
            }
        }
    }
    BOOST_CHECK(RPCConvertValues("createmodelidentity", {}).empty());
    BOOST_CHECK(RPCConvertNamedValues("createmodelidentity", {}).empty());
    // Do not disable JSON conversion for unrelated typed arguments.
    BOOST_CHECK(RPCConvertValues("removemodelrule", {"3"})[0].isNum());
    BOOST_CHECK(RPCConvertValues("setmodelpolicy", {R"({"preserve_rare":false})"})[0].isObject());
}

