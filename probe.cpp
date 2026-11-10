#include <cerrno>
#include <cstdio>
#include <filesystem>
#include <fstream>
#include <io.h>
#include <iostream>
#include <string>

int main(int argc, char** argv)
{
    if (argc != 4) return 2;
    const std::filesystem::path path{argv[1]};
    const std::string mode{argv[2]};
    const bool full = std::string{argv[3]} == "full";
    if (std::filesystem::exists(path)) return 2;
    const std::string bytes(573, 'x');
    bool reported = false;
    int flush_error = 0;
    int close_error = 0;
    if (mode == "old") {
        std::ofstream out{path, std::ios::binary | std::ios::trunc};
        if (!out) return 3;
        out.write(bytes.data(), bytes.size());
        reported = out.good();
        out.close();
        close_error = out.fail();
    } else if (mode == "checked") {
        FILE* file = std::fopen(argv[1], "wb");
        if (!file) return 3;
        const bool written = std::fwrite(bytes.data(), 1, bytes.size(), file) == bytes.size();
        errno = 0;
        const bool flushed = std::fflush(file) == 0;
        flush_error = errno;
        const bool synced = flushed && _commit(_fileno(file)) == 0;
        errno = 0;
        const bool closed = std::fclose(file) == 0;
        close_error = errno;
        reported = written && synced && closed;
        if (!reported && !std::filesystem::remove(path)) return 4;
    } else {
        return 2;
    }
    const auto size = std::filesystem::exists(path) ? static_cast<long long>(std::filesystem::file_size(path)) : -1;
    std::cout << "{\"mode\":\"" << mode << "\",\"reported\":" << (reported ? "true" : "false")
              << ",\"file_bytes\":" << size << ",\"flush_errno\":" << flush_error
              << ",\"close_status\":" << close_error << "}\n";
    if (!full) return reported && size == bytes.size() ? 0 : 5;
    if (mode == "old") return reported && close_error && size >= 0 && size < bytes.size() ? 0 : 6;
    return !reported && size == -1 && flush_error == ENOSPC ? 0 : 7;
}
