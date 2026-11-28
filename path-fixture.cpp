#include <util/fs.h>
#include <shared_p2p/runtime.h>

#include <iostream>
#include <stdexcept>
#include <string>

#ifdef _WIN32
#include <windows.h>
#endif

struct TestArgs {
    fs::path dir;
    const fs::path& GetDataDirNet() const { return dir; }
};

int main(int argc, char** argv)
{
    if (argc == 2 && std::string(argv[1]) == "profile") {
#ifdef _WIN32
        std::cout << "ansi_code_page=" << GetACP() << '\n';
#else
        std::cout << "posix\n";
#endif
        return 0;
    }
    if (argc != 3) return 2;
    const std::string operation = argv[1];
    const std::string path_case = argv[2];
    if (operation != "write" && operation != "reopen") return 2;
    if (path_case != "ascii" && path_case != "unicode") return 2;
    try {
        const std::filesystem::path basename = path_case == "ascii"
            ? std::filesystem::path("data-ascii")
            : std::filesystem::path(u8"data-\u00fc-\U0001f3c3");
        const TestArgs args{std::filesystem::current_path() / basename / "regtest"};
        std::filesystem::create_directories(args.GetDataDirNet());
        const std::string genesis(64, 'a');
        const std::string token(64, 'b');
        NODE_START_RUNTIME_CALL
        auto& core = btx::p2p::AuthoritativeCore();
        constexpr std::int64_t now = 1234;
        const btx::p2p::Record expected{"fixture-key", "fixture-only", 1, now + 600};
        if (operation == "write" && !core.PublishVerified(btx::p2p::Service::SwapNet, expected, now)) {
            throw std::runtime_error("fixture catalog write refused");
        }
        const auto records = core.Page(btx::p2p::Service::SwapNet, "", 2, now);
        if (records.size() != 1 || records[0].key != expected.key ||
            records[0].payload != expected.payload || records[0].sequence != expected.sequence ||
            records[0].expires != expected.expires) {
            throw std::runtime_error("fixture record missing or changed");
        }
#ifndef _WIN32
        const auto directory = args.GetDataDirNet() / "shared-p2p";
        if ((std::filesystem::status(directory).permissions() & std::filesystem::perms::group_all) != std::filesystem::perms::none ||
            (std::filesystem::status(directory).permissions() & std::filesystem::perms::others_all) != std::filesystem::perms::none ||
            !std::filesystem::is_socket(directory / "model-control.sock")) {
            throw std::runtime_error("POSIX private broker controls changed");
        }
#endif
        btx::p2p::StopRuntime();
        std::cout << operation << " " << path_case << ": fixture record matched\n";
        return 0;
    } catch (const std::exception& error) {
        btx::p2p::StopRuntime();
        std::cerr << error.what() << '\n';
        return 3;
    }
}
