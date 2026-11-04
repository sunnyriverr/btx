
#include <modelnet/generate.h>
#include <univalue.h>
#include <util/fs.h>
#include <algorithm>
#include <atomic>
#include <chrono>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <fstream>
#include <iostream>
#include <map>
#include <mutex>
#include <thread>
#include <vector>
#ifndef _WIN32
#include <crypto/common.h>
#include <crypto/sha256.h>
#include <util/strencodings.h>
#include <util/subprocess.h>
#include <fcntl.h>
#include <poll.h>
#include <signal.h>
#include <sys/resource.h>
#include <sys/socket.h>
#include <sys/stat.h>
#include <sys/un.h>
#include <sys/wait.h>
#include <unistd.h>
#ifdef __linux__
#include <sys/prctl.h>
#endif
#endif
// Logging is the only substituted dependency; it has no acceptance assertions.
template <typename... Args> void LogPrintf(const char*, const Args&...) {}
namespace modelnet {

bool IsExecutableFile(const fs::path& p)
{
    if (!fs::exists(p) || !fs::is_regular_file(p)) return false;
#ifdef _WIN32
    // The local runners require fork/exec, which is unsupported on Windows.
    // Existence or CRT read/write attributes cannot qualify execution.
    return false;
#else
    return ::access(fs::PathToString(p).c_str(), X_OK) == 0;
#endif
}

HostGenerateProfile ProbeHostGenerateProfile()
{
    HostGenerateProfile p;
    if (const char* e = std::getenv("BTX_LLAMA_CLI")) {
        const fs::path path = fs::PathFromString(e);
        if (IsExecutableFile(path)) {
            p.llama_cli = true;
            p.llama_cli_path = e;
        }
    }
    if (const char* e = std::getenv("BTX_MODEL_GENERATE")) {
        const fs::path path = fs::PathFromString(e);
        if (IsExecutableFile(path)) {
            p.generate_adapter = true;
            p.generate_adapter_path = e;
        }
    }
    if (const char* e = std::getenv("BTX_MODEL_CUDA_LOADER")) {
        const fs::path path = fs::PathFromString(e);
        if (IsExecutableFile(path)) {
            p.cuda_loader = true;
            p.cuda_loader_path = e;
        }
    }
    if (const char* e = std::getenv("BTX_EXL3_CLI")) {
        const fs::path path = fs::PathFromString(e);
        if (IsExecutableFile(path)) {
            p.exl3_cli = true;
            p.exl3_cli_path = e;
        }
    }
    return p;
}

UniValue HostGenerateProfileJson(const HostGenerateProfile& p)
{
    UniValue o(UniValue::VOBJ);
    o.pushKV("schema_version", 2);
    o.pushKV("llama_cli", p.llama_cli);
    o.pushKV("generate_adapter", p.generate_adapter);
    o.pushKV("cuda_loader", p.cuda_loader);
    o.pushKV("exl3_cli", p.exl3_cli);
    UniValue formats(UniValue::VARR);
    if (p.generate_adapter) formats.push_back("safetensors");
    if (p.llama_cli || p.generate_adapter) formats.push_back("gguf");
    if (p.exl3_cli) formats.push_back("exl3");
    o.pushKV("formats", formats);
    UniValue backends(UniValue::VARR);
    if (p.generate_adapter) backends.push_back("BTX_MODEL_GENERATE");
    if (p.llama_cli) backends.push_back("llama.cpp");
    if (p.exl3_cli) backends.push_back("BTX_EXL3_CLI");
    if (p.cuda_loader) backends.push_back("safetensors-cuda-smoke");
    o.pushKV("backends", backends);
    o.pushKV("can_generate", p.generate_adapter || p.llama_cli || p.exl3_cli);
    o.pushKV("cuda_smoke_is_not_generate", true);
    o.pushKV("trust_remote_code", false);
    o.pushKV("remote_inference", false);
    o.pushKV("automatic_spend_atoms", 0);
    o.pushKV("execution_profile_unqualified", 0);
    o.pushKV("note",
             "Local generate only for host-compatible GGUF (BTX_LLAMA_CLI), "
             "allowlisted SafeTensors architectures (BTX_MODEL_GENERATE), or "
             "allowlisted EXL3 architectures (BTX_EXL3_CLI). EXL3 is not sent to llama.cpp. "
             "CUDA --hold --smoke is not a generate. Granite hybrid is not GGUF.");
    return o;
}

namespace {
#ifndef _WIN32
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
#endif
} // namespace

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


bool StickyWorldWritableDir(const fs::path& dir)
{
    const std::string s = fs::PathToString(dir);
    return s == "/tmp" || s == "/var/tmp" || s == "/dev/shm";
}

bool LooksLikeTmpFallbackSock(const fs::path& sock)
{
    const std::string s = fs::PathToString(sock);
    return s.find("/tmp/btx-md-") != std::string::npos || s.find("/var/tmp/btx-md-") != std::string::npos;
}

#if !defined(WIN32) && !defined(__APPLE__)

bool OwnerOnlyDir(const fs::path& dir, uid_t owner)
{
    struct stat st {};
    return ::lstat(fs::PathToString(dir).c_str(), &st) == 0 && S_ISDIR(st.st_mode) && st.st_uid == owner &&
           (st.st_mode & (S_IWGRP | S_IWOTH)) == 0;
}

#endif

fs::path RuntimeSockDir()
{
    const char* xdg = std::getenv("XDG_RUNTIME_DIR");
    if (xdg && xdg[0] == '/') return fs::PathFromString(xdg) / "btx-modeld";
#ifdef __APPLE__
    // macOS sets no XDG_RUNTIME_DIR. The per-user temporary directory
    // (/var/folders/.../T/) belongs to the user, is mode 0700, and is short
    // enough for sun_path. ListenUnix() still makes btx-modeld/ 0700 inside it.
    char tmp[1024];
    const size_t n = ::confstr(_CS_DARWIN_USER_TEMP_DIR, tmp, sizeof(tmp));
    if (n > 1 && n <= sizeof(tmp) && tmp[0] == '/') return fs::PathFromString(tmp) / "btx-modeld";
#elif !defined(WIN32)
    // XDG_RUNTIME_DIR is often missing under cron, su, sudo and in
    // containers. Use the login runtime directory it would have named, or
    // /run for root. Nobody else can add entries to either, so btx-modeld/
    // cannot be pre-created there by another user; ListenUnix() still makes
    // it 0700 and checks its owner.
    const uid_t uid = ::getuid();
    const fs::path user_run = fs::PathFromString(strprintf("/run/user/%u", static_cast<unsigned>(uid)));
    if (OwnerOnlyDir(user_run, uid)) return user_run / "btx-modeld";
    if (uid == 0 && OwnerOnlyDir(fs::PathFromString("/run"), 0)) return fs::PathFromString("/run/btx-modeld");
#endif
    return {};
}

fs::path UnixRpcListenPath(const fs::path& requested)
{
#ifndef WIN32
    const std::string p = fs::PathToString(requested);
    const bool too_long = p.size() >= sizeof(sockaddr_un::sun_path);
    const bool sticky = StickyWorldWritableDir(requested.parent_path()) || LooksLikeTmpFallbackSock(requested);
    if (!too_long && !sticky) return requested;
    const fs::path dir = RuntimeSockDir();
    if (dir.empty()) return requested;
    unsigned char digest[32];
    CSHA256().Write(UCharCast(p.data()), p.size()).Finalize(digest);
    const fs::path sock = dir / fs::PathFromString(HexStr(std::vector<unsigned char>(digest, digest + 8)) + ".sock");
    if (fs::PathToString(sock).size() >= sizeof(sockaddr_un::sun_path)) return requested;
    return sock;
#else
    return requested;
#endif
}

bool UnixSocketSafeToAdopt(const fs::path& sock, std::string& err)
{
#ifdef _WIN32
    (void)sock;
    err = "helper Unix RPC is not supported on this platform";
    return false;
#else
    err.clear();
    if (LooksLikeTmpFallbackSock(sock) || StickyWorldWritableDir(sock.parent_path())) {
        err = "tmp socket is not a helper";
        return false;
    }
    const std::string p = fs::PathToString(sock);
    struct stat st {};
    if (::lstat(p.c_str(), &st) != 0) {
        err = "socket missing";
        return false;
    }
    if (!S_ISSOCK(st.st_mode) || S_ISLNK(st.st_mode)) {
        err = S_ISLNK(st.st_mode) ? "socket symlink" : "not a socket";
        return false;
    }
    if ((st.st_mode & S_IWOTH) != 0) {
        err = "world-writable socket";
        return false;
    }
    const std::string parent = fs::PathToString(sock.parent_path());
    struct stat pst {};
    if (parent.empty() || ::lstat(parent.c_str(), &pst) != 0 || !S_ISDIR(pst.st_mode) ||
        (pst.st_mode & S_IWOTH) != 0) {
        err = "socket directory is world-writable";
        return false;
    }
    return true;
#endif
}

bool UnixConnectedPeerIsSelf(int fd, std::string& err)
{
#ifdef _WIN32
    (void)fd;
    err = "helper peer identity is not supported on this platform";
    return false;
#else
    err.clear();
#if defined(SO_PEERCRED)
    struct ucred cred {};
    socklen_t len = sizeof(cred);
    if (::getsockopt(fd, SOL_SOCKET, SO_PEERCRED, &cred, &len) != 0) {
        err = "peercred";
        return false;
    }
    if (cred.uid != static_cast<uid_t>(::getuid())) {
        err = "peer uid";
        return false;
    }
    return true;
#else
    (void)fd;
    return true;
#endif
#endif
}

void CloseWorkerDescriptors()
{
#ifndef _WIN32
    subprocess::detail::subprocess_close_all_fds(/*except_fd=*/-1);
#endif
}

// A worker PID is meaningful only for the POSIX runners below.
#ifdef _WIN32
using WorkerPid = int;
#else
using WorkerPid = pid_t;
#endif

bool RunCudaLoader(const fs::path& loader, const fs::path& dir, UniValue& out, std::string& err, WorkerPid* hold_pid)
{
#ifdef _WIN32
    (void)loader; (void)dir; (void)out;
    if (hold_pid) *hold_pid = 0;
    err = "CUDA loader process is not supported on this platform";
    return false;
#else
    std::error_code ec;
    if (!fs::is_regular_file(loader, ec) || ec) {
        err = "BTX_MODEL_CUDA_LOADER is not a regular file";
        return false;
    }
    int pipefd[2];
    if (pipe(pipefd) != 0) {
        err = "pipe";
        return false;
    }
    const pid_t pid = fork();
    if (pid < 0) {
        close(pipefd[0]);
        close(pipefd[1]);
        err = "fork";
        return false;
    }
    if (pid == 0) {
        close(pipefd[0]);
        if (dup2(pipefd[1], STDOUT_FILENO) < 0) _exit(127);
        close(pipefd[1]);
        CloseWorkerDescriptors();
        const std::string loader_s = fs::PathToString(loader);
        const std::string dir_s = fs::PathToString(dir);
        if (hold_pid) {
            const char* argv[] = {loader_s.c_str(), "--dir", dir_s.c_str(), "--hold", "--smoke", nullptr};
            execv(loader_s.c_str(), const_cast<char* const*>(argv));
        } else {
            const char* argv[] = {loader_s.c_str(), "--dir", dir_s.c_str(), "--smoke", nullptr};
            execv(loader_s.c_str(), const_cast<char* const*>(argv));
        }
        _exit(127);
    }
    close(pipefd[1]);
    std::string stdout_s;
    char buf[4096];
    ssize_t nread = 0;
    while ((nread = ::read(pipefd[0], buf, sizeof(buf))) > 0) {
        stdout_s.append(buf, static_cast<size_t>(nread));
        if (stdout_s.find('\n') != std::string::npos) break;
        if (stdout_s.size() > 1024 * 1024) break;
    }
    close(pipefd[0]);
    const size_t nl = stdout_s.find('\n');
    const std::string line = nl == std::string::npos ? stdout_s : stdout_s.substr(0, nl);
    if (!out.read(line) || !out.isObject()) {
        int st = 0;
        kill(pid, SIGTERM);
        waitpid(pid, &st, 0);
        err = "cuda loader json";
        return false;
    }
    if (out.exists("ok") && !out["ok"].get_bool()) {
        int st = 0;
        kill(pid, SIGTERM);
        waitpid(pid, &st, 0);
        err = out.exists("error") && out["error"].isStr() ? out["error"].get_str() : "cuda loader failed";
        return false;
    }
    if (hold_pid) {
        *hold_pid = pid;
        return true;
    }
    int st = 0;
    waitpid(pid, &st, 0);
    if (!WIFEXITED(st) || WEXITSTATUS(st) != 0) {
        err = out.exists("error") && out["error"].isStr() ? out["error"].get_str() : "cuda loader failed";
        return false;
    }
    return true;
#endif
}

struct ResidentCuda {
    WorkerPid pid{0};
    uint64_t bytes_on_device{0};
    std::string device_name;
    UniValue cuda;
};

std::mutex g_resident_mu;
std::map<std::string, ResidentCuda> g_resident;

bool PidAlive(WorkerPid pid)
{
#ifdef _WIN32
    (void)pid;
    return false;
#else
    if (pid <= 0) return false;
    return ::kill(pid, 0) == 0 || errno == EPERM;
#endif
}

void StopResidentLocked(const std::string& key)
{
#ifdef _WIN32
    // Windows cannot create a resident worker through these runners.
    g_resident.erase(key);
#else
    auto it = g_resident.find(key);
    if (it == g_resident.end()) return;
    const pid_t pid = it->second.pid;
    g_resident.erase(it);
    if (pid <= 0) return;
    ::kill(pid, SIGTERM);
    for (int i = 0; i < 50; ++i) {
        int st = 0;
        if (waitpid(pid, &st, WNOHANG) == pid) return;
        usleep(100000);
    }
    ::kill(pid, SIGKILL);
    int st = 0;
    waitpid(pid, &st, 0);
#endif
}

void StopResident(const std::string& key)
{
    std::lock_guard<std::mutex> lock(g_resident_mu);
    StopResidentLocked(key);
}

bool MaybeRunInferCmd(const fs::path& checkout, UniValue& result, std::string& err)
{
#ifdef _WIN32
    (void)checkout; (void)result;
    const char* cmd = std::getenv("BTX_MODEL_INFER_CMD");
    if (!cmd || cmd[0] == '\0') return true;
    err = "inference process is not supported on this platform";
    return false;
#else
    const char* cmd = std::getenv("BTX_MODEL_INFER_CMD");
    if (!cmd || cmd[0] == '\0') return true;
    int pipefd[2];
    if (pipe(pipefd) != 0) {
        err = "infer pipe";
        return false;
    }
    const pid_t pid = fork();
    if (pid < 0) {
        close(pipefd[0]);
        close(pipefd[1]);
        err = "infer fork";
        return false;
    }
    if (pid == 0) {
        close(pipefd[0]);
        if (dup2(pipefd[1], STDOUT_FILENO) < 0) _exit(127);
        close(pipefd[1]);
        CloseWorkerDescriptors();
        const std::string exe = cmd;
        const std::string dir_s = fs::PathToString(checkout);
        const char* argv[] = {exe.c_str(), dir_s.c_str(), nullptr};
        execv(exe.c_str(), const_cast<char* const*>(argv));
        _exit(127);
    }
    close(pipefd[1]);
    std::string stdout_s;
    char buf[4096];
    ssize_t nread = 0;
    while ((nread = ::read(pipefd[0], buf, sizeof(buf))) > 0) {
        stdout_s.append(buf, static_cast<size_t>(nread));
        if (stdout_s.size() > 256 * 1024) break;
    }
    close(pipefd[0]);
    int st = 0;
    waitpid(pid, &st, 0);
    const size_t nl = stdout_s.find('\n');
    const std::string line = nl == std::string::npos ? stdout_s : stdout_s.substr(0, nl);
    result.pushKV("infer_cmd", cmd);
    result.pushKV("infer_stdout", line);
    if (!WIFEXITED(st) || WEXITSTATUS(st) != 0) {
        err = "BTX_MODEL_INFER_CMD failed";
        result.pushKV("infer_ok", false);
        return false;
    }
    result.pushKV("infer_ok", true);
    result.pushKV("generated", !line.empty());
    return true;
#endif
}

bool RunGenerateAdapter(const fs::path& exe, const fs::path& dir, const std::string& prompt,
                        int max_new_tokens, UniValue& out, std::string& err)
{
#ifdef _WIN32
    (void)exe; (void)dir; (void)prompt; (void)max_new_tokens; (void)out;
    err = "generate adapter process is not supported on this platform";
    return false;
#else
    if (!fs::exists(exe) || !fs::is_regular_file(exe)) {
        err = "BTX_MODEL_GENERATE is not a regular file";
        return false;
    }
    int inpipe[2] = {-1, -1};
    int outpipe[2] = {-1, -1};
    if (pipe(inpipe) != 0) {
        err = "generate pipe";
        return false;
    }
    if (pipe(outpipe) != 0) {
        close(inpipe[0]);
        close(inpipe[1]);
        err = "generate pipe";
        return false;
    }
#if defined(__linux__)
    // The child compares its parent with this pid, not with 1: a helper that
    // is itself pid 1 (a container entrypoint) is a live parent.
    const pid_t parent = getpid();
#endif
    const pid_t pid = fork();
    if (pid < 0) {
        close(inpipe[0]);
        close(inpipe[1]);
        close(outpipe[0]);
        close(outpipe[1]);
        err = "generate fork";
        return false;
    }
    if (pid == 0) {
#if defined(__linux__)
        // Match the helper's parent-death watch so a crashed parent cannot
        // leave the adapter running. A new process group lets the timeout
        // signal the adapter and any process it forks.
        if (prctl(PR_SET_PDEATHSIG, SIGTERM) == 0 && getppid() != parent) _exit(127);
#endif
        // Failure leaves the child in the helper's group; the timeout then
        // signals the pid directly. Do not skip exec.
        setpgid(0, 0);
        close(inpipe[1]);
        close(outpipe[0]);
        if (dup2(inpipe[0], STDIN_FILENO) < 0) _exit(127);
        if (dup2(outpipe[1], STDOUT_FILENO) < 0) _exit(127);
        if (inpipe[0] != STDIN_FILENO) close(inpipe[0]);
        if (outpipe[1] != STDOUT_FILENO) close(outpipe[1]);
        CloseWorkerDescriptors();
        const std::string exe_s = fs::PathToString(exe);
        const std::string dir_s = fs::PathToString(dir);
        const std::string n_s = std::to_string(max_new_tokens);
        const char* argv[] = {exe_s.c_str(), "--dir", dir_s.c_str(), "--max-new-tokens", n_s.c_str(), nullptr};
        execv(exe_s.c_str(), const_cast<char* const*>(argv));
        _exit(127);
    }
    setpgid(pid, pid);
    close(inpipe[0]);
    inpipe[0] = -1;
    close(outpipe[1]);
    outpipe[1] = -1;

    // Same bound as the documented BTX_GENERATE_TIMEOUT_S default. The 1 MiB
    // stdout cap still stops a child that streams without a newline.
    constexpr int kTimeoutMs = 600 * 1000;
    constexpr size_t kStdoutCap = 1024 * 1024;
    const auto deadline = std::chrono::steady_clock::now() + std::chrono::milliseconds(kTimeoutMs);
    auto remaining_ms = [&]() -> int {
        const auto now = std::chrono::steady_clock::now();
        if (now >= deadline) return 0;
        auto ms = std::chrono::duration_cast<std::chrono::milliseconds>(deadline - now).count();
        if (ms > kTimeoutMs) ms = kTimeoutMs;
        return static_cast<int>(ms);
    };
    auto set_nonblock = [](int fd) {
        const int flags = fcntl(fd, F_GETFL, 0);
        if (flags >= 0) fcntl(fd, F_SETFL, flags | O_NONBLOCK);
    };
    set_nonblock(inpipe[1]);
    set_nonblock(outpipe[0]);
    auto close_parent = [&]() {
        if (inpipe[1] >= 0) {
            close(inpipe[1]);
            inpipe[1] = -1;
        }
        if (outpipe[0] >= 0) {
            close(outpipe[0]);
            outpipe[0] = -1;
        }
    };
    auto signal_child = [&](int sig) {
        if (kill(-pid, sig) != 0) kill(pid, sig);
    };
    auto reap = [&](bool kill_now) -> int {
        int st = 0;
        bool got = false;
        auto try_reap = [&]() -> bool {
            for (;;) {
                const pid_t w = waitpid(pid, &st, WNOHANG);
                if (w == pid) {
                    got = true;
                    return true;
                }
                if (w < 0) {
                    if (errno == EINTR) continue;
                    return got;
                }
                return false;
            }
        };
        if (!kill_now) {
            while (!try_reap()) {
                if (remaining_ms() <= 0) break;
                usleep(50 * 1000);
            }
        }
        if (got) return st;
        signal_child(SIGTERM);
        const auto grace = std::chrono::steady_clock::now() + std::chrono::milliseconds(200);
        while (!try_reap() && std::chrono::steady_clock::now() < grace) {
            usleep(20 * 1000);
        }
        if (!got) {
            signal_child(SIGKILL);
            for (;;) {
                const pid_t w = waitpid(pid, &st, 0);
                if (w == pid) {
                    got = true;
                    break;
                }
                if (w < 0 && errno != EINTR) break;
            }
        }
        if (!got) st = 0x7f;
        return st;
    };

    UniValue req(UniValue::VOBJ);
    req.pushKV("prompt", prompt);
    req.pushKV("max_new_tokens", max_new_tokens);
    const std::string body = req.write() + "\n";
    size_t off = 0;
    while (off < body.size()) {
        const int left = remaining_ms();
        if (left <= 0) {
            close_parent();
            reap(true);
            err = "generate adapter timeout";
            return false;
        }
        pollfd pfd{};
        pfd.fd = inpipe[1];
        pfd.events = POLLOUT;
        const int pr = poll(&pfd, 1, left);
        if (pr < 0) {
            if (errno == EINTR) continue;
            close_parent();
            reap(true);
            err = "generate stdin";
            return false;
        }
        if (pr == 0) {
            close_parent();
            reap(true);
            err = "generate adapter timeout";
            return false;
        }
        const size_t chunk = std::min<size_t>(body.size() - off, 4096);
        const ssize_t n = ::write(inpipe[1], body.data() + off, chunk);
        if (n < 0) {
            if (errno == EINTR || errno == EAGAIN) continue;
            close_parent();
            reap(true);
            err = "generate stdin";
            return false;
        }
        if (n == 0) continue;
        off += static_cast<size_t>(n);
    }
    close(inpipe[1]);
    inpipe[1] = -1;

    std::string stdout_s;
    char buf[4096];
    bool timed_out = false;
    bool hit_cap = false;
    while (stdout_s.find('\n') == std::string::npos) {
        const int left = remaining_ms();
        if (left <= 0) {
            timed_out = true;
            break;
        }
        pollfd pfd{};
        pfd.fd = outpipe[0];
        pfd.events = POLLIN;
        const int pr = poll(&pfd, 1, left);
        if (pr < 0) {
            if (errno == EINTR) continue;
            break;
        }
        if (pr == 0) {
            timed_out = true;
            break;
        }
        const ssize_t nread = ::read(outpipe[0], buf, sizeof(buf));
        if (nread < 0) {
            if (errno == EINTR || errno == EAGAIN) continue;
            break;
        }
        if (nread == 0) break;
        stdout_s.append(buf, static_cast<size_t>(nread));
        if (stdout_s.find('\n') != std::string::npos) break;
        if (stdout_s.size() > kStdoutCap) {
            hit_cap = true;
            break;
        }
    }
    close(outpipe[0]);
    outpipe[0] = -1;
    // No complete line: the child is still inside the deadline or already over
    // a limit. Kill and reap now. Waiting out the rest of the window would
    // leave a silent adapter attached to this RPC.
    if (stdout_s.find('\n') == std::string::npos) {
        reap(true);
        if (timed_out) err = "generate adapter timeout";
        else if (hit_cap) err = "generate adapter output limit";
        else err = "generate adapter output";
        return false;
    }
    const int st = reap(false);
    const size_t nl = stdout_s.find('\n');
    const std::string line = nl == std::string::npos ? stdout_s : stdout_s.substr(0, nl);
    if (!out.read(line) || !out.isObject()) {
        err = "generate adapter json";
        return false;
    }
    if (out.exists("ok") && !out["ok"].get_bool()) {
        err = out.exists("error") && out["error"].isStr() ? out["error"].get_str() : "generate adapter failed";
        return false;
    }
    if (!WIFEXITED(st) || WEXITSTATUS(st) != 0) {
        if (err.empty()) err = "generate adapter exit";
        return false;
    }
    return true;
#endif
}

bool RunLlamaGenerate(const fs::path& exe, const fs::path& gguf, const std::string& prompt,
                      int max_new_tokens, UniValue& out, std::string& err)
{
#ifdef _WIN32
    (void)exe; (void)gguf; (void)prompt; (void)max_new_tokens; (void)out;
    err = "llama process is not supported on this platform";
    return false;
#else
    if (!fs::exists(exe) || !fs::is_regular_file(exe) ||
        ::access(fs::PathToString(exe).c_str(), X_OK) != 0) {
        err = "BTX_LLAMA_CLI is not executable";
        return false;
    }
    int outpipe[2];
    if (pipe(outpipe) != 0) {
        err = "llama pipe";
        return false;
    }
    const pid_t pid = fork();
    if (pid < 0) {
        close(outpipe[0]);
        close(outpipe[1]);
        err = "llama fork";
        return false;
    }
    if (pid == 0) {
        close(outpipe[0]);
        if (dup2(outpipe[1], STDOUT_FILENO) < 0) _exit(127);
        const int nullfd = open("/dev/null", O_WRONLY);
        if (nullfd >= 0) {
            dup2(nullfd, STDERR_FILENO);
            close(nullfd);
        }
        close(outpipe[1]);
        CloseWorkerDescriptors();
        const std::string exe_s = fs::PathToString(exe);
        const std::string m_s = fs::PathToString(gguf);
        const std::string n_s = std::to_string(max_new_tokens);
        const char* argv[] = {
            exe_s.c_str(), "-m", m_s.c_str(), "-p", prompt.c_str(), "-n", n_s.c_str(),
            "--no-display-prompt", nullptr};
        execv(exe_s.c_str(), const_cast<char* const*>(argv));
        _exit(127);
    }
    close(outpipe[1]);
    std::string stdout_s;
    char buf[4096];
    ssize_t nread = 0;
    while ((nread = ::read(outpipe[0], buf, sizeof(buf))) > 0) {
        stdout_s.append(buf, static_cast<size_t>(nread));
        if (stdout_s.size() > 1024 * 1024) break;
    }
    close(outpipe[0]);
    int st = 0;
    waitpid(pid, &st, 0);
    if (!WIFEXITED(st) || WEXITSTATUS(st) != 0) {
        err = "llama-cli exit";
        return false;
    }
    while (!stdout_s.empty() && (stdout_s.back() == '\n' || stdout_s.back() == '\r')) stdout_s.pop_back();
    out = UniValue(UniValue::VOBJ);
    out.pushKV("ok", true);
    out.pushKV("generated", true);
    out.pushKV("text", stdout_s);
    out.pushKV("backend", "llama.cpp");
    out.pushKV("format", "gguf");
    out.pushKV("remote_inference", false);
    return true;
#endif
}


int ListenUnix(fs::path& path, std::string& err)
{
#ifdef _WIN32
    (void)path;
    err = "helper Unix RPC is not supported on this platform";
    return -1;
#else
    const fs::path requested = path;
    path = UnixRpcListenPath(requested);
    std::string p = fs::PathToString(path);
    if (path != requested) {
        LogPrintf("btx-modeld: unix RPC path %s is not a private sun_path; listening at %s\n",
                  fs::PathToString(requested), p);
    }
    if (LooksLikeTmpFallbackSock(path) || StickyWorldWritableDir(path.parent_path())) {
        err = "refusing helper socket in a world-writable directory";
        return -1;
    }
    const fs::path parent = path.parent_path();
    const std::string parent_s = fs::PathToString(parent);
    try {
        if (!parent_s.empty()) fs::create_directories(parent);
    } catch (const fs::filesystem_error&) {
        err = "unix dir mode";
        return -1;
    }
    if (parent_s.empty() || ::chmod(parent_s.c_str(), 0700) != 0) {
        err = "unix dir mode";
        return -1;
    }
    struct stat pst {};
    if (::lstat(parent_s.c_str(), &pst) != 0 || !S_ISDIR(pst.st_mode) || (pst.st_mode & 0777) != 0700 ||
        pst.st_uid != static_cast<uid_t>(::getuid())) {
        err = "unix dir not private";
        return -1;
    }
    ::unlink(p.c_str());
    const int fd = ::socket(AF_UNIX, SOCK_STREAM, 0);
    if (fd < 0) {
        err = "unix socket";
        return -1;
    }
    sockaddr_un addr{};
    addr.sun_family = AF_UNIX;
    if (p.size() >= sizeof(addr.sun_path)) {
        err = "unix path too long";
        close(fd);
        return -1;
    }
    std::strncpy(addr.sun_path, p.c_str(), sizeof(addr.sun_path) - 1);
    if (::bind(fd, reinterpret_cast<sockaddr*>(&addr), sizeof(addr)) != 0) {
        err = "unix bind/listen failed";
        close(fd);
        return -1;
    }
    // fchmod() on a bound AF_UNIX socket does not reach the path: Linux
    // returns 0 and leaves the mode unchanged, macOS returns EINVAL. Set the
    // mode on the path; the 0700 parent stays the access check.
    if (::chmod(p.c_str(), 0600) != 0 || listen(fd, 16) != 0) {
        err = "unix socket mode";
        close(fd);
        ::unlink(p.c_str());
        return -1;
    }
    return fd;
#endif
}

#ifndef _WIN32

bool WaitFd(int fd, bool want_write, int timeout_ms, std::atomic<bool>* stop, std::string& err)
{
    const auto deadline = std::chrono::steady_clock::now() + std::chrono::milliseconds(timeout_ms);
    while (!stop || !stop->load()) {
        const auto now = std::chrono::steady_clock::now();
        if (now >= deadline) {
            err = "timeout";
            return false;
        }
        auto left = std::chrono::duration_cast<std::chrono::milliseconds>(deadline - now).count();
        int slice = 250;
        if (left < slice) slice = static_cast<int>(left);
        if (slice <= 0) {
            err = "timeout";
            return false;
        }
        pollfd p{};
        p.fd = fd;
        p.events = want_write ? POLLOUT : POLLIN;
        const int r = poll(&p, 1, slice);
        if (r < 0) {
            if (errno == EINTR) continue;
            err = "poll";
            return false;
        }
        if (r > 0) {
            if (p.revents & POLLNVAL) {
                err = "socket closed";
                return false;
            }
            if (want_write) {
                if (p.revents & POLLOUT) return true;
                if (p.revents & (POLLERR | POLLHUP)) {
                    err = "socket closed";
                    return false;
                }
                continue;
            }
            // POLLIN|POLLHUP is the normal unix-RPC close: peer wrote the
            // reply and closed. Drain via recv(); do not fail the wait.
            if (p.revents & (POLLIN | POLLHUP | POLLERR)) return true;
            continue;
        }
    }
    err = "stopped";
    return false;
}

constexpr int PQ1_IDLE_MS = 30000;

std::string RecvUntil(int fd, size_t cap, std::atomic<bool>* stop, int timeout_ms = PQ1_IDLE_MS)
{
    std::string out;
    char buf[4096];
    while (out.size() < cap) {
        if (stop && stop->load()) break;
        std::string werr;
        if (!WaitFd(fd, false, timeout_ms, stop, werr)) break;
        const ssize_t n = ::recv(fd, buf, sizeof(buf), 0);
        if (n <= 0) {
            if (n < 0 && errno == EAGAIN) continue;
            break;
        }
        out.append(buf, static_cast<size_t>(n));
        if (out.find('\n') != std::string::npos) break;
        if (out.find("\r\n\r\n") != std::string::npos) break;
    }
    return out;
}

#endif

constexpr size_t MAX_RPC_BODY = 256 * 1024;

constexpr int UNIX_RPC_REPLY_MS = 120 * 1000;

constexpr int UNIX_RPC_LONG_REPLY_MS = 24 * 60 * 60 * 1000;

int UnixRpcReplyTimeoutMs(const std::string& method)
{
    if (method == "waitformodelevent" || method == "importmodel" || method == "hostmodel" ||
        method == "getmodel" || method == "scanmodelwatch" || method == "executemodelimport" ||
        method == "importbtxpackage" || method == "exportmodelpath" || method == "loadmodel" ||
        method == "unloadmodel" || method == "generatemodel" || method == "removemodel") {
        return UNIX_RPC_LONG_REPLY_MS;
    }
    return UNIX_RPC_REPLY_MS;
}

bool CallUnixRpc(const fs::path& socket_path, const std::string& method, const UniValue& params, UniValue& result, std::string& err)
{
#ifdef _WIN32
    (void)socket_path; (void)method; (void)params; (void)result;
    err = "helper Unix RPC is not supported on this platform";
    return false;
#else
    const int fd = ::socket(AF_UNIX, SOCK_STREAM, 0);
    if (fd < 0) {
        err = "unix socket";
        return false;
    }
    sockaddr_un addr{};
    addr.sun_family = AF_UNIX;
    const std::string p = fs::PathToString(UnixRpcListenPath(socket_path));
    if (p.size() >= sizeof(addr.sun_path)) {
        err = "unix path too long";
        close(fd);
        return false;
    }
    std::strncpy(addr.sun_path, p.c_str(), sizeof(addr.sun_path) - 1);
    if (connect(fd, reinterpret_cast<sockaddr*>(&addr), sizeof(addr)) != 0) {
        err = "helper unix connect failed (btx-modeld not running)";
        close(fd);
        return false;
    }
    UniValue req(UniValue::VOBJ);
    req.pushKV("jsonrpc", "1.0");
    req.pushKV("id", "model");
    req.pushKV("method", method);
    req.pushKV("params", params);
    const std::string wire = req.write() + "\n";
    if (::send(fd, wire.data(), wire.size(), 0) < 0) {
        err = "unix write";
        close(fd);
        return false;
    }
    ::shutdown(fd, SHUT_WR);
    const std::string raw = RecvUntil(fd, MAX_RPC_BODY, nullptr, UnixRpcReplyTimeoutMs(method));
    close(fd);
    UniValue reply;
    if (!reply.read(raw) || !reply.isObject()) {
        err = "helper reply json";
        return false;
    }
    if (reply.exists("error") && !reply["error"].isNull()) {
        err = reply["error"].write();
        return false;
    }
    result = reply["result"];
    return true;
#endif
}

template <typename Writer>
bool WritePrivatePem(const fs::path& path, Writer&& write)
{
#ifdef _WIN32
    // Do not create or truncate a private key without a native ACL contract.
    (void)path; (void)write;
    return false;
#else
    const int fd = ::open(fs::PathToString(path).c_str(), O_WRONLY | O_CREAT | O_TRUNC, 0600);
    if (fd < 0) return false;
    if (::fchmod(fd, 0600) != 0) {
        ::close(fd);
        return false;
    }
    FILE* f = ::fdopen(fd, "w");
    if (!f) {
        ::close(fd);
        return false;
    }
    const bool ok = write(f);
    return std::fclose(f) == 0 && ok;
#endif
}

} // namespace modelnet

