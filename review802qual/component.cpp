#include <bitcoin-build-config.h>
#include <crypto/common.h>
#include <modelnet/catalog.h>
#include <modelnet/crypto.h>
#include <modelnet/helper.h>
#include <modelnet/release.h>
#include <modelnet/types.h>
#include <test/util/setup_common.h>
#include <univalue.h>
#include <util/fs.h>
#include <util/translation.h>
#include <algorithm>
#include <fstream>
#include <iterator>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>
const TranslateFn G_TRANSLATION_FUN{nullptr};
using namespace modelnet;
#define BOOST_REQUIRE(x) do { if (!(x)) throw std::runtime_error(#x); } while (0)
#define BOOST_CHECK(x) BOOST_REQUIRE(x)
#define BOOST_REQUIRE_MESSAGE(x,m) do { if (!(x)) throw std::runtime_error(std::string(#x)+": "+(m)); } while (0)
#define BOOST_CHECK_EQUAL(a,b) BOOST_REQUIRE((a)==(b))
#define BOOST_REQUIRE_EQUAL(a,b) BOOST_REQUIRE((a)==(b))
#define BOOST_REQUIRE_GT(a,b) BOOST_REQUIRE((a)>(b))
#define BOOST_REQUIRE_GE(a,b) BOOST_REQUIRE((a)>=(b))
#define BOOST_REQUIRE_LE(a,b) BOOST_REQUIRE((a)<=(b))
fs::path m_path_root;
namespace {

void WriteTinySafeTensors(const fs::path& dir, const std::string& header)
{
    fs::create_directories(dir);
    std::vector<unsigned char> st(8 + header.size());
    WriteLE64(st.data(), header.size());
    std::copy(header.begin(), header.end(), st.begin() + 8);
    std::ofstream out(dir / "toy.safetensors", std::ios::binary);
    out.write(reinterpret_cast<const char*>(st.data()), static_cast<std::streamsize>(st.size()));
}

bool CallHelper(ModelCatalog& cat, const std::string& method, const UniValue& params, UniValue& result, std::string& code)
{
    UniValue req(UniValue::VOBJ);
    req.pushKV("method", method);
    req.pushKV("params", params);
    result = UniValue{};
    code.clear();
    std::string err;
    return DispatchHelperRpc(cat, req, result, code, err);
}

UniValue OneParam(const UniValue& v)
{
    UniValue params(UniValue::VARR);
    params.push_back(v);
    return params;
}

UniValue CreateParams(const std::string& uri, char secret)
{
    UniValue body(UniValue::VOBJ);
    body.pushKV("uri", uri);
    body.pushKV("secret32_hex", std::string(64, secret));
    body.pushKV("refund_height", 100000);
    body.pushKV("target_atoms", 5'000'000);
    return OneParam(body);
}

} // namespace
// Join the saved campaign to its verified ciphertext bytes and its own key.
// Metadata or a primitive cipher round trip alone cannot prove this contract.
void created_release_ciphertext_opens_with_its_own_campaign_secret()
{
    const fs::path root = m_path_root / "release-ciphertext-bytes";
    WriteTinySafeTensors(root / "a.dir", "{}");
    WriteTinySafeTensors(root / "b.dir", "{\"__metadata__\":{\"name\":\"different-model\"}}");
    ModelCatalog cat{root, 8 << 20};
    const fs::path helper_dir = cat.Store().Root().parent_path();
    const auto input_bytes = [&](const fs::path& path) {
        std::ifstream in(path, std::ios::binary);
        BOOST_REQUIRE(in.good());
        return std::vector<unsigned char>((std::istreambuf_iterator<char>(in)), std::istreambuf_iterator<char>());
    };
    const std::vector<std::vector<unsigned char>> original{
        input_bytes(root / "a.dir" / "toy.safetensors"),
        input_bytes(root / "b.dir" / "toy.safetensors")};
    BOOST_REQUIRE(original[0] != original[1]);
    const std::vector<std::vector<unsigned char>> secret{
        std::vector<unsigned char>(32, 0xaa), std::vector<unsigned char>(32, 0xbb)};
    std::vector<Digest48> ciphertext_ids;
    std::vector<std::string> release_ids;
    UniValue res;
    std::string code;
    for (size_t i = 0; i < original.size(); ++i) {
        const fs::path dir = root / (i == 0 ? "a.dir" : "b.dir");
        BOOST_REQUIRE_MESSAGE(CallHelper(cat, "hostmodel", OneParam(fs::PathToString(dir)), res, code), code);
        const std::string uri = res["uri"].get_str();
        BOOST_REQUIRE_MESSAGE(CallHelper(cat, "createmodelrelease", CreateParams(uri, i == 0 ? 'a' : 'b'), res, code), code);
        const std::string release_id = res["release_id"].get_str();
        release_ids.push_back(release_id);
        BOOST_REQUIRE_MESSAGE(CallHelper(cat, "getmodelrelease", UniValue(UniValue::VARR), res, code), code);
        bool found{false};
        for (const auto& campaign : res["campaigns"].getValues()) {
            if (campaign["release_id"].get_str() != release_id) continue;
            found = true;
            // The base silently points at the plaintext instead of storing ciphertext.
            BOOST_REQUIRE(campaign["ciphertext_artifact_id"].get_str() != campaign["artifact_id"].get_str());
            Digest48 ciphertext;
            std::string err;
            BOOST_REQUIRE_MESSAGE(Digest48::FromHex(campaign["ciphertext_artifact_id"].get_str(), ciphertext, err), err);
            ciphertext_ids.push_back(ciphertext);
        }
        BOOST_REQUIRE(found);
    }
    BOOST_REQUIRE_EQUAL(ciphertext_ids.size(), 2U);
    BOOST_REQUIRE(ciphertext_ids[0] != ciphertext_ids[1]);
    BOOST_REQUIRE(release_ids[0] != release_ids[1]);
    const auto check_stored = [&](ModelCatalog& store, size_t index) {
        CatalogEntry entry;
        BOOST_REQUIRE(store.Find(ciphertext_ids[index], entry));
        BOOST_REQUIRE_EQUAL(entry.core.files.size(), 1U);
        const auto& file = entry.core.files[0];
        BOOST_CHECK_EQUAL(file.path, "tmp-cipher.btxenc");
        BOOST_REQUIRE_GT(file.size, 0U);
        BOOST_REQUIRE_LE(file.size, RELEASE_WRAP_MAX_BYTES);
        std::vector<unsigned char> wrapped;
        std::string err;
        const uint32_t count = static_cast<uint32_t>((file.size + PIECE_SIZE - 1) / PIECE_SIZE);
        for (uint32_t piece_index = 0; piece_index < count; ++piece_index) {
            std::vector<unsigned char> piece;
            std::vector<Digest48> proof;
            uint64_t file_size{0};
            BOOST_REQUIRE_MESSAGE(store.GetVerifiedPiece(entry.artifact_id, 0, piece_index, piece, proof, file_size, err), err);
            BOOST_REQUIRE_EQUAL(file_size, file.size);
            wrapped.insert(wrapped.end(), piece.begin(), piece.end());
        }
        BOOST_REQUIRE_GE(wrapped.size(), static_cast<size_t>(file.size));
        wrapped.resize(static_cast<size_t>(file.size));
        BOOST_REQUIRE(LooksLikeBtxEnc2(wrapped));
        std::vector<unsigned char> plain;
        BOOST_REQUIRE_MESSAGE(UnwrapBtxEnc2(secret[index], wrapped, plain, err), err);
        BOOST_CHECK(plain == original[index]);
        std::vector<unsigned char> wrong;
        err.clear();
        BOOST_CHECK(!UnwrapBtxEnc2(secret[1 - index], wrapped, wrong, err));
        BOOST_CHECK(wrong.empty());
    };
    // Re-read the first ciphertext after creating the second release too.
    for (size_t i = 0; i < original.size(); ++i) check_stored(cat, i);
    // Fresh catalog metadata and pieces, without pretending to restart helper globals.
    ModelCatalog reloaded{root, 8 << 20};
    std::vector<ReleaseCampaign> campaigns;
    std::string err;
    BOOST_REQUIRE_MESSAGE(LoadCampaigns(helper_dir, campaigns, err), err);
    BOOST_REQUIRE_EQUAL(campaigns.size(), 2U);
    for (size_t i = 0; i < original.size(); ++i) {
        const auto saved = std::find_if(campaigns.begin(), campaigns.end(), [&](const ReleaseCampaign& c) {
            return c.release_id.Hex() == release_ids[i];
        });
        BOOST_REQUIRE(saved != campaigns.end());
        BOOST_CHECK(saved->ciphertext_artifact_id == ciphertext_ids[i]);
        check_stored(reloaded, i);
    }
}

int main(int argc, char** argv)
{
    try {
        if (argc != 1) return 2;
        BasicTestingSetup setup{ChainType::REGTEST};
        m_path_root = setup.m_path_root;
        created_release_ciphertext_opens_with_its_own_campaign_secret();
        std::cout << "PASS stored_ciphertext_own_secret_exact_bytes_and_catalog_reload\n";
        return 0;
    } catch (const std::exception& e) {
        std::cerr << "FAIL " << e.what() << "\n";
        return 1;
    }
}
