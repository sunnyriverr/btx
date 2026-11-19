"""Configure and query three MSVC object rules only when a matching cache exists."""
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess

root = Path.cwd()
source = root / "source"
records = root / "plan-records"
records.mkdir()
rev = "c97c9a8d00ea37359b8691fd25c783725c1f4021"
manifest_hash = "d5c0ecee8a42546f65e9620cf10d800c919495ea0b62f77b43916b199435a8f9"
target_names = (
    "matmul_v4_rc_freivalds_i8mm.cpp",
    "matmul_v4_rc_freivalds_sampled.cpp",
    "matmul_v4_rc_fri_ext3_alg.cpp",
)
receipt = {"source": rev, "status": "INCOMPLETE", "configured": False,
           "object_builds": False, "dependency_installs": False,
           "cache_hit": os.environ.get("BTX_CACHE_HIT") == "true",
           "image": os.environ.get("ImageOS"), "image_version": os.environ.get("ImageVersion")}


def save():
    (records / "result.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")


def sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def inspect():
    assert subprocess.check_output(["git", "-C", str(source), "rev-parse", "HEAD"], text=True).strip() == rev
    assert sha(source / "vcpkg.json") == manifest_hash
    vswhere = Path(os.environ["ProgramFiles(x86)"]) / "Microsoft Visual Studio/Installer/vswhere.exe"
    installs = json.loads(subprocess.check_output(
        [str(vswhere), "-all", "-products", "*", "-requires",
         "Microsoft.VisualStudio.Component.VC.Tools.x86.x64", "-format", "json"], text=True))
    toolset = "14.44.35207"
    choices = [Path(item["installationPath"]) for item in installs if item["installationVersion"].startswith("17.")]
    selected = next((base for base in choices
                     if (base / "VC/Tools/MSVC" / toolset / "bin/Hostx64/x64/cl.exe").is_file()), None)
    if selected is None:
        receipt.update(status="BLOCKED_TOOLSET", reason="VS 2022 x64 toolset 14.44.35207 absent")
        return
    dev = selected / "Common7/Tools/VsDevCmd.bat"
    shell_env = subprocess.check_output(
        f'call "{dev}" -arch=x64 -host_arch=x64 -vcvars_ver={toolset} -winsdk=10.0.26100.0 >nul && set',
        shell=True, text=True, timeout=30)
    env = os.environ.copy()
    env.update(line.split("=", 1) for line in shell_env.splitlines() if "=" in line and not line.startswith("="))
    cl = Path(shutil.which("cl.exe", path=env["PATH"])).resolve()
    expected_cl = selected / "VC/Tools/MSVC" / toolset / "bin/Hostx64/x64/cl.exe"
    version = subprocess.run([str(cl)], env=env, capture_output=True, text=True, timeout=15)
    banner = version.stdout + version.stderr
    (records / "compiler-version.txt").write_text(banner, encoding="utf-8")
    receipt.update(cl=str(cl), toolset=env.get("VCToolsVersion"), sdk=env.get("WindowsSDKVersion"),
                   compiler_exact=cl==expected_cl.resolve() and "19.44.35230" in banner and "x64" in banner,
                   sdk_exact=env.get("WindowsSDKVersion","").rstrip(chr(92))=="10.0.26100.0")
    if not receipt["compiler_exact"] or not receipt["sdk_exact"]:
        receipt.update(status="BLOCKED_TOOLSET", reason="Selected cl or SDK differs")
        return
    cache = Path(os.environ["RUNNER_TEMP"]) / "btx-msvc1944-dynamic-deps"
    if not receipt["cache_hit"]:
        vcpkg = env.get("VCPKG_INSTALLATION_ROOT")
        receipt.update(status="BLOCKED_CACHE_MISS", triplet="x64-windows", manifest_sha256=manifest_hash,
                       runner_vcpkg_root_present=bool(vcpkg and Path(vcpkg).is_dir()),
                       runner_has_installed_dynamic_prefix=bool(vcpkg and (Path(vcpkg)/"installed/x64-windows").is_dir()),
                       reason="No exact provenance-tagged dynamic dependency cache was restored; CMake not called.")
        return
    provenance = cache / "provenance.json"
    if not provenance.is_file():
        receipt.update(status="BLOCKED_CACHE_MISMATCH", reason="Missing dependency provenance in restored cache")
        return
    info = json.loads(provenance.read_text())
    expected = {"target_triplet": "x64-windows", "manifest_sha256": manifest_hash,
                "toolset": toolset, "sdk": "10.0.26100.0"}
    prefix = cache / "installed/x64-windows"
    toolchain = cache / "vcpkg/scripts/buildsystems/vcpkg.cmake"
    if any(info.get(k) != v for k,v in expected.items()) or not toolchain.is_file() or not list((prefix/"bin").glob("*.dll")):
        receipt.update(status="BLOCKED_CACHE_MISMATCH", reason="Restored dependencies differ in provenance or dynamic payload")
        return
    files = info.get("sha256", {})
    if not files or any(not (cache / f).resolve().is_relative_to(cache.resolve()) or
                        not (cache / f).is_file() or sha(cache / f)!=h for f,h in files.items()):
        receipt.update(status="BLOCKED_CACHE_MISMATCH", reason="Cache integrity inventory absent or differs")
        return
    build = root / "build-plan"
    env.update(VCPKG_BINARY_SOURCES="clear", VCPKG_DISABLE_METRICS="1")
    cmake = ["cmake", "-S", str(source), "-B", str(build), "-G", "Ninja",
             "-DCMAKE_BUILD_TYPE=Release", "-DCMAKE_EXPORT_COMPILE_COMMANDS=ON",
             f"-DCMAKE_C_COMPILER={cl}", f"-DCMAKE_CXX_COMPILER={cl}",
             f"-DCMAKE_TOOLCHAIN_FILE={toolchain}", f"-DVCPKG_INSTALLED_DIR={cache/'installed'}",
             "-DVCPKG_MANIFEST_INSTALL=OFF", "-DVCPKG_TARGET_TRIPLET=x64-windows",
             "-DVCPKG_MANIFEST_NO_DEFAULT_FEATURES=ON", "-DVCPKG_MANIFEST_FEATURES=wallet;tests;zeromq",
             "-DBUILD_TESTS=ON", "-DENABLE_WALLET=ON", "-DWITH_SQLITE=ON", "-DWITH_ZMQ=ON",
             "-DWITH_MODELNET=OFF", "-DBUILD_GUI=OFF", "-DBUILD_BENCH=OFF"]
    with (records/"configure.log").open("wb") as log:
        subprocess.run(cmake, env=env, stdout=log, stderr=subprocess.STDOUT, check=True, timeout=300)
    receipt["configured"] = True
    shutil.copy(build/"CMakeCache.txt", records)
    db = json.loads((build/"compile_commands.json").read_text())
    rows = []
    for name in target_names:
        matches = [row for row in db if Path(row["file"]).resolve()==source/"src/matmul"/name]
        assert len(matches)==1
        command = matches[0]["command"]
        assert re.search(r"(?:^|\s)[/-]openmp(?:\s|$)",command,re.I)
        obj = f"src/CMakeFiles/bitcoin_common.dir/matmul/{name}.obj"
        assert obj.lower() in command.replace(chr(92),"/").lower() and not (build/obj).exists()
        for tool, suffix in (("query", "query.txt"),("commands","closure.txt")):
            output = subprocess.check_output(["ninja", "-C", str(build), "-t", tool, obj], env=env)
            (records/f"{name}.{suffix}").write_bytes(output)
        rows.append({"source":name,"object":obj,"command":command})
    (records/"three-commands.json").write_text(json.dumps(rows,indent=2)+"\n",encoding="utf-8")
    receipt.update(status="PASS_CONFIGURE_ONLY", rules=len(rows), generator="Ninja")


try:
    inspect()
except Exception as error:
    receipt.update(status="FAILED", error=repr(error))
    raise
finally:
    save()
