"""Restore the verified #522 checkpoint and rebuild the changed RPC object."""
from pathlib import Path
import json
import os
import re
import shutil
import subprocess
import tarfile
import time
from checkpoint import sha, restore_timestamps, verify_restored

HEAD = "37deb8f0da4fc52401efa4c8d64eef17b7226d90"
TREE = "21d2e153f1b0666dfffdd79bf5946488cc6d0868"
BASE = "dac9aee53520bd49ed320ec7a49b9072fc7d88d9"
CACHE = "5093bff8e9f807f19e14c57a9a7252a6cceb8f75f210831785218036c8654e58"
BEFORE = "970cfc3d22b5d3557f2df9f00305de8d17c942cf8844b4369004db5581ffb026"
TARGET = "src/wallet/rpc/labels.cpp"

workspace = Path(os.environ["GITHUB_WORKSPACE"]).resolve()
out = workspace / "build-records"
out.mkdir()
binaries = workspace / "daemon-binaries"
binaries.mkdir()
record = {"head": HEAD, "before_tree": TREE, "checkpoint_sha256": CACHE, "passed": False}

def run(args, name, cwd=workspace, timeout=90):
    result = subprocess.run(args, cwd=cwd, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=timeout)
    (out / (name + ".log")).write_text(result.stdout)
    print(name, result.stdout[-5000:], flush=True)
    result.check_returncode()
    return result.stdout.strip()

try:
    assert shutil.disk_usage(workspace).free > 10 * 1024**3
    saved = workspace / "saved-checkpoint"
    archive = saved / "build-state.tar.gz"
    manifest = json.loads((saved / "manifest.json").read_text())
    assert sha(archive) == manifest["archive_sha256"] == CACHE
    identity = manifest["identity"]
    assert Path(manifest["workspace"]) == workspace
    assert identity["source"] == BASE and identity["candidate_tree"] == TREE and identity["candidate_daemon_sha256"] == BEFORE
    assert not (workspace / "product").exists()
    with tarfile.open(archive) as tar:
        tar.extractall(workspace, filter="data")
    restore_timestamps(workspace, manifest)
    verify_restored(workspace, manifest)
    record["checkpoint_files"] = len(manifest["rows"])
    src = workspace / "product"
    build = workspace / "gui-pilot-runtime/qtbuild"
    assert sha(build / "bin/btxd") == BEFORE
    shutil.copy2(build / "bin/btxd", binaries / "before")
    shutil.copytree(workspace / "accepted-source/.git", src / ".git")
    assert run(["git","rev-parse","HEAD"], "before-head", src) == HEAD
    assert run(["git","rev-parse","HEAD^{tree}"], "before-tree", src) == TREE
    assert not run(["git","diff","HEAD","--name-only"], "before-tracked-delta", src)
    patch = workspace / "read-portable/portable.patch"
    run(["git","apply","--index",str(patch)], "apply", src)
    assert run(["git","diff","HEAD","--name-only"], "after-tracked-delta", src) == TARGET
    run(["git","diff","HEAD","--check"], "after-whitespace", src)
    record["candidate_tree"] = run(["git","write-tree"], "candidate-tree", src)
    record["patch_sha256"] = sha(patch)
    record["changed_source_sha256"] = sha(src / TARGET)
    assert run(["g++","-dumpfullversion"], "compiler") == "11.4.0"
    cache = (build / "CMakeCache.txt").read_text()
    assert all(flag in cache for flag in ("BUILD_DAEMON:BOOL=ON", "ENABLE_WALLET:BOOL=ON", "WITH_SQLITE:BOOL=ON"))
    run(["cmake","-P","CMakeFiles/VerifyGlobs.cmake"], "globs", build)
    ninja = out / "build.ninja"
    shutil.copy2(build / "build.ninja", ninja)
    cmd = ["ninja","-f",str(ninja)]
    dry = run([*cmd,"-d","explain","-n","btxd"], "build-plan", build)
    actions = [re.sub(r"^\[\d+/\d+\] ", "", line) for line in dry.splitlines() if re.match(r"^\[\d+/\d+\] ",line)]
    required = {"Building CXX object src/wallet/CMakeFiles/bitcoin_wallet.dir/rpc/labels.cpp.o",
                "Linking CXX executable bin/btxd"}
    allowed = required | {
        "Generating bitcoin-build-info.h",
        "Building CXX object src/CMakeFiles/bitcoin_clientversion.dir/clientversion.cpp.o",
        "Linking CXX static library lib/libbitcoin_clientversion.a",
        # The generated build-info header also feeds the existing MatMul canary.
        "Building CXX object src/CMakeFiles/bitcoin_common.dir/matmul/matmul_v4_rc_production_canary.cpp.o",
        "Linking CXX static library lib/libbitcoin_common.a",
        "Linking CXX static library lib/libbitcoin_wallet.a",
    }
    record["actions"] = actions
    assert "Re-running CMake" not in dry and "Re-checking globbed" not in dry
    assert required <= set(actions) <= allowed, actions
    started = time.monotonic()
    run([*cmd,"-j1","btxd"], "compile", build, timeout=300)
    record["compile_seconds"] = round(time.monotonic()-started, 2)
    shutil.copy2(build / "bin/btxd", binaries / "after")
    record["binaries"] = {v: sha(binaries / v) for v in ("before", "after")}
    assert record["binaries"]["before"] == BEFORE != record["binaries"]["after"]
    for v in ("before","after"):
        assert "not found" not in run(["ldd",str(binaries/v)], v+"-ldd")
    assert sha(archive) == CACHE
    record["passed"] = True
finally:
    (out / "build-result.json").write_text(json.dumps(record, indent=2)+"\n")