// Test harness. Product functions above are extracted byte-for-byte.
using namespace modelnet;
static int failures = 0;
static int checks = 0;
static void Check(bool ok, const char* label)
{
    ++checks;
    std::cout << (ok ? "PASS " : "FAIL ") << label << '\n';
    if (!ok) ++failures;
}
static std::string Read(const fs::path& path)
{
    std::ifstream in(path); return {std::istreambuf_iterator<char>(in), {}};
}
static void Write(const fs::path& path, const char* text)
{
    std::ofstream out(path); out << text;
}
int main(int argc, char** argv)
{
    if (argc != 3) return 2;
    const std::string mode = argv[1];
    const fs::path root = fs::PathFromString(argv[2]);
    const fs::path worker = root / "worker";
    const fs::path marker = root / "marker";
    UniValue out(UniValue::VOBJ); out.pushKV("sentinel", "untouched");
    std::string err;
    if (mode == "empty") {
        Check(std::getenv("BTX_OPENSSL") && !*std::getenv("BTX_OPENSSL"), "empty override actually inherited");
        Check(OpensslBin().empty(), "OpenSSL explicit empty override preserved");
        Check(std::getenv("BTX_MODEL_INFER_CMD") && !*std::getenv("BTX_MODEL_INFER_CMD"), "empty inference setting actually inherited");
        Check(MaybeRunInferCmd(root, out, err), "empty optional inference succeeds");
        Check(out.size() == 1 && out["sentinel"].get_str() == "untouched", "empty optional inference output unchanged");
    } else if (mode == "override") {
        Check(OpensslBin() == "fixture explicit openssl override", "OpenSSL exact override preserved");
    } else if (mode == "infer") {
#ifndef _WIN32
        struct rlimit infer_lim{};
        Check(getrlimit(RLIMIT_NOFILE, &infer_lim) == 0, "read inference fixture fd limit");
        infer_lim.rlim_cur = std::min<rlim_t>(infer_lim.rlim_max, 256);
        Check(setrlimit(RLIMIT_NOFILE, &infer_lim) == 0, "bound inference fixture fd limit");
        const int infer_fd = open("/dev/null", O_RDONLY);
        Check(infer_fd >= 0 && dup2(infer_fd, 200) == 200, "install inference descriptor leakage control");
        if (infer_fd >= 0) close(infer_fd);
#endif
        const bool ok = MaybeRunInferCmd(root, out, err);
#ifdef _WIN32
        Check(!ok && !err.empty(), "configured inference refuses natively");
        Check(out.size() == 1 && out["sentinel"].get_str() == "untouched", "refused inference output unchanged");
        Check(!fs::exists(marker), "configured inference creates no worker marker");
#else
        Check(ok && out["infer_ok"].get_bool() && out["generated"].get_bool(), "configured inference executes successfully");
        Check(out["infer_stdout"].get_str() == "fixture-infer", "configured inference protocol output");
        close(200);
#endif
    } else if (mode == "profile-nonexec" || mode == "profile-missing") {
        const HostGenerateProfile p = ProbeHostGenerateProfile();
        const UniValue json = HostGenerateProfileJson(p);
        Check(!p.llama_cli && !p.generate_adapter && !p.cuda_loader && !p.exl3_cli,
              "configured missing/nonexecutable files advertise no backend");
        Check(json["formats"].empty() && json["backends"].empty() && !json["can_generate"].get_bool(),
              "configured missing/nonexecutable exported profile unavailable");
    } else if (mode == "full") {
#ifndef _WIN32
        signal(SIGPIPE, SIG_IGN);
        // This process and its own children only: keep the real fallback FD sweep bounded.
        struct rlimit lim{};
        Check(getrlimit(RLIMIT_NOFILE, &lim) == 0, "read fixture fd limit");
        lim.rlim_cur = std::min<rlim_t>(lim.rlim_max, 256);
        Check(setrlimit(RLIMIT_NOFILE, &lim) == 0, "bound fixture fd limit to 256");
        const int inherited_fd = open("/dev/null", O_RDONLY);
        Check(inherited_fd >= 0 && dup2(inherited_fd, 200) == 200, "install descriptor leakage control");
        if (inherited_fd >= 0) close(inherited_fd);
        pid_t fdchild = fork();
        if (fdchild == 0) { CloseWorkerDescriptors(); _exit(fcntl(200, F_GETFD) == -1 && errno == EBADF ? 0 : 1); }
        int fdstatus = 0;
        Check(fdchild > 0 && waitpid(fdchild, &fdstatus, 0) == fdchild && WIFEXITED(fdstatus) && WEXITSTATUS(fdstatus) == 0,
              "real PR403 descriptor cleanup closes inherited fd");
#endif
        const HostGenerateProfile p = ProbeHostGenerateProfile();
        const UniValue json = HostGenerateProfileJson(p);
#ifdef _WIN32
        Check(!p.llama_cli && !p.generate_adapter && !p.cuda_loader && !p.exl3_cli, "all four native backend flags false with existing files");
        Check(!json["llama_cli"].get_bool() && !json["generate_adapter"].get_bool() && !json["cuda_loader"].get_bool() && !json["exl3_cli"].get_bool(), "all four exported native backend flags false");
        Check(json["formats"].empty() && json["backends"].empty() && !json["can_generate"].get_bool(), "native profile advertises no formats/backends/generation");
        Check(!IsExecutableFile(worker), "native existing backend is unavailable");
        Check(OpensslBin() == "openssl", "native unset OpenSSL uses existing fallback");
#else
        Check(p.llama_cli && p.generate_adapter && p.cuda_loader && p.exl3_cli, "all four POSIX executable backend flags true");
        Check(json["formats"].size() == 3 && json["backends"].size() == 4 && json["can_generate"].get_bool(), "POSIX profile advertises supported execution");
        const fs::path nonexec = root / "nonexec"; Write(nonexec, "not executable"); chmod(fs::PathToString(nonexec).c_str(), 0600);
        Check(IsExecutableFile(worker) && !IsExecutableFile(nonexec) && !IsExecutableFile(root / "missing") && !IsExecutableFile(root), "POSIX file admission: executable, nonexec, missing, directory");
        Check(!OpensslBin().empty(), "POSIX OpenSSL discovery returns existing nonempty path fallback");
#endif
        Check(!std::getenv("BTX_MODEL_INFER_CMD"), "optional inference setting actually absent");
        Check(MaybeRunInferCmd(root, out, err), "absent optional inference succeeds");
        using TestPid = decltype(ResidentCuda{}.pid);
        TestPid pid = 9876;
        bool cuda = RunCudaLoader(worker, root, out, err, &pid);
#ifdef _WIN32
        Check(!cuda && pid == 0 && !err.empty(), "CUDA hold refuses and clears PID");
        Check(!RunCudaLoader(worker, root, out, err, nullptr), "CUDA one-shot refuses");
        Check(!RunGenerateAdapter(worker, root, "fixture", 4, out, err), "generate adapter refuses");
        Check(!RunLlamaGenerate(worker, root / "dummy.gguf", "fixture", 4, out, err), "llama runner refuses");
        Check(out.size() == 1 && out["sentinel"].get_str() == "untouched", "native runners leave output unchanged");
        Check(g_resident.empty(), "native runner refusal creates no resident entry");
        Check(!PidAlive(0) && !PidAlive(4242), "native PID checks never claim live worker");
        ResidentCuda stale; stale.pid = 4242; g_resident["fixture"] = stale;
        StopResident("fixture"); Check(g_resident.empty(), "native stale resident cleanup erases record");
        Check(!fs::exists(marker), "native runner guards create no worker marker");
        const fs::path sentinel = root / "sentinel.sock"; Write(sentinel, "endpoint sentinel");
        Check(!UnixSocketSafeToAdopt(sentinel, err) && !err.empty(), "native Unix adoption check refuses");
        Check(!UnixConnectedPeerIsSelf(-1, err) && !err.empty(), "native peer identity check refuses");
        fs::path requested = sentinel;
        Check(ListenUnix(requested, err) < 0 && requested == sentinel && Read(sentinel) == "endpoint sentinel", "native listener refuses before sentinel/path mutation");
        Check(!CallUnixRpc(sentinel, "hello", UniValue(UniValue::VARR), out, err) && Read(sentinel) == "endpoint sentinel", "native Unix RPC refuses before sentinel mutation");
        fs::path missing_socket = root / "missing-socket-parent" / "helper.sock";
        Check(ListenUnix(missing_socket, err) < 0 && !fs::exists(missing_socket.parent_path()), "native listener creates no parent directory");
        const fs::path pem = root / "key.pem"; Write(pem, "PEM sentinel");
        bool called = false;
        auto writer = [&](FILE*) { called = true; return true; };
        Check(!WritePrivatePem(pem, writer) && !called && Read(pem) == "PEM sentinel", "native private PEM refuses before callback/truncation");
        const fs::path missing_pem = root / "missing-pem-parent" / "key.pem";
        Check(!WritePrivatePem(missing_pem, writer) && !called && !fs::exists(missing_pem.parent_path()), "native private PEM creates no parent/file");
#else
        Check(cuda && pid > 0 && PidAlive(pid), "legitimate CUDA resident starts and lives");
        if (cuda && pid > 0) { ResidentCuda r; r.pid = pid; g_resident["fixture"] = r; StopResident("fixture"); }
        Check(g_resident.empty() && !PidAlive(pid), "legitimate CUDA resident stops and reaps");
        Check(RunCudaLoader(worker, root, out, err, nullptr) && out["ok"].get_bool(), "legitimate CUDA one-shot protocol");
        Check(RunGenerateAdapter(worker, root, "fixture", 4, out, err) && out["text"].get_str() == "fixture-adapter", "legitimate adapter stdin/stdout protocol");
        Check(RunLlamaGenerate(worker, root / "dummy.gguf", "fixture", 4, out, err) && out["text"].get_str() == "fixture-llama", "legitimate llama execution");
        Check(!RunCudaLoader(root / "missing", root, out, err, nullptr), "CUDA missing executable refuses");
        Check(!RunGenerateAdapter(root / "nonexec", root, "fixture", 4, out, err), "adapter nonexecutable input refuses");
        Check(!RunLlamaGenerate(root / "nonexec", root / "dummy.gguf", "fixture", 4, out, err), "llama nonexecutable input refuses");
        Check(fs::exists(marker), "POSIX workers actually executed");
        const fs::path pem = root / "key.pem";
        bool called = false;
        Check(WritePrivatePem(pem, [&](FILE* f) { called = true; return std::fputs("private fixture", f) >= 0; }) && called && Read(pem) == "private fixture", "POSIX private PEM writer succeeds");
        struct stat st{}; stat(fs::PathToString(pem).c_str(), &st);
        Check((st.st_mode & 0777) == 0600, "POSIX private PEM has mode 0600");
        fs::path sock = root / "s" / "rpc";
        const int listenfd = ListenUnix(sock, err);
        Check(listenfd >= 0 && UnixSocketSafeToAdopt(sock, err), "POSIX private listener and adoption succeed");
        if (listenfd >= 0) {
            chmod(fs::PathToString(sock).c_str(), 0602);
            Check(!UnixSocketSafeToAdopt(sock, err), "POSIX world-writable socket refuses adoption");
            chmod(fs::PathToString(sock).c_str(), 0600);
            const fs::path link = root / "s" / "link";
            fs::create_symlink(sock, link);
            Check(!UnixSocketSafeToAdopt(link, err), "POSIX socket symlink refuses adoption");
            std::thread server([&] {
                const int fd = accept(listenfd, nullptr, nullptr);
                if (fd < 0) return;
                std::string pe; const bool same = UnixConnectedPeerIsSelf(fd, pe);
                const std::string request = RecvUntil(fd, 4096, nullptr, 3000);
                const std::string reply = same && request.find("hello") != std::string::npos ? "{\"result\":\"fixture-rpc\",\"error\":null}\n" : "{}\n";
                send(fd, reply.data(), reply.size(), 0); close(fd);
            });
            Check(CallUnixRpc(sock, "hello", UniValue(UniValue::VARR), out, err) && out.get_str() == "fixture-rpc", "POSIX actual local Unix RPC exchange");
            server.join(); close(listenfd); fs::remove(sock);
        }
        close(200);
#endif
    } else return 2;
    std::cout << "RESULT checks=" << checks << " failures=" << failures << '\n';
    return failures ? 1 : 0;
}
