#include <util/translation.h>
const TranslateFn G_TRANSLATION_FUN{nullptr};
#include <node/autoupdate.h>
#include <crypto/sha256.h>
#include <uint256.h>
#include <tinyformat.h>
#include <util/strencodings.h>
#include <cassert>
#include <fstream>
#include <iostream>
#include <map>
#include <sys/stat.h>

std::vector<unsigned char> Bytes(std::string_view text)
{
    return {text.begin(), text.end()};
}

std::string SHA256Hex(const std::vector<unsigned char>& bytes)
{
    uint256 digest;
    CSHA256().Write(bytes.data(), bytes.size()).Finalize(digest.begin());
    return HexStr(Span<const unsigned char>{digest.begin(), digest.size()});
}

struct FakeFetcher final : node::AutoUpdateFetcher {
    struct Reply {
        bool ok{true};
        int status{200};
        std::string final_url;
        std::vector<unsigned char> body;
        std::string error;
    };

    std::map<std::string, Reply> replies;
    std::vector<std::string> calls;

    node::AutoUpdateFetchResult Fetch(std::string_view url, size_t) override
    {
        calls.emplace_back(url);
        const auto it = replies.find(std::string{url});
        if (it == replies.end()) return {.ok = false, .error = "not found"};
        const auto& reply = it->second;
        return {
            .ok = reply.ok,
            .status = reply.status,
            .final_url = reply.final_url.empty() ? std::string{url} : reply.final_url,
            .body = reply.body,
            .error = reply.error,
        };
    }
};

struct FakeVerifier final : node::AutoUpdateSignatureVerifier {
    bool valid{true};
    int calls{0};
    std::vector<unsigned char> last_message;
    std::vector<unsigned char> last_signature;

    bool Verify(std::string_view, const std::vector<unsigned char>& message, const std::vector<unsigned char>& signature) override
    {
        ++calls;
        last_message = message;
        last_signature = signature;
        return valid;
    }
};

struct RecordingRunner final : node::AutoUpdateCommandRunner {
    int calls{0};
    node::AutoUpdateManifest last_manifest;
    std::vector<unsigned char> last_script;

    bool LaunchInstaller(const node::AutoUpdateConfig&,
                         const node::AutoUpdateManifest& manifest,
                         const std::vector<unsigned char>& script) override
    {
        ++calls;
        last_manifest = manifest;
        last_script = script;
        return true;
    }
};

node::AutoUpdateConfig TestConfig()
{
    node::AutoUpdateConfig config;
    config.enabled = true;
    config.seamless = true;
    config.dev_origin = true;
    config.manifest_url = "http://updates.test/version.txt";
    config.trusted_origin = "http://updates.test";
    config.release_pubkey = "test-pubkey";
    config.telemetry = false;
    return config;
}

std::string Manifest(std::string version,
                     std::string script_url,
                     std::string sig_url,
                     std::string script_sha256 = {})
{
    std::string hash_field;
    if (!script_sha256.empty()) {
        hash_field = strprintf(R"(,"script_sha256":"%s")", script_sha256);
    }
    return strprintf(
        R"({"version":"%s","script_url":"%s","sig_url":"%s"%s})",
        version,
        script_url,
        sig_url,
        hash_field);
}

struct Harness {
    node::AutoUpdateConfig config{TestConfig()};
    FakeFetcher fetcher;
    FakeVerifier verifier;
    RecordingRunner runner;
    std::vector<unsigned char> script{Bytes("#!/bin/sh\nexit 0\n")};
    std::string script_hash{SHA256Hex(script)};

    void AddManifest(std::string version = "99.0.0",
                     std::string script_url = "http://updates.test/install.sh",
                     std::string sig_url = "http://updates.test/version.txt.sig",
                     std::string hash = {})
    {
        if (hash.empty()) hash = script_hash;
        fetcher.replies[config.manifest_url] = {
            .final_url = config.manifest_url,
            .body = Bytes(Manifest(std::move(version), std::move(script_url), std::move(sig_url), std::move(hash))),
        };
    }

    void AddSignature(std::string sig_url = "http://updates.test/version.txt.sig")
    {
        fetcher.replies[std::move(sig_url)] = {.body = {0x01, 0x02, 0x03, 0xff}};
    }

    void AddScript(std::string script_url = "http://updates.test/install.sh")
    {
        fetcher.replies[std::move(script_url)] = {.body = script};
    }

    node::AutoUpdateCheckResult Run()
    {
        return node::CheckForAutoUpdate(config, fetcher, verifier, runner);
    }

    node::AutoUpdateCheckResult RunWith(node::AutoUpdateSignatureVerifier& verifier_in)
    {
        return node::CheckForAutoUpdate(config, fetcher, verifier_in, runner);
    }
};


int main(int argc, char** argv)
{
    assert(argc == 2);
    const fs::path root{argv[1]};
    int regressions = 0;
    for (const std::string name : {"missing", "unreadable", "dangling", "empty", "higher"}) {
        const auto datadir = root / fs::u8path(name);
        const auto dir = datadir / "autoupdate";
        fs::create_directories(dir);
        const auto floor = dir / "highest-accepted-version";
        if (name == "unreadable" || name == "empty" || name == "higher") {
            std::ofstream file(floor);
            if (name == "unreadable" || name == "higher") file << "100.0.0\n";
        }
        if (name == "unreadable") {
            assert(chmod(floor.c_str(), 0) == 0);
            assert(!std::ifstream(floor).is_open());
        }
        if (name == "dangling") fs::create_symlink(dir / "missing-target", floor);
        Harness h;
        h.config.datadir = datadir;
        h.AddManifest();
        h.AddSignature();
        h.AddScript();
        const auto result = h.Run();
        using Status = node::AutoUpdateStatus;
        if (name == "missing") {
            assert(result.status == Status::LAUNCHED && h.runner.calls == 1);
        } else if (name == "higher") {
            assert(result.status == Status::NOT_NEWER && h.runner.calls == 0);
        } else if (name == "empty") {
            assert(result.status == Status::BAD_MANIFEST && h.runner.calls == 0);
        } else if (result.status != Status::BAD_MANIFEST) {
            assert(result.status == Status::LAUNCHED && h.runner.calls == 1);
            ++regressions;
        } else {
            assert(h.runner.calls == 0 && result.detail.find("unreadable") != std::string::npos);
        }
        std::cout << name << " status=" << static_cast<int>(result.status)
                  << " installer_calls=" << h.runner.calls << " detail=" << result.detail << "\n";
    }
    assert(regressions == 0 || regressions == 2);
    return regressions ? 42 : 0;
}
