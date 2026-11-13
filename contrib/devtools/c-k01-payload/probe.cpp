#include <compat/mingw/posix_extra.h>
#include <array>
#include <cstdlib>
#include <fstream>
#include <iostream>
#include <iterator>
#include <string>
#include <vector>

namespace modelnet {
using Generation16 = std::array<unsigned char, 16>;
std::string GenerationHex(const Generation16& gen)
{
    constexpr char hex[] = "0123456789abcdef";
    std::string out;
    for (unsigned char byte : gen) {
        out += hex[byte >> 4];
        out += hex[byte & 15];
    }
    return out;
}
#include "materialize.inc"
}

std::string Read(const std::string& path, std::ios::openmode mode = std::ios::binary)
{
    std::ifstream in(path, mode);
    return {std::istreambuf_iterator<char>(in), {}};
}

int main(int argc, char** argv)
{
    if (argc != 2) return 2;
    const std::string dest = std::string(argv[1]) + "/payload";
    const std::string sidecar = dest + ".gen";
    const std::vector<std::vector<unsigned char>> pieces{{'a'}, {'b'}};
    const modelnet::Generation16 gen{};
    std::string code, error;
    {
        std::ofstream out(sidecar, std::ios::binary);
        out << "existing generation";
        out.close();
        if (!out) return 3;
    }
    const bool accepted = modelnet::MaterializeCompleteFile(pieces, dest, gen, code, error);
    const DWORD attributes = GetFileAttributesA(dest.c_str());
    const bool collision_ok = !accepted && code == "IO_ERROR" && error == "generation sidecar" &&
        Read(sidecar) == "existing generation";
    std::cout << "collision_ok=" << collision_ok << " payload_attributes=" << attributes << '\n';
    if (!collision_ok) return 4;
    if (::_unlink(sidecar.c_str()) != 0) return 5;
    const bool retry = modelnet::MaterializeCompleteFile(pieces, dest, gen, code, error);
    if (attributes != INVALID_FILE_ATTRIBUTES) {
        const int deleted = ::_unlink(dest.c_str());
        const int unlink_errno = errno;
        std::cout << "leftover_readonly=" << bool(attributes & FILE_ATTRIBUTE_READONLY)
                  << " unlink_rc=" << deleted << " unlink_errno=" << unlink_errno
                  << " retry=" << retry << " retry_code=" << code << '\n';
        return !retry && code == "OVERWRITE_REFUSED" &&
            (attributes & FILE_ATTRIBUTE_READONLY) && deleted == -1 && unlink_errno == EACCES ? 17 : 6;
    }
    const DWORD published = GetFileAttributesA(dest.c_str());
    if (!retry || published == INVALID_FILE_ATTRIBUTES || !(published & FILE_ATTRIBUTE_READONLY) ||
        Read(dest) != "ab" || Read(sidecar, std::ios::in) != std::string(32, '0') + "\n2\n") return 7;
    if (modelnet::MaterializeCompleteFile({{'x'}}, dest, gen, code, error) ||
        code != "OVERWRITE_REFUSED" || Read(dest) != "ab") return 8;
    std::cout << "retry=pass read_only=pass no_overwrite=pass\n";
}
