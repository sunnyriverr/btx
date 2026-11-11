"""Run the maintained queue case against the helper archives with a temporary root."""
from pathlib import Path
import shlex
import subprocess
import sys
import tempfile

root = Path(sys.argv[1]).resolve()
build = root / "build"
source = root / "source/src"
case = (source / "test/modelnet_watch_tests.cpp").read_text()
start = case.index("modelnet::ModelEvent MakeSigned(")
end = case.index("std::string HexBytes(", start)
helpers = case[start:end]
start = case.index("BOOST_AUTO_TEST_CASE(unwatch_drops_the_actions_the_watch_queued)")
end = case.index("BOOST_AUTO_TEST_CASE(", start + 1)
test = case[start:end]

work = build / "src/modelnet"
with tempfile.TemporaryDirectory(prefix="watch-case-", dir=(build / "bin").resolve().parent) as temporary:
    folder = Path(temporary)
    driver = folder / "driver.cpp"
    driver.write_text('''#define BOOST_TEST_MODULE ModelWatchQueue
#define BOOST_TEST_DYN_LINK
#include <boost/test/unit_test.hpp>
#include <modelnet/catalog.h>
#include <modelnet/helper.h>
#include <modelnet/model_watch.h>
#include <univalue.h>
#include <util/fs.h>
#include <util/translation.h>
#include <cstdlib>

const TranslateFn G_TRANSLATION_FUN{nullptr};

namespace {
''' + helpers + '''
struct Fixture {
    const fs::path m_path_root{fs::PathFromString(std::getenv("BTX_WATCH_CASE_ROOT"))};
};
}
BOOST_FIXTURE_TEST_SUITE(modelnet_watch_tests, Fixture)
''' + test + '\nBOOST_AUTO_TEST_SUITE_END()\n')
    cmd = shlex.split((work / "CMakeFiles/btx-modeld.dir/link.txt").read_text())
    entry = next(i for i, arg in enumerate(cmd) if arg.endswith("/modeld.cpp.o"))
    cmd[entry] = str(driver)
    cmd[cmd.index("-o") + 1] = str(folder / "test")
    cmd += [
        "-std=c++20", "-I" + str(source), "-I" + str(build / "src"),
        "-I" + str(source / "univalue/include"), "-I/opt/homebrew/opt/boost/include",
        "/opt/homebrew/opt/boost/lib/libboost_unit_test_framework.dylib",
    ]
    subprocess.run(cmd, cwd=work, check=True)
    process = subprocess.run([folder / "test", "--log_level=test_suite", "--report_level=detailed"],
                             env={"BTX_WATCH_CASE_ROOT": str(folder / "data")})
    sys.exit(process.returncode)
