#define BOOST_TEST_MODULE CloudBudgetRecovery
#include <boost/test/included/unit_test.hpp>
#include <modelnet/s3_store.h>
#include <util/fs.h>
#include <util/translation.h>
#include <csignal>
#include <cstdlib>
#include <exception>
#include <fstream>
#include <iterator>
#include <stdexcept>
#include <sys/resource.h>
const TranslateFn G_TRANSLATION_FUN{nullptr};
struct CloudOnlySetup {
 fs::path m_path_root;
 CloudOnlySetup() : m_path_root(fs::PathFromString(std::getenv("CLOUD_BUDGET_CASE_DIR"))) { fs::create_directories(m_path_root); }
};
constexpr char kAccess[] = "AKIATESTKEYNOTREAL00";
constexpr char kSecret[] = "super-secret-cloud-value-xyz";

void WriteCreds(const fs::path& path, const std::string& access, const std::string& secret, bool mode0600)
{
    {
        std::ofstream out(path);
        out << "aws_access_key_id=" << access << "\n";
        out << "aws_secret_access_key=" << secret << "\n";
    }
    auto perms = fs::perms::owner_read | fs::perms::owner_write;
    if (!mode0600) perms |= fs::perms::group_read | fs::perms::others_read;
    fs::permissions(path, perms, fs::perm_options::replace);
}

modelnet::CloudStoreConfig BaseCfg(const fs::path& creds, const std::string& endpoint = "https://acct.r2.cloudflarestorage.com")
{
    modelnet::CloudStoreConfig c;
    c.s3.endpoint = endpoint;
    c.s3.bucket = "btx-models";
    c.s3.prefix = "v1";
    c.s3.region = "auto";
    c.s3.use_fake = true;
    c.s3.creds.kind = modelnet::CredentialRefKind::PATH;
    c.s3.creds.value = fs::PathToString(creds);
    c.provider = modelnet::CloudProvider::AUTO;
    c.layout = modelnet::CloudObjectLayout::AUTO;
    return c;
}

// Positive Windows fixtures use the supported ENV source. Keep BaseCfg's PATH
// source available for permission-refusal checks; never relax product policy.
class ScopedCloudCredentials
{
#ifdef WIN32
    test::ScopedEnvVar m_credentials{"BTX_TEST_CLOUD_FIXTURE_CREDS",
        (std::string{"aws_access_key_id="} + kAccess +
         "\naws_secret_access_key=" + kSecret + "\n").c_str()};
#endif

public:
    modelnet::CloudStoreConfig Config(const fs::path& creds, const std::string& endpoint = "https://acct.r2.cloudflarestorage.com") const
    {
        auto cfg = BaseCfg(creds, endpoint);
#ifdef WIN32
        cfg.s3.creds = {modelnet::CredentialRefKind::ENV, "BTX_TEST_CLOUD_FIXTURE_CREDS"};
#endif
        return cfg;
    }

    std::string RpcRef(const fs::path& creds) const
    {
#ifdef WIN32
        return "env:BTX_TEST_CLOUD_FIXTURE_CREDS";
#else
        return fs::PathToString(creds);
#endif
    }
};
modelnet::Digest48 ArtifactFill(unsigned char b)
{
    modelnet::Digest48 d;
    d.data.fill(b);
    return d;
}
BOOST_FIXTURE_TEST_SUITE(modelnet_cloud_tests, CloudOnlySetup)
BOOST_AUTO_TEST_CASE(cloud_12f_calendar_rollback_preserves_exhausted_allowance)
{
    const ScopedCloudCredentials credentials;
    const fs::path creds = m_path_root / "cloud_12f_calendar_rollback_preserves_exhausted_allowance-creds";
    WriteCreds(creds, kAccess, kSecret, true);
    // 2026-03-01 01:00 UTC; the preceding day is in the preceding month.
    constexpr int64_t day = 1772326800;
    constexpr int64_t next_month = 1775005200;
    for (int quota = 0; quota < 4; ++quota) {
        BOOST_TEST_CONTEXT("quota=" << quota) {
            auto cfg = credentials.Config(creds);
            const auto suffix = fs::PathFromString("cloud_12f_calendar_rollback_preserves_exhausted_allowance-" + std::to_string(quota));
            cfg.budget_state_path = m_path_root / suffix / "budget.json";
            cfg.s3.fake_store_dir = m_path_root / suffix / "origin";
            if (quota == 0) cfg.budget_gets_per_day = 1;
            if (quota == 1) cfg.budget_bytes_per_day = 6;
            if (quota == 2) cfg.budget_gets_per_month = 1;
            if (quota == 3) cfg.budget_bytes_per_month = 6;
            auto attempt = [&](int64_t clock, bool expected, bool seed = false) {
                // Reopen both the actual saved budget and the persistent fake origin.
                modelnet::S3PieceStore store{cfg};
                store.SetClockForTests(clock);
                std::string err;
                BOOST_REQUIRE_MESSAGE(store.Init(err), err);
                if (seed) {
                    std::istringstream input{"daycap"};
                    BOOST_REQUIRE_MESSAGE(store.PutObject("calendar", input, 6, err), err);
                }
                uint64_t size{0};
                BOOST_REQUIRE_MESSAGE(store.HeadObject("calendar", size, err), err);
                BOOST_REQUIRE_EQUAL(size, 6);
                const auto before = store.FakeForTests()->GetCount();
                std::vector<unsigned char> got;
                const bool allowed = store.GetObject("calendar", 0, 0, got, err);
                BOOST_CHECK_EQUAL(allowed, expected);
                BOOST_CHECK_EQUAL(store.FakeForTests()->GetCount() - before, expected ? 1 : 0);
                if (allowed) {
                    BOOST_CHECK_EQUAL(std::string(got.begin(), got.end()), "daycap");
                } else {
                    BOOST_CHECK(err.find("budget") != std::string::npos);
                }
            };
            attempt(day, true, true);
            attempt(day, false);
            attempt(day - 86400, false);
            attempt(day, false);
            attempt(day, false);
            attempt(quota < 2 ? day + 86400 : next_month, true);
            attempt(quota < 2 ? day + 86400 : next_month, false);
        }
    }
}

