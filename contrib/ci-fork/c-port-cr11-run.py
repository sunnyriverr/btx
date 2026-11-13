"""Compile the same release source and control under the native toolchain."""
import hashlib
import shutil
import subprocess
from pathlib import Path

root = Path.cwd()
out = root / "windows-cr11-results"
out.mkdir()
compiler = shutil.which("clang-cl")
if not compiler:
    raise RuntimeError("clang-cl unavailable")
version = subprocess.check_output([compiler, "--version"], text=True)
(out / "compiler.txt").write_text(version)
resource_dir = Path(subprocess.check_output([compiler, "--print-resource-dir"], text=True).strip())
builtins = resource_dir / "lib/windows/clang_rt.builtins-x86_64.lib"
if not builtins.is_file():
    raise RuntimeError(f"missing release-profile Clang builtins: {builtins}")
stock = root / "src/modelnet/hcp_cr11.cpp"
source = stock.read_bytes()
old = b"const __int128 kMax = std::numeric_limits<__int128>::max();"
new = b"constexpr auto kMax = static_cast<__int128>(~static_cast<unsigned __int128>(0) >> 1);"
assert source.count(old) == 1
harness = root / "contrib/ci-fork/c-port-cr11-control.cpp"
univalue = root / "src/univalue"
variants = (("stock", source), ("candidate", source.replace(old, new)))
for name, data in variants:
    work = out / name
    work.mkdir()
    local = work / "hcp_cr11.cpp"
    local.write_bytes(data)
    command = [compiler, "/nologo", "/std:c++20", "/EHsc", "/O2", "/MT", "/DWIN32", "/Zc:preprocessor", "/Zc:__cplusplus",
               f"/I{root / 'src'}", f"/I{univalue / 'include'}",
               str(harness), str(local),
               *map(str, sorted((univalue / "lib").glob("univalue*.cpp"))), "/Fe:control.exe", "/link", str(builtins)]
    compiled = subprocess.run(command, cwd=work, stdout=subprocess.PIPE,
                              stderr=subprocess.STDOUT, text=True, errors="replace")
    (out / f"{name}-compile.log").write_text(compiled.stdout, encoding="utf-8")
    compiled.check_returncode()
    binary = work / "control.exe"
    result = subprocess.run([str(binary)], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    (out / f"{name}-run.log").write_text(result.stdout)
    (out / f"{name}-sha256.txt").write_text(
        f"{hashlib.sha256(data).hexdigest()} source\n{hashlib.sha256(binary.read_bytes()).hexdigest()} binary\n")
    for artifact in work.iterdir():
        artifact.unlink()
    work.rmdir()
    print(name, result.returncode, result.stdout, flush=True)
    lines = result.stdout.splitlines()
    assert lines and lines[0] == "stdlib_specialized=0 stdlib_max_is_zero=1"
    if name == "stock":
        assert result.returncode == 1 and lines[1:] == ["null matched=0"] * 3 + ["null matched=1"] * 2
    else:
        assert result.returncode == 0 and lines[1:] == [
            '"8166666.666666666666666666" matched=1', '"816.666666666666666666" matched=1',
            '"100" matched=1', "null matched=1", "null matched=1"]
