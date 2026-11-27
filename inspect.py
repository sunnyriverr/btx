"""Verify the static dependency cache and compile two pinned MatMul objects."""
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time

root = Path.cwd()
source = root / "source"
records = root / "plan-records"
records.mkdir(exist_ok=True)
mode = sys.argv[1]
assert mode == "compile"
rev = "c2e71aafc48a41593277e335c8bc370e45599f01"
manifest_hash = "d5c0ecee8a42546f65e9620cf10d800c919495ea0b62f77b43916b199435a8f9"
target_names = (
    "matmul_v4_rc_stage3_bounded_semantic_codec.cpp",
    "matmul_v4_rc_stage3_relation_local_sharding.cpp",
)
expected_commands = dict(zip(target_names, (
    "0bc73afea95796c074a84ef221fc68288d239912d88fd31edeedb09fef7cac1b",
    "f19e05f42d81d9535b185c70c2ee72c61f667f77f0de970f74f72ed6220b341b",
)))
expected_diagnostics = dict(zip(target_names, (
    r"\(107\):\s*fatal error C1202:",
    r"\(224\):\s*error C2065:.*__uint128_t",
)))
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
    return {"target_triplet": "x64-windows-static", "manifest_sha256": manifest_hash,
            "toolset": "14.44.35207", "sdk": "10.0.26100.0", "cl_sha256": sha(cl),
            "vcpkg_registry": "c82f74667287d3dc386bce81e44964370c91a289",
            "manifest_features": ["wallet", "tests", "zeromq"]}


def inspect_static_payload(cache):
    installed = cache / "installed"
    prefix = installed / "x64-windows-static"
    triplet = cache / "vcpkg/triplets/x64-windows-static.cmake"
    triplet_text = triplet.read_text(encoding="utf-8")
    dlls = sorted(f.relative_to(prefix).as_posix() for f in (prefix / "bin").glob("*.dll")
                  if f.relative_to(prefix).parts[0].casefold() != "debug")
    metadata = installed / "vcpkg"
    package_lists = sorted(f.name for f in (metadata / "info").glob("*_x64-windows-static.list"))
    layout = {"triplet_sha256": sha(triplet), "release_dlls": dlls,
              "status_file": (metadata / "status").is_file(),
              "package_list_count": len(package_lists), "package_lists": package_lists,
              "prefix_entries": sorted(p.name for p in prefix.iterdir()),
              "metadata_entries": sorted(p.name for p in metadata.iterdir())}
    (records / f"{mode}-dependency-layout.json").write_text(json.dumps(layout, indent=2)+"\n")
    assert "set(VCPKG_CRT_LINKAGE static)" in triplet_text, "CRT linkage differs"
    assert "set(VCPKG_LIBRARY_LINKAGE static)" in triplet_text, "Library linkage differs"
    libs = sorted(p.name for p in (prefix / "lib").glob("*.lib"))
    assert libs, "Static release libraries missing"
    assert not dlls, "Unexpected release DLLs in static target prefix"
    layout["static_libraries"] = libs
    (records / f"{mode}-dependency-layout.json").write_text(json.dumps(layout, indent=2)+"\n")
    assert package_lists, "Installed package inventories missing"
    return layout


