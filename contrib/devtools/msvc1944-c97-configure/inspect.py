"""Prepare dynamic vcpkg dependencies, then configure only and query three MSVC rules."""
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

root = Path.cwd()
source = root / "source"
records = root / "plan-records"
records.mkdir(exist_ok=True)
mode = sys.argv[1]
assert mode in {"prepare", "configure"}
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
    (records / (mode + "-result.json")).write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")


def sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def provenance_identity(cl):
    return {"target_triplet": "x64-windows", "manifest_sha256": manifest_hash,
            "toolset": "14.44.35207", "sdk": "10.0.26100.0", "cl_sha256": sha(cl),
            "vcpkg_registry": "c82f74667287d3dc386bce81e44964370c91a289",
            "manifest_features": ["wallet", "tests", "zeromq"]}


def prepare_cache(cache, env, selected, cl):
    expected = provenance_identity(cl)
    cache.mkdir(parents=True, exist_ok=False)
    repo = cache / "vcpkg"
    subprocess.run(["git", "init", str(repo)], check=True, timeout=30)
    subprocess.run(["git", "-C", str(repo), "config", "core.longpaths", "true"], check=True, timeout=15)
    subprocess.run(["git", "-C", str(repo), "fetch", "--no-tags",
                    "https://github.com/microsoft/vcpkg.git", expected["vcpkg_registry"]], check=True, timeout=180)
    subprocess.run(["git", "-C", str(repo), "checkout", "--detach", "FETCH_HEAD"], check=True, timeout=30)
    assert subprocess.check_output(["git", "-C", str(repo), "rev-parse", "HEAD"], text=True).strip() == expected["vcpkg_registry"]
    dep_env = {**env, "VCPKG_VISUAL_STUDIO_PATH": str(selected), "VCPKG_BINARY_SOURCES": "clear",
               "VCPKG_DISABLE_METRICS": "1", "VCPKG_MAX_CONCURRENCY": "4", "VCPKG_ROOT": str(repo)}
    msys = Path("C:/msys64")
    choices = [msys / f"{prefix}/bin/{name}.exe"
               for prefix in ("mingw64", "ucrt64") for name in ("pkg-config", "pkgconf")]
    pkgconf = next((p for p in choices if p.is_file()), None)
    if pkgconf is None:
        bash = msys / "usr/bin/bash.exe"
        with (records/"pkgconf-setup.log").open("wb") as log:
            subprocess.run([str(bash), "-lc", "pacman --noconfirm --needed -Sy mingw-w64-x86_64-pkgconf"],
                           stdout=log, stderr=subprocess.STDOUT, check=True, timeout=120)
        pkgconf = next(p for p in choices if p.is_file())
    pkg_version = subprocess.check_output([str(pkgconf), "--version"], text=True, timeout=10).strip()
    receipt["pkgconf"] = {"path": str(pkgconf), "version": pkg_version, "sha256": sha(pkgconf)}
    dep_env.update(PKG_CONFIG=str(pkgconf), VCPKG_KEEP_ENV_VARS="PKG_CONFIG")
    binary_cache = Path(os.environ["RUNNER_TEMP"]) / "btx-msvc1944-dynamic-ports"
    binary_cache.mkdir(exist_ok=True)
    dep_env["VCPKG_BINARY_SOURCES"] = f"clear;files,{binary_cache},readwrite"
    # Use the stock dynamic triplet. The actual detected cl is checked in the install log.
    subprocess.run(["cmd.exe", "/d", "/c", "bootstrap-vcpkg.bat", "-disableMetrics"], cwd=repo,
                   env=dep_env, check=True, timeout=100)
    exe = repo / "vcpkg.exe"
    dirs = Path(os.environ["RUNNER_TEMP"]) / "btx-msvc1944-port-work"
    dirs.mkdir()
    args = [str(exe), "install", "--triplet=x64-windows", "--host-triplet=x64-windows",
            f"--x-manifest-root={source}", f"--x-install-root={cache/'installed'}",
            f"--x-buildtrees-root={dirs/'buildtrees'}", f"--x-packages-root={dirs/'packages'}",
            f"--downloads-root={dirs/'downloads'}", "--x-no-default-features",
            *["--x-feature="+f for f in expected["manifest_features"]]]
    receipt["dependency_install_attempted"] = True
    try:
        with (records/"vcpkg-install.log").open("wb") as log:
            subprocess.run(args, cwd=source, env=dep_env, stdout=log, stderr=subprocess.STDOUT,
                           check=True, timeout=1350)
    finally:
        for f in (dirs/"buildtrees/detect_compiler").glob("stdout-*"):
            if f.is_file():
                shutil.copy(f, records)
    receipt["dependency_installs"] = True
    log = (records/"vcpkg-install.log").read_text(errors="replace")
    assert "compiler found:" in log.lower(), "vcpkg compiler report missing"
    assert "14.44.35207" in log and "14.51." not in log, "vcpkg selected another compiler"
    prefix = cache / "installed/x64-windows"
    payload = [f for f in (cache/"installed").rglob("*") if f.is_file()]
    payload += [f for f in (repo/"scripts").rglob("*") if f.is_file()]
    payload.append(exe)
    assert list((prefix/"bin").glob("*.dll")) and (cache/"installed/vcpkg/status").is_file()
    expected["pkgconf"] = receipt["pkgconf"]
    expected["sha256"] = {f.relative_to(cache).as_posix(): sha(f) for f in payload}
    (cache/"provenance.json").write_text(json.dumps(expected,indent=2)+"\n")
    # The cache retains the install and toolchain, separate from BTX outputs and port work directories.


