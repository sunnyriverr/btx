// Copyright (c) 2026 The BTX developers
// Portions Copyright (c) 2020-2022 The Bitcoin Core developers
// MIT license; source provenance recorded in source-identities.json.
#include <modelnet/helper.h>
#include <util/sock.h>
#include <univalue.h>
#include <chrono>
#include <thread>
#include <algorithm>
#include <cstring>
#include <poll.h>
#include <sys/socket.h>
#include <sys/un.h>
#include <sys/stat.h>
#include <unistd.h>
namespace modelnet {
constexpr int PQ1_IDLE_MS=30000;
constexpr size_t MAX_RPC_BODY=256*1024;
constexpr int UNIX_RPC_REPLY_MS=120*1000;
constexpr int UNIX_RPC_LONG_REPLY_MS=24*60*60*1000;
// Fixture paths are always private and short: the unrelated path fallback is outside this build.
fs::path UnixRpcListenPath(const fs::path& p){return p;}
void SetNodeModelHostAdvertised(bool){}

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
bool UnixSocketSafeToAdopt(const fs::path& sock, std::string& err)
{
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
}
bool UnixConnectedPeerIsSelf(int fd, std::string& err)
{
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
}
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
}
}
