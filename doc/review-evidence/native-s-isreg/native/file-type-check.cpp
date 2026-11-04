#include <cstdio>
#include <filesystem>
#include <fstream>
#include <string>
#include <system_error>
#include <sys/stat.h>
#ifdef TEST_EXISTING_PREDICATE
#ifdef S_ISREG
#undef S_ISREG
#endif
#define S_ISREG(mode) ((mode) == 0x1234)
#endif
#include <compat/mingw/posix_extra.h>
#ifndef _WIN32
#include <unistd.h>
#endif

namespace fs = std::filesystem;
static int failures = 0;
static int checks = 0;
static void Check(bool pass, const char* name)
{
    ++checks;
    std::printf("%s %s\n", pass ? "PASS" : "FAIL", name);
    if (!pass) ++failures;
}

#ifndef TEST_EXISTING_PREDICATE
// The unmodified post-materialization file-type predicate from store.cpp.
static bool AcceptedFileType(const fs::path& path)
{
    struct stat st {};
    const std::string narrow = path.string(); // Match store.cpp caller; fixture paths are ASCII.
    return !(::lstat(narrow.c_str(), &st) != 0 || !S_ISREG(st.st_mode) || S_ISLNK(st.st_mode));
}
static bool ModeChecks()
{
#ifdef _WIN32
    constexpr unsigned REG = _S_IFREG, DIR = _S_IFDIR, CHR = _S_IFCHR, FIFO = _S_IFIFO;
#else
    constexpr unsigned REG = S_IFREG, DIR = S_IFDIR, CHR = S_IFCHR, FIFO = S_IFIFO;
#endif
    struct Case { const char* name; unsigned mode; bool regular; };
    const Case cases[] = {{"regular", REG, true}, {"regular-permissions", REG | 0777, true},
        {"directory", DIR, false}, {"directory-permissions", DIR | 0777, false},
        {"character-device", CHR, false}, {"fifo", FIFO, false},
        {"socket", S_IFSOCK, false}, {"symlink", S_IFLNK, false},
        {"symlink-permissions", S_IFLNK | 0777, false}, {"no-file-type", 0, false},
        {"permissions-only", 0777, false}, {"mixed-type", REG | DIR, false}};
    for (const auto& c : cases) Check(static_cast<bool>(S_ISREG(c.mode)) == c.regular, c.name);
    int evaluations = 0;
    const auto next = [&] { ++evaluations; return REG | 0600; };
    Check(S_ISREG(next()) && evaluations == 1, "single-evaluation");
    return failures == 0;
}
#endif

int main(int argc, char** argv)
{
#ifdef TEST_EXISTING_PREDICATE
    (void)argc; (void)argv;
    Check(S_ISREG(0x1234), "preexisting-predicate-retained");
    Check(!S_ISREG(0), "preexisting-predicate-control");
#else
    ModeChecks();
    if (argc != 2) { std::fprintf(stderr, "Expected owned temporary fixture directory\n"); return 2; }
    const fs::path root{argv[1]}; // Owned fixture paths are ASCII.
    if (fs::exists(root)) { std::fprintf(stderr, "Refusing an existing fixture directory\n"); return 2; }
    std::error_code ec;
    fs::create_directories(root, ec);
    if (ec) { std::fprintf(stderr, "SETUP create-directory %d\n", ec.value()); return 2; }
    const auto cleanup = [&] { std::error_code ignored; fs::remove_all(root, ignored); };
    const fs::path file = root / "regular", dir = root / "directory";
    { std::ofstream out(file, std::ios::binary); out << "regular model fixture\n"; if (!out) { cleanup(); return 2; } }
    fs::create_directory(dir, ec);
    if (ec) { cleanup(); return 2; }
    Check(AcceptedFileType(file), "actual-regular-file-accepted");
    Check(!AcceptedFileType(dir), "actual-directory-rejected");
    Check(!AcceptedFileType(root / "missing"), "actual-missing-path-rejected");
    struct LinkCase { const char* name; fs::path target; bool directory; };
    const LinkCase links[] = {{"file-link", file, false}, {"directory-link", dir, true},
                             {"dangling-link", root / "absent-target", false}};
    for (const auto& link : links) {
        const fs::path path = root / link.name;
        ec.clear();
        if (link.directory) fs::create_directory_symlink(link.target, path, ec);
        else fs::create_symlink(link.target, path, ec);
        if (ec) {
            std::fprintf(stderr, "SETUP symlink-create %s code=%d; no privileges changed\n", link.name, ec.value());
            cleanup(); return 2;
        }
        struct stat st {};
        const std::string narrow = path.string();
        const int rc = ::lstat(narrow.c_str(), &st);
        Check(rc == 0 && S_ISLNK(st.st_mode) && !S_ISREG(st.st_mode), link.name);
        Check(!AcceptedFileType(path), (std::string(link.name) + "-rejected").c_str());
    }
    cleanup();
    Check(!fs::exists(root), "owned-fixture-cleanup");
#endif
    std::printf("RESULT checks=%d failures=%d\n", checks, failures);
    return failures ? 1 : 0;
}