def inspect():
    assert subprocess.check_output(["git", "-C", str(source), "rev-parse", "HEAD"], text=True).strip() == rev
    manifest_blob = subprocess.check_output(["git", "-C", str(source), "show", "HEAD:vcpkg.json"])
    receipt["manifest_blob_sha256"] = hashlib.sha256(manifest_blob).hexdigest()
    receipt["manifest_worktree_sha256"] = sha(source / "vcpkg.json")
    assert receipt["manifest_blob_sha256"] == manifest_hash, "Unexpected pinned Git manifest blob"
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
    env.update((k.upper(), v) for k, v in (line.split("=", 1) for line in shell_env.splitlines()
                if "=" in line and not line.startswith("=")))
    cl = Path(shutil.which("cl.exe", path=env["PATH"])).resolve()
    expected_cl = selected / "VC/Tools/MSVC" / toolset / "bin/Hostx64/x64/cl.exe"
    version = subprocess.run([str(cl)], env=env, capture_output=True, text=True, timeout=15)
    banner = version.stdout + version.stderr
    (records / "compiler-version.txt").write_text(banner, encoding="utf-8")
    receipt.update(cl=str(cl), toolset=env.get("VCTOOLSVERSION"), sdk=env.get("WINDOWSSDKVERSION"),
                   compiler_exact=cl==expected_cl.resolve() and "19.44.35230" in banner and "x64" in banner,
                   sdk_exact=env.get("WINDOWSSDKVERSION","").rstrip(chr(92))=="10.0.26100.0")
    if not receipt["compiler_exact"] or not receipt["sdk_exact"]:
        receipt.update(status="BLOCKED_TOOLSET", reason="Selected cl or SDK differs")
        return
    cache = Path(os.environ["RUNNER_TEMP"]) / "btx-msvc1944-dynamic-deps"
    if mode == "prepare" and not receipt["cache_hit"]:
        prepare_cache(cache, env, selected, cl)
    provenance = cache / "provenance.json"
    if not provenance.is_file():
        receipt.update(status="BLOCKED_CACHE_MISMATCH", reason="Missing dependency provenance in restored cache")
        return
    info = json.loads(provenance.read_text())
    expected = provenance_identity(cl)
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
    receipt.update(dependency_provenance_verified=True, cache_file_count=len(files))
    if mode == "prepare":
        with Path(os.environ["GITHUB_OUTPUT"]).open("a", encoding="utf-8") as stream:
            stream.write("admitted=true\n")
        shutil.copy(provenance, records/"dependency-provenance.json")
        receipt.update(status="PASS_DEPENDENCY_CACHE", provenance=expected)
        return
    subprocess.run([sys.executable, "-m", "pip", "install", "--only-binary=:all:", "cryptography==46.0.4"],
                   check=True, timeout=75)
    build = root / "build-plan"
    env.update(VCPKG_BINARY_SOURCES="clear", VCPKG_DISABLE_METRICS="1")
    cmake = ["cmake", "-S", str(source), "-B", str(build), "-G", "Ninja",
             "-DCMAKE_BUILD_TYPE=Release", "-DCMAKE_EXPORT_COMPILE_COMMANDS=ON",
             f"-DPython3_EXECUTABLE={sys.executable}",
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
        matches = [row for row in db if Path(row["file"]).resolve()==(source/"src/matmul"/name).resolve()]
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
