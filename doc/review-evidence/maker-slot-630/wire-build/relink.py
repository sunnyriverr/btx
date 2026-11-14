"""Relink two local daemons with paired embedded SwapNet variants."""
import json
from pathlib import Path
import shlex
import shutil
import subprocess
import sys

out = Path(__file__).resolve().parent
root = out.parent
build = root / "embedded-build"
source = root / "embedded-source"
ninja = root.parent / "wallet-sendall-acceptance/venv/bin/ninja"
partner_patch = Path(sys.argv[1]).resolve()
commands = json.loads((build / "compile_commands.json").read_text())
check = subprocess.check_output([ninja, "-C", build, "-t", "commands", "bin/btxd"], text=True).splitlines()
link, = [line.strip() for line in check if " -o bin/btxd " in line]
assert link.startswith(": && ") and " && cd " in link
link_cmd = shlex.split(link.removeprefix(": && ").split(" && cd ", 1)[0])

def compile_file(suffix, dest, include=None):
    entry, = [entry for entry in commands if entry["file"] == str(source / suffix)
              and (suffix != "src/bitcoind.cpp" or "CMakeFiles/btxd.dir/" in entry["command"])]
    args = shlex.split(entry["command"])
    args[args.index("-o") + 1] = str(dest)
    if include:
        flag = "-I" + str(build / "src/swapnet-generated")
        args[args.index(flag)] = "-I" + str(include)
    subprocess.run(args, cwd=build, check=True)

compile_file("src/bitcoind.cpp", out/"bitcoind.o")
compile_file("src/init/bitcoind.cpp", out/"init.o")
common = {}
for member in ("runtime.cpp.o", "transport.cpp.o"):
    common[member] = out/member
    common[member].write_bytes(subprocess.check_output(
        ["/usr/bin/ar", "-p", build/"lib/libbtx_swapnet_engine.a", member]))
for mode in ("patched", "stock"):
    directory = out/mode
    directory.mkdir()
    package = directory/"contrib/swapnet/swapnet"
    shutil.copytree(source/"contrib/swapnet/swapnet", package, ignore=shutil.ignore_patterns("__pycache__"))
    if mode == "stock":
        for name in ("coordinator", "journal", "store"):
            shutil.copy2(root/f"native-baseline-source/contrib/swapnet/swapnet/{name}.py", package/f"{name}.py")
    patch = partner_patch.read_text().split("--- a/doc/", 1)[0]
    assert patch.count("--- a/") == 1
    subprocess.run(["/usr/bin/patch", "-p1"], cwd=directory, input=patch, text=True, check=True)
    subprocess.run([sys.executable, source/"contrib/swapnet/generate_embedded.py", package,
                    directory/"swapnet/frozen_sources.h"], check=True)
    compile_file("src/swapnet/embed.cpp", directory/"embed.o", directory)
    engine = directory/"libbtx_swapnet_engine.a"
    subprocess.run(["/usr/bin/ar", "rcs", engine, directory/"embed.o", *common.values()], check=True)
    replacements = {
        "src/CMakeFiles/btxd.dir/bitcoind.cpp.o": str(out/"bitcoind.o"),
        "src/CMakeFiles/btxd.dir/init/bitcoind.cpp.o": str(out/"init.o"),
        "lib/libbtx_swapnet_engine.a": str(engine),
        "bin/btxd": str(root/f"venv/bin/btxd-wire-{mode}"),
    }
    assert set(replacements) <= set(link_cmd)
    subprocess.run([replacements.get(arg, arg) for arg in link_cmd], cwd=build, check=True)
    print(f"{mode}: linked", flush=True)
