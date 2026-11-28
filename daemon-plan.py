"""Get the exact cold btxd graph with no BTX compiler, archive or link actions."""
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import sys
import traceback

ROOT = Path.cwd()
SOURCE = ROOT / "source"
BUILD = ROOT / "build-plan"
RECORDS = ROOT / "plan-records"
BASE = "c2e71aafc48a41593277e335c8bc370e45599f01"
CANDIDATE = "1332e7a6545c19af3fa04da329fd55845aa1981b"
MANIFEST_HASH = "d5c0ecee8a42546f65e9620cf10d800c919495ea0b62f77b43916b199435a8f9"
COMPILER_HASH = "e87e78b3ef6580b75aebda843f8a22e874612d9f766344046551399f898eb226"
PROVENANCE_HASH = "81a55c747feb4a090a55aa56c2a0c665c40ebd824268c2704fd34d5b7c489d6c"
TOOLSET = "14.44.35207"
SDK = "10.0.26100.0"
TRIPLET = "x64-windows-static"
FEATURES = ["wallet", "tests", "zeromq"]
PATCHED_BLOBS = {
    "src/matmul/matmul_v4_rc_stage3_bounded_semantic_codec.cpp": "50464e4def34ee26a450f234e9effd2bba833ce1",
    "src/matmul/matmul_v4_rc_stage3_relation_local_sharding.cpp": "f57b817244f613b6bfba220ebc9d5c83f49acaf5",
}
FLAGS = {
    "BUILD_DAEMON": "ON",
    "BUILD_TESTS": "ON",
    "ENABLE_WALLET": "ON",
    "WITH_SQLITE": "ON",
    "WITH_ZMQ": "ON",
    "WITH_MODELNET": "OFF",
    "BUILD_GUI": "OFF",
    "BUILD_BENCH": "OFF",
    "BTX_ENABLE_CUDA_EXPERIMENTAL": "OFF",
}


