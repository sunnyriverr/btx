"""Build the Qt candidate from the verified prior release checkpoint."""
import hashlib
import json
import os
import shutil
import subprocess
import tarfile
from pathlib import Path

from checkpoint import restore_timestamps, sha, verify_restored

BASE = "dac9aee53520bd49ed320ec7a49b9072fc7d88d9"
CHECKPOINT = "d95dc41e4a6bfd3e81fdaeefbc57deead3cace244089e21b6f46f2b29e4e866c"
w = Path(os.environ["GITHUB_WORKSPACE"]).resolve()
out = w / "build-records"
out.mkdir()
state = {"source": BASE, "phase": "restore"}
def run(args, label, limit, cwd=None):
    print(label, flush=True)
    with (out / (label + ".log")).open("wb") as log:
        subprocess.run(list(map(str, args)), cwd=cwd, stdout=log, stderr=subprocess.STDOUT,
                       timeout=limit, check=True)
    return (out / (label + ".log")).read_text(errors="replace")

try:
    source = w / "product"
    build = w / "gui-pilot-runtime/qtbuild"
    saved = w / "saved-checkpoint"
    archive = saved / "build-state.tar.gz"
    manifest = json.loads((saved / "manifest.json").read_text())
    assert shutil.disk_usage(w).free >= 10 * 1024**3
    assert sha(archive) == CHECKPOINT == manifest["archive_sha256"]
    assert manifest["identity"]["source"] == BASE and Path(manifest["workspace"]) == w
    assert not source.exists()
    with tarfile.open(archive) as stream:
        stream.extractall(w, filter="data")
    restore_timestamps(w, manifest)
    verify_restored(w, manifest)
    accepted = w / "accepted-source"
    assert run(["git", "rev-parse", "HEAD"], "accepted-head", 20, accepted).strip() == BASE
    for name in run(["git", "ls-files"], "accepted-files", 20, accepted).splitlines():
        a, b = accepted / name, source / name
        if a.is_symlink():
            assert b.is_symlink() and os.readlink(a) == os.readlink(b), name
        else:
            assert a.is_file() and b.is_file() and sha(a) == sha(b), name
    assert run(["g++", "-dumpfullversion"], "compiler", 15).strip() == "11.4.0"
    assert "OpenSSL 3.5.9" in run([w/"gui-pilot-runtime/openssl/bin/openssl", "version"], "openssl", 15)
    state["phase"] = "configure"
    run(["cmake", "-S", source, "-B", build, "-DBUILD_DAEMON=ON", "-DBUILD_CLI=ON"], "configure", 180)
    cache = (build / "CMakeCache.txt").read_text()
    assert all(flag in cache for flag in ("BUILD_GUI:BOOL=ON", "ENABLE_WALLET:BOOL=ON", "WITH_SQLITE:BOOL=ON"))
    before = {n: sha(build/"bin"/n) for n in ("btx-qt","btxd","btx-cli")}
    state["baseline_binaries"] = before
    patch = w / "candidate.patch"
    state["patch_sha256"] = sha(patch)
    run(["git", "apply", "--check", patch], "patch-check", 30, source)
    run(["git", "apply", patch], "patch-apply", 30, source)
    state["phase"] = "build-plan"
    run(["cmake", "-P", build/"CMakeFiles/VerifyGlobs.cmake"], "verify-globs", 120, build)
    ninja = out / "observed.ninja"
    shutil.copy2(build/"build.ninja", ninja)
    plan = run(["ninja", "-C", build, "-f", ninja, "-n", "btx-qt"], "build-plan", 120)
    assert all(f in plan for f in ("walletview.cpp.o", "interfaces.cpp.o", "transactions.cpp.o"))
    steps = sum(line.startswith("[") for line in plan.splitlines())
    state["planned_steps"] = steps
    assert 1 <= steps <= 140, steps
    state["phase"] = "compile"
    run(["ninja", "-C", build, "-j2", "btx-qt"], "compile", 900)
    state["candidate_qt"] = sha(build/"bin/btx-qt")
    assert state["candidate_qt"] != before["btx-qt"]
    assert all(sha(build/"bin"/n) == before[n] for n in ("btxd","btx-cli"))
    run(["ldd", build/"bin/btx-qt"], "dependencies", 30)
    state["phase"] = "retain"
    binaries = w / "compiled-binaries"
    binaries.mkdir()
    for n in ("btx-qt", "btxd", "btx-cli"):
        shutil.copy2(build/"bin"/n, binaries/n)
    state["phase"] = "built"
except Exception as exc:
    state["error"] = repr(exc)
    raise
finally:
    (out/"result.json").write_text(json.dumps(state, indent=2) + "\n")
