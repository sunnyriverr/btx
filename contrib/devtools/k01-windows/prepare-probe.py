"""Use the exact writer and platform filesystem functions in a small Windows link."""
import hashlib
from pathlib import Path
import sys

root, out = map(Path, sys.argv[1:])
out.mkdir(exist_ok=True)

def read(name):
    data = (root / name).read_bytes()
    print(f"{hashlib.sha256(data).hexdigest()}  {name}")
    return data.decode()

def between(source, start, end):
    first = source.index(start)
    return source[first:source.index(end, first)]

writer = read("src/util/readwritefile.cpp")
fs = read("src/util/fs.cpp")
helpers = read("src/util/fs_helpers.cpp")
(out / "readwritefile.cpp").write_text(writer, encoding="utf-8")
(out / "random.h").write_text(
    "#include <cstdint>\n"
    "class FastRandomContext { public: uint64_t rand64() { static uint64_t counter{}; return ++counter; } };\n",
    encoding="utf-8",
)
prefix = """#include <util/fs_helpers.h>
#include <util/check.h>
#include <codecvt>
#include <locale>
#include <cstdlib>
#include <io.h>
#include <fcntl.h>
#include <share.h>
#include <sys/stat.h>
#include <windows.h>
#define LogPrintf(...) std::fputs("file sync failed\\n", stderr)
void assertion_fail(std::string_view, int, std::string_view, std::string_view) { std::abort(); }
namespace fsbridge {
"""
functions = between(fs, "FILE *fopen(", "fs::path AbsPathJoin(") + "}\n"
functions += between(helpers, "bool FileCommit(", "bool TruncateFile(")
functions += between(helpers, "bool RenameOver(", "/**\n * Ignores exceptions")
(out / "platform.cpp").write_text(prefix + functions, encoding="utf-8")
