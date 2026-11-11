#define BOOST_TEST_MODULE PartialResumeQuota
#include <boost/test/included/unit_test.hpp>
#include <crypto/common.h>
#include <modelnet/catalog.h>
#include <modelnet/verified_manifest.h>
#include <util/fs.h>
#include <util/translation.h>
#include <atomic>
#include <cstdlib>
#include <cstring>
#include <fstream>
const TranslateFn G_TRANSLATION_FUN{nullptr};
struct ComponentSetup { fs::path m_path_root; ComponentSetup() {
 static unsigned n=0; m_path_root=fs::PathFromString(std::getenv("QUOTA_UNIT_DIR"))/std::to_string(++n).c_str();
 fs::create_directories(m_path_root);
}};
std::vector<unsigned char> TinySafeTensors(unsigned char tag)
{
    const std::string json = "{\"__metadata__\":{\"t\":\"" + std::to_string(static_cast<int>(tag)) + "\"}}";
    std::vector<unsigned char> st(8 + json.size(), 0);
    WriteLE64(st.data(), json.size());
    std::memcpy(st.data() + 8, json.data(), json.size());
    return st;
}

fs::path WriteTinyModel(const fs::path& dir, unsigned char tag)
{
    fs::create_directories(dir);
    const auto st = TinySafeTensors(tag);
    std::ofstream out(dir / "model.safetensors", std::ios::binary);
    out.write(reinterpret_cast<const char*>(st.data()), static_cast<std::streamsize>(st.size()));
    return dir;
}

modelnet::CatalogEntry ImportTiny(modelnet::ModelCatalog& cat, const fs::path& dir, unsigned char tag, bool pin)
{
    std::string err;
    modelnet::CatalogEntry imported;
    BOOST_REQUIRE_MESSAGE(cat.ImportPath(fs::PathToString(WriteTinyModel(dir, tag)), pin, imported, err), err);
    BOOST_REQUIRE(!imported.core.files.empty());
    return imported;
}


BOOST_FIXTURE_TEST_SUITE(modelnet_b0_disc_store_tests, ComponentSetup)
#include "regression.inc"
BOOST_AUTO_TEST_SUITE_END()
