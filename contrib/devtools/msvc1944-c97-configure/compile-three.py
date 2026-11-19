"""Verify the fresh dependency restore and compile three pinned MSVC rules."""
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import struct
import subprocess
import time
import sys

root = Path.cwd()
source = root / "source"
records = root / "plan-records"
records.mkdir(exist_ok=True)
mode = "compile"
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


def inspect_dynamic_payload(cache):
    installed = cache / "installed"
    prefix = installed / "x64-windows"
    triplet = cache / "vcpkg/triplets/x64-windows.cmake"
    triplet_text = triplet.read_text(encoding="utf-8")
    dlls = sorted(f.relative_to(prefix).as_posix() for f in prefix.rglob("*.dll")
                  if f.relative_to(prefix).parts[0].casefold() != "debug")
    metadata = installed / "vcpkg"
    package_lists = sorted(f.name for f in (metadata / "info").glob("*_x64-windows.list"))
    layout = {"triplet_sha256": sha(triplet), "release_dlls": dlls,
              "status_file": (metadata / "status").is_file(),
              "package_list_count": len(package_lists), "package_lists": package_lists,
              "prefix_entries": sorted(p.name for p in prefix.iterdir()),
              "metadata_entries": sorted(p.name for p in metadata.iterdir())}
    (records / f"{mode}-dependency-layout.json").write_text(json.dumps(layout, indent=2)+"\n")
    assert "set(VCPKG_CRT_LINKAGE dynamic)" in triplet_text, "CRT linkage differs"
    assert "set(VCPKG_LIBRARY_LINKAGE dynamic)" in triplet_text, "Library linkage differs"
    assert dlls, "Dynamic release DLLs missing from dependency prefix"
    assert package_lists, "Installed package inventories missing"
    return layout


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
    assert receipt["cache_hit"], "The exact complete dependency cache did not restore"
    provenance = cache / "provenance.json"
    if not provenance.is_file():
        receipt.update(status="BLOCKED_CACHE_MISMATCH", reason="Missing dependency provenance in restored cache")
        return
    info = json.loads(provenance.read_text())
    expected = provenance_identity(cl)
    toolchain = cache / "vcpkg/scripts/buildsystems/vcpkg.cmake"
    if any(info.get(k) != v for k,v in expected.items()) or not toolchain.is_file():
        receipt.update(status="BLOCKED_CACHE_MISMATCH", reason="Restored dependencies differ in provenance or dynamic payload")
        return
    files = info.get("sha256", {})
    if not files or any(not (cache / f).resolve().is_relative_to(cache.resolve()) or
                        not (cache / f).is_file() or sha(cache / f)!=h for f,h in files.items()):
        receipt.update(status="BLOCKED_CACHE_MISMATCH", reason="Cache integrity inventory absent or differs")
        return
    inspect_dynamic_payload(cache)
    receipt.update(dependency_provenance_verified=True, cache_file_count=len(files))
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
    generators = set()
    for name in target_names:
        matches = [row for row in db if Path(row["file"]).resolve()==(source/"src/matmul"/name).resolve()]
        assert len(matches)==1
        command = matches[0]["command"]
        assert re.search(r"(?:^|\s)[/-]openmp(?:\s|$)",command,re.I)
        obj = f"src/CMakeFiles/bitcoin_common.dir/matmul/{name}.obj"
        assert obj.lower() in command.replace(chr(92),"/").lower() and not (build/obj).exists()
        command_exe = command.split(maxsplit=1)[0].strip('"')
        assert Path(command_exe).samefile(cl), f"Unmatched generated compiler for {name}"
        assert Path(matches[0]["directory"]).resolve() == build.resolve()
        for tool, suffix in (("query", "query.txt"),("commands","closure.txt")):
            output = subprocess.check_output(["ninja", "-C", str(build), "-t", tool, obj], env=env)
            (records/f"{name}.{suffix}").write_bytes(output)
            if tool == "commands":
                graph = output.decode("utf-8").splitlines()
                assert len(graph) == 2, f"Unexpected closure for {name}"
                graph_args = [arg for arg in graph[1].split() if arg.lower() != "/showincludes"]
                assert graph_args == command.split(), f"Unexpected graph compiler flags for {name}"
                generators.add(graph[0])
        rows.append({"source":name,"object":obj,"command":command})
    (records/"three-commands.json").write_text(json.dumps(rows,indent=2)+"\n",encoding="utf-8")
    previous_hashes = {'matmul_v4_rc_freivalds_i8mm.cpp': '3faf547366544bcbe0224e42ceafd09cd3bb3470136607c6b599d7c1c60e20f2', 'matmul_v4_rc_freivalds_sampled.cpp': 'bb8ec5af34f5029c605f5e6677cc517f4fdfd0e74423f0498b9e77410305ecdc', 'matmul_v4_rc_fri_ext3_alg.cpp': '173f787e05b11ef3bf3f5be9152b3ca1251429b345dd12b5fd6fddef4f3ddfd2'}
    for row in rows:
        row["command_sha256"] = hashlib.sha256(row["command"].encode()).hexdigest()
        row["matches_configure_run"] = row["command_sha256"] == previous_hashes[row["source"]]
    assert len(generators) == 1 and all(row["matches_configure_run"] for row in rows), "Plan drift since verified configure"
    header = build/"src/bitcoin-build-info.h"
    config_header = build/"src/bitcoin-build-config.h"
    generator = source/"cmake/script/GenerateBuildInfo.cmake"
    graph_generator = next(iter(generators))
    assert all(part in graph_generator for part in
               (f"-DBUILD_INFO_HEADER_PATH={header.as_posix()}",
                f"-DSOURCE_DIR={source.as_posix()}", f"-P {generator.as_posix()}"))
    assert config_header.is_file(), "CMake's generated config header is absent"
    before = {p.relative_to(build).as_posix() for p in build.rglob("*.obj")}
    assert not before.intersection(row["object"] for row in rows)
    with (records/"build-info.log").open("wb") as log:
        subprocess.run(["cmake", f"-DBUILD_INFO_HEADER_PATH={header.as_posix()}",
                        f"-DSOURCE_DIR={source.as_posix()}", "-P", str(generator)],
                       cwd=build/"src", env=env, stdout=log, stderr=subprocess.STDOUT,
                       check=True, timeout=30)
    assert header.is_file(), "Build-info generator did not produce its header"
    receipt.update(status="COMPILING_THREE", rules=3, generator="Ninja", objects=[],
                   prerequisite_sha256={p.name: sha(p) for p in (header, config_header)})
    save()
    for row in rows:
        name = row["source"]
        obj = build/row["object"]
        obj.parent.mkdir(parents=True, exist_ok=True)
        started = time.monotonic()
        with (records/f"{name}.compile.log").open("wb") as log:
            receipt["object_builds"] = True
            try:
                result = subprocess.run(row["command"], cwd=build, env=env, stdout=log,
                                        stderr=subprocess.STDOUT, timeout=150)
                code = result.returncode
            except subprocess.TimeoutExpired:
                code = "timeout"
        passed = False
        info = {k: v for k, v in row.items() if k != "command"}
        if code == 0 and obj.is_file():
            with obj.open("rb") as file:
                machine, sections = struct.unpack("<HH", file.read(4))
            passed = machine == 0x8664 and sections > 0
            info.update(sha256=sha(obj), size_bytes=obj.stat().st_size, machine=hex(machine), sections=sections)
        info.update(exit_code=code, passed=passed, duration_seconds=round(time.monotonic()-started, 2))
        receipt["objects"].append(info)
        save()
        print(f"{name}: exit {code}, valid AMD64 COFF {passed}", flush=True)
    after = {p.relative_to(build).as_posix() for p in build.rglob("*.obj")}
    receipt["product_objects_created"] = sorted(after - before)
    assert after - before == {row["object"] for row in rows if (build/row["object"]).exists()}
    receipt["linked"] = False
    receipt["unit_tests"] = False
    assert all(row["passed"] for row in receipt["objects"]), "One or more focal object commands failed"
    assert len(after-before)==3, "The expected three product objects are missing"
    receipt["status"] = "PASS_THREE_MATMUL_OBJECTS"


try:
    inspect()
except Exception as error:
    receipt.update(status="FAILED", error=repr(error))
    raise
finally:
    save()