def compile_plan(build, env, cl, rows):
    header = build / "src/bitcoin-build-info.h"
    config_header = build / "src/bitcoin-build-config.h"
    generator = source / "cmake/script/GenerateBuildInfo.cmake"
    assert config_header.is_file()
    for row in rows:
        name = row["source"]
        command = row["command"]
        row["command_sha256"] = hashlib.sha256(command.encode()).hexdigest()
        assert row["command_sha256"] == expected_commands[name], f"Configured flags drifted for {name}"
        assert Path(command.split(maxsplit=1)[0].strip('"')).samefile(cl)
        closure = (records / f"{name}.closure.txt").read_text().splitlines()
        assert len(closure) == 2, f"Unexpected rule closure for {name}"
        assert all(term in closure[0] for term in (
            f"-DBUILD_INFO_HEADER_PATH={header.as_posix()}",
            f"-DSOURCE_DIR={source.as_posix()}", f"-P {generator.as_posix()}",
        )), f"Unexpected prerequisite for {name}"
        assert [arg for arg in closure[1].split() if arg.lower() != "/showincludes"] == command.split()

    with (records / "build-info.log").open("wb") as log:
        subprocess.run(["cmake", f"-DBUILD_INFO_HEADER_PATH={header.as_posix()}",
                        f"-DSOURCE_DIR={source.as_posix()}", "-P", str(generator)],
                       cwd=build / "src", env=env, stdout=log, stderr=subprocess.STDOUT,
                       check=True, timeout=30)
    receipt.update(status="RUNNING_TWO_COMMANDS", source_files_unmodified=True,
                   prerequisite_sha256={path.name: sha(path) for path in (header, config_header)},
                   objects=[], linked=False, unit_tests=False)
    before = {path.relative_to(build).as_posix() for path in build.rglob("*.obj")}
    for row in rows:
        name = row["source"]
        obj = build / row["object"]
        obj.parent.mkdir(parents=True, exist_ok=True)
        started = time.monotonic()
        logfile = records / f"{name}.compile.log"
        with logfile.open("wb") as log:
            receipt["object_builds"] = True
            try:
                result = subprocess.run(row["command"], cwd=build, env=env, stdout=log,
                                        stderr=subprocess.STDOUT, timeout=120)
                code = result.returncode
            except subprocess.TimeoutExpired:
                code = "timeout"
        diagnostics = [line for line in logfile.read_text(errors="replace").splitlines()
                       if re.search(r"(?:fatal )?error [A-Z]+\d+:", line)]
        matched = (isinstance(code, int) and code != 0 and not obj.exists()
                   and bool(diagnostics) and bool(re.search(expected_diagnostics[name], diagnostics[0])))
        receipt["objects"].append(dict(
            source=name, object=row["object"], command_sha256=row["command_sha256"],
            source_sha256=sha(source / "src/matmul" / name), exit_code=code,
            diagnostics=diagnostics, expected_failure=matched,
            object_created=obj.exists(), seconds=round(time.monotonic() - started, 2),
        ))
        save()
        print(f"{name}: exit {code}, expected failure {matched}", flush=True)
        for line in diagnostics:
            print(line, flush=True)

    after = {path.relative_to(build).as_posix() for path in build.rglob("*.obj")}
    receipt["new_objects"] = sorted(after - before)
    assert after - before <= {row["object"] for row in rows}, "Unexpected product object output"
    assert not subprocess.check_output(["git", "-C", str(source), "status", "--porcelain", "--untracked-files=no"], text=True).strip()
    receipt["status"] = ("REPRODUCED_BOTH_ERRORS" if all(row["expected_failure"] for row in receipt["objects"])
                         else "DIAGNOSTICS_DIFFER")


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
    cache = Path(os.environ["RUNNER_TEMP"]) / "btx-msvc1944-static-deps"
    if not receipt["cache_hit"]:
        receipt.update(status="BLOCKED_CACHE_MISMATCH", reason="Exact static cache did not restore")
        return
    provenance = cache / "provenance.json"
    if not provenance.is_file() or sha(provenance) != "81a55c747feb4a090a55aa56c2a0c665c40ebd824268c2704fd34d5b7c489d6c":
        receipt.update(status="BLOCKED_CACHE_MISMATCH", reason="Missing dependency provenance in restored cache")
        return
    info = json.loads(provenance.read_text())
    expected = provenance_identity(cl)
    toolchain = cache / "vcpkg/scripts/buildsystems/vcpkg.cmake"
    if any(info.get(k) != v for k,v in expected.items()) or not toolchain.is_file():
        receipt.update(status="BLOCKED_CACHE_MISMATCH", reason="Restored dependencies differ in provenance or static payload")
        return
    files = info.get("sha256", {})
    if not files or any(not (cache / f).resolve().is_relative_to(cache.resolve()) or
                        not (cache / f).is_file() or sha(cache / f)!=h for f,h in files.items()):
        receipt.update(status="BLOCKED_CACHE_MISMATCH", reason="Cache integrity inventory absent or differs")
        return
    inspect_static_payload(cache)
    receipt.update(dependency_provenance_verified=True, cache_file_count=len(files))
    shutil.copy(provenance, records / "dependency-provenance.json")
    subprocess.run([sys.executable, "-m", "pip", "install", "--only-binary=:all:", "cryptography==46.0.4"],
                   check=True, timeout=75)
    build = root / "build-plan"
    env.update(VCPKG_BINARY_SOURCES="clear", VCPKG_DISABLE_METRICS="1")
    cmake = ["cmake", "-S", str(source), "-B", str(build), "-G", "Ninja",
             "-DCMAKE_BUILD_TYPE=Release", "-DCMAKE_EXPORT_COMPILE_COMMANDS=ON",
             f"-DPython3_EXECUTABLE={sys.executable}",
             f"-DCMAKE_C_COMPILER={cl}", f"-DCMAKE_CXX_COMPILER={cl}",
             f"-DCMAKE_TOOLCHAIN_FILE={toolchain}", f"-DVCPKG_INSTALLED_DIR={cache/'installed'}",
             "-DVCPKG_MANIFEST_INSTALL=OFF", "-DVCPKG_TARGET_TRIPLET=x64-windows-static",
             "-DVCPKG_MANIFEST_NO_DEFAULT_FEATURES=ON", "-DVCPKG_MANIFEST_FEATURES=wallet;tests;zeromq",
             "-DBUILD_TESTS=ON", "-DENABLE_WALLET=ON", "-DWITH_SQLITE=ON", "-DWITH_ZMQ=ON",
             "-DWITH_MODELNET=OFF", "-DBUILD_GUI=OFF", "-DBUILD_BENCH=OFF",
             "-DBTX_ENABLE_CUDA_EXPERIMENTAL=OFF", "-DVCPKG_HOST_TRIPLET=x64-windows"]
    with (records/"configure.log").open("wb") as log:
        subprocess.run(cmake, env=env, stdout=log, stderr=subprocess.STDOUT, check=True, timeout=300)
    receipt["configured"] = True
    shutil.copy(build/"CMakeCache.txt", records)
    db = json.loads((build/"compile_commands.json").read_text())
    cache_text = (build/"CMakeCache.txt").read_text()
    assert re.search(r"^VCPKG_TARGET_TRIPLET:[^=]+[=]x64-windows-static$",cache_text,re.M)
    assert "CMAKE_GENERATOR:INTERNAL=Ninja" in cache_text
    assert not list((build/"src").rglob("*.obj")), "BTX object exists after configure"
    rows = []
    for name in target_names:
        matches = [row for row in db if Path(row["file"]).resolve()==(source/"src/matmul"/name).resolve()]
        assert len(matches)==1
        command = matches[0]["command"]
        assert re.search(r"(?:^|\s)[/-]MT(?:\s|$)", command, re.I), "Expected static MSVC CRT"
        assert re.search(r"(?:^|\s)[/-]openmp(?:\s|$)", command, re.I)
        assert "x64-windows-static" in command.replace(chr(92), "/").lower()
        obj = f"src/CMakeFiles/bitcoin_common.dir/matmul/{name}.obj"
        assert obj.lower() in command.replace(chr(92),"/").lower() and not (build/obj).exists()
        for tool, suffix in (("query", "query.txt"),("commands","closure.txt")):
            output = subprocess.check_output(["ninja", "-C", str(build), "-t", tool, obj], env=env)
            (records/f"{name}.{suffix}").write_bytes(output)
        rows.append({"source":name,"object":obj,"command":command})
    (records/"two-commands.json").write_text(json.dumps(rows,indent=2)+"\n",encoding="utf-8")
    assert not subprocess.check_output(["git","-C",str(source),"status","--porcelain","--untracked-files=no"],text=True).strip()
    receipt.update(rules=len(rows), generator="Ninja", triplet="x64-windows-static")
    compile_plan(build, env, cl, rows)


try:
    inspect()
    if receipt["status"] != "REPRODUCED_BOTH_ERRORS":
        raise SystemExit(1)
except Exception as error:
    receipt.update(status="FAILED", error=repr(error))
    raise
finally:
    save()
