#define BOOST_TEST_MODULE pq1_component
#include <boost/test/included/unit_test.hpp>
#include <modelnet/transport_pq.h>
#include <openssl/ssl.h>
#include <openssl/bio.h>
#include <filesystem>
#include <fstream>
#include <sstream>
#include <tinyformat.h>
namespace fs {using path=std::filesystem::path;using std::filesystem::create_directories;std::string PathToString(const path& p){return p.string();}}
namespace modelnet {std::string OpensslBin();}
const fs::path m_path_root=std::getenv("PQ1_TEST_ROOT");
std::string ReadAll(const fs::path& p){std::ifstream f(p);return std::string(std::istreambuf_iterator<char>(f),{});}
BOOST_AUTO_TEST_CASE(pq1_handshake_mlkem768)
{
    const fs::path dir = m_path_root / "pq1";
    fs::create_directories(dir);
    const fs::path key = dir / "key.pem";
    const fs::path cert = dir / "cert.pem";
    const fs::path openssl_err = dir / "openssl.err";
    const std::string openssl = modelnet::OpensslBin();
    const std::string cmd = strprintf(
        "%s req -x509 -new -newkey mldsa44 -keyout '%s' -out '%s' -nodes -subj '/CN=btx-model-test' -days 1 >'%s' 2>&1",
        openssl, fs::PathToString(key), fs::PathToString(cert), fs::PathToString(openssl_err));
    const int rc = std::system(cmd.c_str());
    BOOST_REQUIRE_MESSAGE(rc == 0, "openssl mldsa44 cert failed rc=" + std::to_string(rc) +
                                         " bin=" + openssl + " " + ReadAll(openssl_err));
    const std::string cert_pem = ReadAll(cert);
    const std::string key_pem = ReadAll(key);
    modelnet::Pq1Context server;
    modelnet::Pq1Context client;
    BOOST_REQUIRE_MESSAGE(server.Ready(), server.Error());
    BOOST_REQUIRE_MESSAGE(client.Ready(), client.Error());
    std::string err;
    BOOST_REQUIRE(server.LoadSelfSignedMlDsa(cert_pem, key_pem, err));
    BOOST_REQUIRE(client.LoadSelfSignedMlDsa(cert_pem, key_pem, err));
    modelnet::NegotiatedPq1 n;
    BOOST_REQUIRE_MESSAGE(modelnet::HandshakePair(server, client, n, err), err);
    BOOST_CHECK(modelnet::IsStrictPq1(n));
    BOOST_TEST_MESSAGE("PQ1 group=" + n.group + " cipher=" + n.ciphersuite + " ver=" + n.tls_version);
}
BOOST_AUTO_TEST_CASE(pq1_rejects_hybrid_peer)
{
    modelnet::Pq1Context client;
    BOOST_REQUIRE(client.Ready());
    SSL_CTX* rogue = SSL_CTX_new(TLS_method());
    BOOST_REQUIRE(rogue);
    SSL_CTX_set_min_proto_version(rogue, TLS1_3_VERSION);
    SSL_CTX_set_max_proto_version(rogue, TLS1_3_VERSION);
    BOOST_REQUIRE_EQUAL(SSL_CTX_set1_groups_list(rogue, "X25519MLKEM768"), 1);
    SSL* ssl_s = SSL_new(rogue);
    SSL* ssl_c = SSL_new(static_cast<SSL_CTX*>(client.SslCtx()));
    BIO *b1 = nullptr, *b2 = nullptr;
    BOOST_REQUIRE_EQUAL(BIO_new_bio_pair(&b1, 0, &b2, 0), 1);
    SSL_set_bio(ssl_s, b1, b1);
    SSL_set_bio(ssl_c, b2, b2);
    SSL_set_accept_state(ssl_s);
    SSL_set_connect_state(ssl_c);
    int rc_c = 0, rc_s = 0;
    for (int i = 0; i < 32; ++i) {
        rc_c = SSL_do_handshake(ssl_c);
        rc_s = SSL_do_handshake(ssl_s);
        if (rc_c == 1 && rc_s == 1) break;
    }
    BOOST_CHECK(!(rc_c == 1 && rc_s == 1));
    SSL_free(ssl_c);
    SSL_free(ssl_s);
    SSL_CTX_free(rogue);
}
