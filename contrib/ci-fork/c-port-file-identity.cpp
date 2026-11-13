#include <filesystem>
#include <fstream>
#include <iostream>
#include <sys/stat.h>
namespace fs = std::filesystem;
int main()
{
    std::ofstream("source.txt") << "same bytes";
    std::ofstream("copy.txt") << "same bytes";
    fs::create_hard_link("source.txt", "link.txt");
    struct stat source{}, copy{}, link{};
    if (stat("source.txt", &source) || stat("copy.txt", &copy) || stat("link.txt", &link)) return 2;
    std::error_code ec;
    const bool distinct = !fs::equivalent("source.txt", "copy.txt", ec) && !ec;
    const bool hardlink = fs::equivalent("source.txt", "link.txt", ec) && !ec;
    std::cout << "stat_inode_distinguishes_copy=" << (source.st_ino != copy.st_ino)
              << " equivalent_distinguishes_copy=" << distinct << " equivalent_detects_hardlink=" << hardlink << '\n';
#ifdef _WIN32
    return !(source.st_ino == copy.st_ino && distinct && hardlink);
#else
    return !(source.st_ino != copy.st_ino && distinct && hardlink);
#endif
}
