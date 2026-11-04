#define BOOST_TEST_MODULE BackendScopedEnvironment
#include <boost/test/included/unit_test.hpp>
#include <cstdlib>
#include <string>
#include <cstdio>
class ScopedEnvVar
{
public:
    ScopedEnvVar(const char* name, const char* value) : m_name(name)
    {
        const char* current = std::getenv(name);
        if (current != nullptr) {
            m_had_original = true;
            m_original = current;
        }

#if defined(_WIN32)
        _putenv_s(name, value != nullptr ? value : "");
#else
        if (value != nullptr) {
            setenv(name, value, 1);
        } else {
            unsetenv(name);
        }
#endif
    }

    ~ScopedEnvVar() {}

private:
    const char* m_name;
    bool m_had_original{false};
    std::string m_original;
};
// Independent fixture: check the caller's initial environment after all cases.
// Use process exit rather than Boost assertions after framework teardown.
struct OriginalEnvironmentFixture
{
    bool had{std::getenv("BTX_TEST_BACKEND_SCOPED_ENV") != nullptr};
    std::string value{had ? std::getenv("BTX_TEST_BACKEND_SCOPED_ENV") : ""};
    ~OriginalEnvironmentFixture()
    {
        const char* after = std::getenv("BTX_TEST_BACKEND_SCOPED_ENV");
        if ((after != nullptr) != had || (had && after != nullptr && after != value)) {
            std::fputs("Initial environment was not restored\n", stderr);
            std::exit(90);
        }
    }
};
BOOST_GLOBAL_FIXTURE(OriginalEnvironmentFixture);

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

