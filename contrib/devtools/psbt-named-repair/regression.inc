BOOST_AUTO_TEST_CASE(rpc_convert_walletprocesspsbt_named_options)
{
    const std::string psbt{"opaque-psbt"};
    for (const std::string field : {"adjust_timelocks", "htlc_presign"}) {
        for (const std::string text : {"false", "true"}) {
            const UniValue named = RPCConvertNamedValues("walletprocesspsbt",
                {"psbt=" + psbt, "sign=false", "finalize=false", field + "=" + text});
            BOOST_CHECK_EQUAL(named["psbt"].get_str(), psbt);
            BOOST_CHECK_EQUAL(named["sign"].get_bool(), false);
            BOOST_CHECK_EQUAL(named["finalize"].get_bool(), false);
            BOOST_CHECK(named[field].isBool());
            if (named[field].isBool()) BOOST_CHECK_EQUAL(named[field].get_bool(), text == "true");
        }
        // JSON strings stay strings; conversion must not coerce a wrong type
        // into a valid Boolean or bypass the wallet's type checks.
        const UniValue wrong_type = RPCConvertNamedValues("walletprocesspsbt", {field + "=\"false\""});
        BOOST_CHECK(wrong_type[field].isStr());
        BOOST_CHECK_EQUAL(wrong_type[field].get_str(), "false");
        BOOST_CHECK_THROW(RPCConvertNamedValues("walletprocesspsbt", {field + "=not-json"}), std::runtime_error);
    }
    const std::string leaf = "{\"" + std::string(64, '1') + ":0\":0}";
    UniValue expected_leaf;
    BOOST_REQUIRE(expected_leaf.read(leaf));
    const UniValue named_leaf = RPCConvertNamedValues("walletprocesspsbt", {"p2mr_leaf=" + leaf});
    BOOST_CHECK(named_leaf["p2mr_leaf"].isObject());
    BOOST_CHECK_EQUAL(named_leaf["p2mr_leaf"].write(), expected_leaf.write());
    BOOST_CHECK(RPCConvertNamedValues("walletprocesspsbt", {"p2mr_leaf={}"})["p2mr_leaf"].isObject());
    BOOST_CHECK(RPCConvertNamedValues("walletprocesspsbt", {"p2mr_leaf=[]"})["p2mr_leaf"].isArray());
    BOOST_CHECK_THROW(RPCConvertNamedValues("walletprocesspsbt", {"p2mr_leaf=not-json"}), std::runtime_error);

    const std::string options = R"({"sign":false,"finalize":false,"adjust_timelocks":false,"htlc_presign":false,"p2mr_leaf":{}})";
    UniValue expected_options;
    BOOST_REQUIRE(expected_options.read(options));
    const UniValue positional = RPCConvertValues("walletprocesspsbt", {psbt, options});
    const UniValue named = RPCConvertNamedValues("walletprocesspsbt", {"psbt=" + psbt, "options=" + options});
    BOOST_CHECK_EQUAL(positional[0].get_str(), psbt);
    BOOST_CHECK_EQUAL(positional[1].write(), expected_options.write());
    BOOST_CHECK_EQUAL(named["psbt"].get_str(), psbt);
    BOOST_CHECK_EQUAL(named["options"].write(), expected_options.write());

    const UniValue legacy = RPCConvertValues("walletprocesspsbt", {psbt, "false", "ALL", "false", "false"});
    BOOST_CHECK_EQUAL(legacy[0].get_str(), psbt);
    BOOST_CHECK_EQUAL(legacy[1].get_bool(), false);
    BOOST_CHECK_EQUAL(legacy[2].get_str(), "ALL");
    BOOST_CHECK_EQUAL(legacy[3].get_bool(), false);
    BOOST_CHECK_EQUAL(legacy[4].get_bool(), false);
}