BOOST_AUTO_TEST_CASE(cloud_12g_calendar_rollback_preserves_remaining_allowance)
{
    const ScopedCloudCredentials credentials;
    const fs::path creds = m_path_root / "cloud_12g_calendar_rollback_preserves_remaining_allowance-creds";
    WriteCreds(creds, kAccess, kSecret, true);
    // 2026-03-01 01:00 UTC; the preceding day is in the preceding month.
    constexpr int64_t day = 1772326800;
    constexpr int64_t next_month = 1775005200;
    for (int quota = 0; quota < 4; ++quota) {
        BOOST_TEST_CONTEXT("quota=" << quota) {
            auto cfg = credentials.Config(creds);
            const auto suffix = fs::PathFromString("cloud_12g_calendar_rollback_preserves_remaining_allowance-" + std::to_string(quota));
            cfg.budget_state_path = m_path_root / suffix / "budget.json";
            cfg.s3.fake_store_dir = m_path_root / suffix / "origin";
            if (quota == 0) cfg.budget_gets_per_day = 2;
            if (quota == 1) cfg.budget_bytes_per_day = 12;
            if (quota == 2) cfg.budget_gets_per_month = 2;
            if (quota == 3) cfg.budget_bytes_per_month = 12;
            auto attempt = [&](int64_t clock, bool expected, bool seed = false) {
                // Reopen both the actual saved budget and the persistent fake origin.
                modelnet::S3PieceStore store{cfg};
                store.SetClockForTests(clock);
                std::string err;
                BOOST_REQUIRE_MESSAGE(store.Init(err), err);
                if (seed) {
                    std::istringstream input{"daycap"};
                    BOOST_REQUIRE_MESSAGE(store.PutObject("calendar", input, 6, err), err);
                }
                uint64_t size{0};
                BOOST_REQUIRE_MESSAGE(store.HeadObject("calendar", size, err), err);
                BOOST_REQUIRE_EQUAL(size, 6);
                const auto before = store.FakeForTests()->GetCount();
                std::vector<unsigned char> got;
                const bool allowed = store.GetObject("calendar", 0, 0, got, err);
                BOOST_CHECK_EQUAL(allowed, expected);
                BOOST_CHECK_EQUAL(store.FakeForTests()->GetCount() - before, expected ? 1 : 0);
                if (allowed) {
                    BOOST_CHECK_EQUAL(std::string(got.begin(), got.end()), "daycap");
                } else {
                    BOOST_CHECK(err.find("budget") != std::string::npos);
                }
            };
            attempt(day, true, true);
            attempt(day - 86400, true); // The remaining allowance stays usable.
            attempt(day - 86400, false);
            attempt(day, false);
            const auto forward = quota < 2 ? day + 86400 : next_month;
            attempt(forward, true);
            attempt(forward, true);
            attempt(forward, false);
        }
    }
}

BOOST_AUTO_TEST_CASE(cloud_12b_calendar_day_budget_persists)
{
    const ScopedCloudCredentials credentials;
    const fs::path creds = m_path_root / "cloud-12b-creds";
    WriteCreds(creds, kAccess, kSecret, true);
    auto cfg = credentials.Config(creds);
    cfg.budget_gets_per_day = 1;
    cfg.budget_state_path = m_path_root / "cloud-12b-budget.json";
    const int64_t day0 = 86400 * 20000 + 3600;
    {
        modelnet::S3PieceStore store{cfg};
        store.SetClockForTests(day0);
        std::string err;
        BOOST_REQUIRE_MESSAGE(store.Init(err), err);
        const auto art = ArtifactFill(0x45);
        const fs::path src = m_path_root / "cloud-12b.bin";
        {
            std::ofstream out(src, std::ios::binary);
            out << "daycap";
        }
        BOOST_REQUIRE(store.PutSourceFile(art, 0, src, 6, 1, err));
        std::vector<unsigned char> got;
        BOOST_REQUIRE(store.GetSourceFile(art, 0, got, err));
        BOOST_CHECK(!store.GetSourceFile(art, 0, got, err));
        BOOST_CHECK(err.find("budget") != std::string::npos);
        const UniValue h = store.HealthJson();
        BOOST_CHECK(h["budget_gets_per_day_limited"].get_bool());
        BOOST_CHECK_EQUAL(h["budget_gets_remaining_day"].getInt<int64_t>(), 0);
        store.SetClockForTests(day0 + 86400);
        BOOST_REQUIRE(store.GetSourceFile(art, 0, got, err));
        BOOST_CHECK_EQUAL(store.HealthJson()["budget_gets_remaining_day"].getInt<int64_t>(), 0);
    }
    {
        modelnet::S3PieceStore store{cfg};
        store.SetClockForTests(day0 + 86400);
        std::string err;
        BOOST_REQUIRE_MESSAGE(store.Init(err), err);
        const auto art = ArtifactFill(0x45);
        std::vector<unsigned char> got;
        BOOST_CHECK(!store.GetSourceFile(art, 0, got, err));
        BOOST_CHECK(err.find("budget") != std::string::npos);
    }
}

BOOST_AUTO_TEST_SUITE_END()
