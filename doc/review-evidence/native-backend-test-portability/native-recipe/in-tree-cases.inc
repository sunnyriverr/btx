BOOST_AUTO_TEST_CASE(scoped_environment_restores_values)
{
    constexpr const char* name = "BTX_TEST_BACKEND_SCOPED_ENV";
    const ScopedEnvVar original{name, "original"};
    BOOST_REQUIRE(std::getenv(name) != nullptr);
    BOOST_CHECK_EQUAL(std::getenv(name), "original");
    {
        const ScopedEnvVar replacement{name, "replacement"};
        BOOST_REQUIRE(std::getenv(name) != nullptr);
        BOOST_CHECK_EQUAL(std::getenv(name), "replacement");
        {
            const ScopedEnvVar removed{name, nullptr};
            BOOST_CHECK(std::getenv(name) == nullptr);
        }
        BOOST_REQUIRE(std::getenv(name) != nullptr);
        BOOST_CHECK_EQUAL(std::getenv(name), "replacement");
    }
    BOOST_REQUIRE(std::getenv(name) != nullptr);
    BOOST_CHECK_EQUAL(std::getenv(name), "original");
}

BOOST_AUTO_TEST_CASE(scoped_environment_restores_absence)
{
    constexpr const char* name = "BTX_TEST_BACKEND_SCOPED_ENV";
    const ScopedEnvVar absent{name, nullptr};
    BOOST_CHECK(std::getenv(name) == nullptr);
    {
        const ScopedEnvVar temporary{name, "temporary"};
        BOOST_REQUIRE(std::getenv(name) != nullptr);
        BOOST_CHECK_EQUAL(std::getenv(name), "temporary");
    }
    BOOST_CHECK(std::getenv(name) == nullptr);
}

