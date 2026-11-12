#include <modelnet/realm_channel.h>

#include <csignal>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <iterator>
#include <stdexcept>
#include <sys/resource.h>

using modelnet::RealmRollout;
namespace fs = std::filesystem;

void Require(bool ok, const std::string& message)
{
    if (!ok) throw std::runtime_error(message);
}

std::string ReadBytes(const fs::path& path)
{
    std::ifstream in(path, std::ios::binary);
    Require(in.is_open(), "bundle disappeared");
    return {std::istreambuf_iterator<char>(in), {}};
}

bool WriteShort(const RealmRollout& rollout, const fs::path& path, std::string& err)
{
    struct rlimit saved{};
    Require(getrlimit(RLIMIT_FSIZE, &saved) == 0, "getrlimit");
    const auto previous = std::signal(SIGXFSZ, SIG_IGN);
    Require(previous != SIG_ERR, "ignore SIGXFSZ");
    struct rlimit limited{saved};
    limited.rlim_cur = 8;
    Require(setrlimit(RLIMIT_FSIZE, &limited) == 0, "apply file-size limit");
    bool ok;
    try {
        ok = rollout.WriteOfflineBundle(path, "alpha", err);
    } catch (...) {
        setrlimit(RLIMIT_FSIZE, &saved);
        std::signal(SIGXFSZ, previous);
        throw;
    }
    Require(setrlimit(RLIMIT_FSIZE, &saved) == 0, "restore limit");
    Require(std::signal(SIGXFSZ, previous) != SIG_ERR, "restore signal");
    return ok;
}

void RequireLoaded(const fs::path& path, int64_t sequence, const std::string& body)
{
    RealmRollout loaded;
    std::string err;
    Require(loaded.ReadOfflineBundle(path, "alpha", err), "read bundle: " + err);
    Require(loaded.Threshold("alpha") == 2 && loaded.Quorum("alpha", {"a", "c"}) &&
            !loaded.Quorum("alpha", {"a", "b"}) && !loaded.Quorum("alpha", {"a"}) &&
            loaded.ChannelSequence("alpha") == sequence && loaded.ChannelBody("alpha") == body,
            "bundle did not restore the expected channel and quorum");
}

int main(int argc, char** argv)
{
    if (argc != 2) return 2;
    try {
        const fs::path root{argv[1]};
        const auto bundle = root / "bundle.txt";
        const auto control = root / "control.txt";
        RealmRollout rollout;
        std::string err;
        Require(rollout.SetPolicy("alpha", 2, {"c", "a", "b"}, err), "set policy");
        Require(rollout.RevokeAttestor("alpha", "b", err), "revoke attestor");
        Require(rollout.PublishChannel("alpha", 0, "h0", err), "publish sequence zero");
        Require(rollout.PublishChannel("alpha", 1, "body-hash", err), "publish sequence one");
        Require(rollout.AdvanceRing("alpha", "policy", "policy", 0, err), "advance ring");
        Require(rollout.WriteOfflineBundle(bundle, "alpha", err), "write old bundle");
        RequireLoaded(bundle, 1, "body-hash");
        const std::string old = ReadBytes(bundle);
        const std::string expected_old =
            "BTX035-OFFLINE-1\nrealm=alpha\nthreshold=2\npinned=3\na\nb\nc\n"
            "revoked=1\nb\nchannel=1\nbody=body-hash\n";
        Require(old == expected_old, "old fixture bytes");
        Require(rollout.PublishChannel("alpha", 2, "replacement-hash", err), "publish sequence two");
        Require(rollout.WriteOfflineBundle(control, "alpha", err), "write healthy control");
        RequireLoaded(control, 2, "replacement-hash");
        const std::string expected = ReadBytes(control);
        Require(old != expected, "new fixture must differ from old");

        const bool saved = WriteShort(rollout, bundle, err);
        Require(!saved && err == "BTX035_BUNDLE", "write did not report the expected fault");
        std::cout << "fault_error=" << err << '\n';
        const std::string partial = ReadBytes(bundle);
        RealmRollout reopened;
        const bool loaded = reopened.ReadOfflineBundle(bundle, "alpha", err);
        if (loaded) {
            Require(partial == old, "failed replacement changed the old bytes");
            RequireLoaded(bundle, 1, "body-hash");
        } else {
            Require(err == "BTX035_BUNDLE" && partial.size() == 8 && partial == expected.substr(0, 8),
                    "unexpected fault outcome");
            Require(reopened.Threshold("alpha") == 0 && reopened.ChannelSequence("alpha") == -1,
                    "failed import applied bundle state");
        }
        std::cout << "old_bytes=" << old.size() << " after_bytes=" << partial.size()
                  << " preserved=" << (partial == old) << " reopened=" << loaded << '\n';

        Require(rollout.WriteOfflineBundle(bundle, "alpha", err), "same-path retry failed");
        Require(ReadBytes(bundle) == expected, "retry differs from healthy export");
        RequireLoaded(bundle, 2, "replacement-hash");
        std::cout << "retry_bytes=" << expected.size()
                  << " exact_bytes=1 imported_sequence=2 quorum_preserved=1\n";
        Require(loaded && partial == old, "old bundle did not survive");
    } catch (const std::exception& e) {
        std::cerr << e.what() << '\n';
        return 1;
    }
}
