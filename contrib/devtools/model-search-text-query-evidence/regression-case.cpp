BOOST_AUTO_TEST_CASE(rpc_convert_values_model_search_text_or_object)
{
    // Search accepts text or a query object. JSON-looking text must stay text.
    const std::vector<std::string> text_queries{
        "", "llama 70m", "70", "true", "null", R"(["llama"])", "{not-json", R"("llama")", "text=llama",
    };
    const std::vector<std::string> object_queries{"{}", R"({"text":"llama","limit":5})"};
    for (const auto* method : {"searchmodels", "searchpublishers", "searchcollections"}) {
        BOOST_TEST_CONTEXT(method) {
            BOOST_CHECK_EQUAL(RPCConvertValues(method, {}).size(), 0U);
            BOOST_CHECK_EQUAL(RPCConvertNamedValues(method, {}).size(), 0U);
            for (const auto& query : text_queries) {
                BOOST_TEST_CONTEXT(query) {
                    UniValue positional;
                    UniValue named;
                    BOOST_CHECK_NO_THROW(positional = RPCConvertValues(method, {query}));
                    BOOST_CHECK_NO_THROW(named = RPCConvertNamedValues(method, {"query=" + query}));
                    BOOST_CHECK_EQUAL(positional.size(), 1U);
                    BOOST_CHECK(named.exists("query"));
                    if (positional.size() == 1) {
                        BOOST_CHECK(positional[0].isStr());
                        if (positional[0].isStr()) BOOST_CHECK_EQUAL(positional[0].get_str(), query);
                    }
                    if (named.exists("query")) {
                        BOOST_CHECK(named["query"].isStr());
                        if (named["query"].isStr()) BOOST_CHECK_EQUAL(named["query"].get_str(), query);
                    }
                }
            }
            for (const auto& query : object_queries) {
                const UniValue positional = RPCConvertValues(method, {query});
                const UniValue named = RPCConvertNamedValues(method, {"query=" + query});
                BOOST_CHECK(positional[0].isObject());
                BOOST_CHECK(named["query"].isObject());
                BOOST_CHECK_EQUAL(positional[0].write(), query);
                BOOST_CHECK_EQUAL(named["query"].write(), query);
            }
        }
    }
}

