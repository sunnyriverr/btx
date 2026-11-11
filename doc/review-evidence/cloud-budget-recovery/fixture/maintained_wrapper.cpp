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
#include "startup-regression.inc"
BOOST_AUTO_TEST_SUITE_END()
