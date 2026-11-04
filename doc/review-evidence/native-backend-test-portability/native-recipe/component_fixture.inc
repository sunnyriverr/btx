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