def get_hash(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def git(*args):
    return subprocess.check_output(["git", "-C", str(SOURCE), *args], timeout=20)


def check_source():
    assert git("rev-parse", "HEAD").decode().strip() == CANDIDATE
    assert git("rev-parse", "HEAD^").decode().strip() == BASE
    assert set(git("diff", "--name-only", "HEAD^", "HEAD").decode().splitlines()) == set(PATCHED_BLOBS)
    assert not git("status", "--porcelain", "--untracked-files=no")
    for name, oid in PATCHED_BLOBS.items():
        assert git("rev-parse", f"HEAD:{name}").decode().strip() == oid
    assert hashlib.sha256(git("show", "HEAD:vcpkg.json")).hexdigest() == MANIFEST_HASH


def compiler_profile():
    vswhere = Path(os.environ["ProgramFiles(x86)"]) / "Microsoft Visual Studio/Installer/vswhere.exe"
    installations = json.loads(subprocess.check_output(
        [str(vswhere), "-all", "-products", "*", "-requires",
         "Microsoft.VisualStudio.Component.VC.Tools.x86.x64", "-format", "json"], timeout=20))
    cl_rel = Path("VC/Tools/MSVC") / TOOLSET / "bin/Hostx64/x64/cl.exe"
    base = next((Path(i["installationPath"]) for i in installations
                 if i["installationVersion"].startswith("17.") and (Path(i["installationPath"]) / cl_rel).is_file()), None)
    assert base, "Exact MSVC 19.44 x64 toolset unavailable"
    settings = subprocess.check_output(
        f'call "{base / "Common7/Tools/VsDevCmd.bat"}" -arch=x64 -host_arch=x64 -vcvars_ver={TOOLSET} -winsdk={SDK} >nul && set',
        shell=True, text=True, timeout=40)
    env = {k.upper(): v for k, v in os.environ.items()}
    env.update((k.upper(), v) for k, v in (line.split("=", 1) for line in settings.splitlines()
               if "=" in line and not line.startswith("=")))
    cl = Path(shutil.which("cl.exe", path=env["PATH"])).resolve()
    banner = subprocess.run([str(cl)], env=env, capture_output=True, timeout=15)
    version = banner.stdout + banner.stderr
    (RECORDS / "compiler-version.txt").write_bytes(version)
    assert cl == (base / cl_rel).resolve() and b"19.44.35230" in version and b"x64" in version
    assert get_hash(cl) == COMPILER_HASH
    assert env["WINDOWSSDKVERSION"].rstrip(chr(92)) == SDK
    return cl, env


def restore_admission():
    assert os.environ.get("BTX_CACHE_HIT") == "true", "Exact dependency cache missed"
    cache = Path(os.environ["RUNNER_TEMP"]) / "btx-msvc1944-static-deps"
    prov = cache / "provenance.json"
    assert get_hash(prov) == PROVENANCE_HASH
    data = json.loads(prov.read_text(encoding="utf-8"))
    for k, v in {
        "target_triplet": TRIPLET, "manifest_sha256": MANIFEST_HASH,
        "toolset": TOOLSET, "sdk": SDK, "cl_sha256": COMPILER_HASH,
        "vcpkg_registry": "c82f74667287d3dc386bce81e44964370c91a289", "manifest_features": FEATURES,
    }.items():
        assert data[k] == v, k
    assert len(data["sha256"]) == 6675
    resolved = cache.resolve()
    for name, value in data["sha256"].items():
        file = cache / name
        assert file.resolve().is_relative_to(resolved) and get_hash(file) == value, name
    target = cache / "installed" / TRIPLET
    assert list((target / "lib").glob("*.lib")) and not list((target / "bin").glob("*.dll"))
    assert not list((target / "bin").glob("*.exe"))
    shutil.copyfile(prov, RECORDS / "dependency-provenance.json")
    return cache, len(data["sha256"])


def capture(args, outfile, env, timeout, combine=False):
    with (RECORDS / outfile).open("wb") as out:
        if combine:
            subprocess.run(args, stdout=out, stderr=subprocess.STDOUT, env=env, timeout=timeout, check=True)
        else:
            with (RECORDS / f"{outfile}.stderr").open("wb") as err:
                subprocess.run(args, stdout=out, stderr=err, env=env, timeout=timeout, check=True)


def product_outputs():
    return sorted(path.relative_to(BUILD).as_posix() for path in BUILD.rglob("*")
                  if path.is_file() and path.suffix.lower() in {".obj", ".o", ".lib", ".a", ".exe", ".pdb", ".dll", ".res"}
                  and "CMakeFiles" != path.relative_to(BUILD).parts[0])


def run(receipt):
    check_source()
    cl, env = compiler_profile()
    cache, count = restore_admission()
    receipt.update(profile={"toolset": TOOLSET, "compiler": "19.44.35230 x64", "sdk": SDK, "cl_sha256": COMPILER_HASH},
                   cache_hit=True, verified_dependency_files=count, free_before_bytes=shutil.disk_usage(ROOT).free)
    assert not BUILD.exists()
    capture([sys.executable, "-m", "pip", "install", "--only-binary=:all:", "cryptography==46.0.4"],
            "configure-python-tooling.log", env, 75, combine=True)
    env.update(VCPKG_BINARY_SOURCES="clear", VCPKG_DISABLE_METRICS="1", NINJA_STATUS="[%f/%t] ")
    cmake = ["cmake", "-S", str(SOURCE), "-B", str(BUILD), "-G", "Ninja",
             "-DCMAKE_BUILD_TYPE=Release", "-DCMAKE_EXPORT_COMPILE_COMMANDS=ON",
             # A dry-run cannot update CMake's glob stamp. Suppress implicit CMake
             # regeneration in this measurement-only graph to expose btxd actions.
             "-DCMAKE_SUPPRESS_REGENERATION=ON",
             f"-DPython3_EXECUTABLE={sys.executable}", f"-DCMAKE_C_COMPILER={cl}",
             f"-DCMAKE_CXX_COMPILER={cl}",
             f"-DCMAKE_TOOLCHAIN_FILE={cache / 'vcpkg/scripts/buildsystems/vcpkg.cmake'}",
             f"-DVCPKG_INSTALLED_DIR={cache / 'installed'}",
             "-DVCPKG_MANIFEST_INSTALL=OFF", f"-DVCPKG_TARGET_TRIPLET={TRIPLET}",
             "-DVCPKG_MANIFEST_NO_DEFAULT_FEATURES=ON", "-DVCPKG_MANIFEST_FEATURES=" + ";".join(FEATURES),
             "-DVCPKG_HOST_TRIPLET=x64-windows", *[f"-D{k}={v}" for k, v in FLAGS.items()]]
    receipt["configure_args"] = cmake
    capture(cmake, "configure.log", env, 320, combine=True)
    shutil.copyfile(BUILD / "CMakeCache.txt", RECORDS / "CMakeCache.txt")
    raw_cache = (BUILD / "CMakeCache.txt").read_text(encoding="utf-8")
    for key, value in FLAGS.items():
        assert re.search(rf"^{key}:[^=]+={value}$", raw_cache, re.M), key
    assert re.search(r"^VCPKG_TARGET_TRIPLET:[^=]+=x64-windows-static$", raw_cache, re.M)
    assert "CMAKE_GENERATOR:INTERNAL=Ninja" in raw_cache
    assert not product_outputs(), "BTX products exist after configure"

    ninja = ["ninja", "-C", str(BUILD)]
    capture([*ninja, "-t", "query", "btxd"], "ninja-query-alias.txt", env, 30)
    alias = (RECORDS / "ninja-query-alias.txt").read_text(encoding="utf-8")
    targets = [p.strip() for p in alias.splitlines() if p.strip().lower().endswith("/btxd.exe")]
    assert len(targets) == 1, alias
    capture([*ninja, "-t", "query", targets[0]], "ninja-query-exe.txt", env, 30)
    capture([*ninja, "-t", "commands", "btxd"], "ninja-commands.txt", env, 30)
    capture([*ninja, "-t", "graph", "btxd"], "ninja-graph.dot", env, 30)
    capture([*ninja, "-n", "-v", "-d", "explain", "btxd"], "ninja-dry-run.txt", env, 60)
    shutil.copyfile(BUILD / "compile_commands.json", RECORDS / "compile_commands.json")
    assert not product_outputs(), "BTX products exist after dry run"
    lines = (RECORDS / "ninja-dry-run.txt").read_text(encoding="utf-8").splitlines()
    numbered = [re.match(r"^\[(\d+)/(\d+)\] (.*)", line) for line in lines]
    actions = [m for m in numbered if m]
    assert actions and int(actions[-1][1]) == int(actions[-1][2]) == len(actions)
    assert "btxd.exe" in actions[-1][3].lower(), actions[-1][3]
    assert all("re-running cmake" not in m[3].lower() for m in actions)
    receipt.update(complete=True, target="btxd", binary=targets[0], actions=len(actions),
                   free_after_bytes=shutil.disk_usage(ROOT).free, product_objects_after_configure_and_dry_run=0,
                   suppress_automatic_regeneration_for_measurement=True)


if __name__ == "__main__":
    RECORDS.mkdir(exist_ok=True)
    result = {"base": BASE, "candidate": CANDIDATE, "patched_blobs": PATCHED_BLOBS,
              "platform": platform.platform(), "image": os.environ.get("ImageVersion"), "complete": False}
    try:
        run(result)
    except Exception:
        (RECORDS / "exception.txt").write_text(traceback.format_exc(), encoding="utf-8")
        raise
    finally:
        (RECORDS / "result.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
