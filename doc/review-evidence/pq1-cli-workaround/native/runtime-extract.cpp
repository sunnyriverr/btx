#include <openssl/ssl.h>
#include <cstdlib>
#include <cstdio>
#include <string>
namespace modelnet {
bool OpensslCliHasMlKem768(const std::string& bin)
{
    if (bin.empty()) return false;
    const std::string cmd = bin + " list -kem-algorithms 2>/dev/null";
    FILE* fp = popen(cmd.c_str(), "r");
    if (!fp) return false;
    std::string out;
    char buf[256];
    while (fgets(buf, sizeof(buf), fp) != nullptr) out += buf;
    const int rc = pclose(fp);
    return rc == 0 && out.find("MLKEM768") != std::string::npos;
}
std::string OpensslBin()
{
    if (const char* e = std::getenv("BTX_OPENSSL")) return e;
#ifdef _WIN32
    // Keep the explicit override above and the existing CLI-name fallback.
    // The POSIX shell probe is not a native Windows capability check.
    return "openssl";
#else
    static const std::string cached = [] {
        const char* cands[] = {
            "/opt/openssl-3.5.8/bin/openssl",
            "/opt/homebrew/opt/openssl@3/bin/openssl",
            "/opt/homebrew/opt/openssl/bin/openssl",
            "/usr/local/opt/openssl@3/bin/openssl",
            "/usr/local/opt/openssl/bin/openssl",
            "openssl",
        };
        for (const char* c : cands) {
            if (OpensslCliHasMlKem768(c)) return std::string{c};
        }
        return std::string{"openssl"};
    }();
    return cached;
#endif
}
void Pq1SanitizeOpenSslEnv()
{
    unsetenv("OPENSSL_CONF");
    unsetenv("OPENSSL_CONF_INCLUDE");
    unsetenv("OPENSSL_MODULES");
    unsetenv("OPENSSL_ENGINES");
}
void Pq1InitOpenSsl()
{
    Pq1SanitizeOpenSslEnv();
    OPENSSL_init_ssl(OPENSSL_INIT_NO_LOAD_CONFIG, nullptr);
}
}
