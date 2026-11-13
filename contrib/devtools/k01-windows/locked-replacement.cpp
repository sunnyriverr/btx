#include <util/readwritefile.h>
#include <util/fs_helpers.h>
#include <windows.h>

#include <cstdio>
#include <memory>
#include <stdexcept>
#include <string_view>

static void require(bool ok, const char* message)
{
    if (!ok) throw std::runtime_error{message};
}

int main(int argc, char* argv[])
{
    if (argc != 2) return 2;
    try {
        const fs::path root = fs::PathFromString(argv[1]);
        const fs::path target = root / "target";
        const fs::path staging = root / "staging";
        require(fs::create_directory(staging), "create empty staging");
        require(WriteBinaryFileAtomically(target, "previous"), "initial write");
        const auto write = [](std::FILE* file) {
            constexpr std::string_view data = "replacement";
            return std::fwrite(data.data(), 1, data.size(), file) == data.size();
        };
        const auto close = [](void* handle) { CloseHandle(handle); };
        const HANDLE raw = CreateFileW(target.c_str(), GENERIC_READ, FILE_SHARE_READ | FILE_SHARE_WRITE,
                                       nullptr, OPEN_EXISTING, FILE_ATTRIBUTE_NORMAL, nullptr);
        require(raw != INVALID_HANDLE_VALUE, "open destination without delete sharing");
        std::unique_ptr<void, decltype(close)> lock{raw, close};
        const auto control = root / "control";
        require(WriteBinaryFileAtomically(control, "control"), "write rename control");
        require(!RenameOver(control, target), "Windows must refuse direct replacement with handle open");
        require(fs::remove(control), "clean direct replacement control");
        bool staged = false;
        const auto observed_write = [&](std::FILE* file) {
            staged = write(file) && FileCommit(file);
            return staged;
        };
        require(!WriteBinaryFileAtomically(target, observed_write, staging), "writer must report replacement failure");
        require(staged, "writer must have reached and synced staged bytes");
        require(fs::is_empty(staging), "failed replacement must clean staging");
        char original[16]{};
        DWORD count{0};
        require(ReadFile(lock.get(), original, sizeof(original), &count, nullptr), "read locked destination");
        require(std::string_view(original, count) == "previous", "locked handle must retain previous bytes");
        require(CloseHandle(lock.release()), "release destination handle");
        require(ReadBinaryFile(target) == std::pair{true, std::string{"previous"}}, "path must retain previous bytes");
        staged = false;
        require(WriteBinaryFileAtomically(target, observed_write, staging), "identical write must succeed after unlock");
        require(staged && fs::is_empty(staging), "retry must sync bytes and clean staging");
        require(ReadBinaryFile(target) == std::pair{true, std::string{"replacement"}}, "retry must publish exact bytes");
        std::puts("PASS: locked replacement refused, original bytes preserved, staging cleaned, identical retry passed");
    } catch (const std::exception& error) {
        std::fprintf(stderr, "FAIL: %s\n", error.what());
        return 1;
    }
}
