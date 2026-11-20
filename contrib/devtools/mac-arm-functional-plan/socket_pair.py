"""Run the same two maintained tests before and after the fixture-only patch."""
from pathlib import Path
import json
import os
import subprocess
import sys
import tempfile
import time

import default_suite as saved

CASES = ("feature_capabilityd_file_modes.py", "feature_modelnet_btx_model.py")
PATCH = Path(__file__).with_name("socket-fixtures.patch")


def guard_checks(scratch, env):
    code = """
import os
from pathlib import Path
import runpy
import sys
from test_framework.util import UNIX_PATH_MAX, unix_socket_path

test_file, scratch = sys.argv[1], Path(sys.argv[2])
cls = runpy.run_path(test_file)["ModelNetBtxModelTest"]
fixture = cls.__new__(cls)
private = scratch / "guard"
private.mkdir(mode=0o700)
outside = scratch / "guard-outside"
outside.mkdir(mode=0o700)
fixture.modeld_socket_dir = private.resolve()
fixture.modeld_socket = private / "modeld.sock"
fixture._assert_scratch_socket()
fixture.modeld_socket.symlink_to(outside / "modeld.sock")
try:
    fixture._assert_scratch_socket()
except AssertionError as exc:
    assert "test scratch directory" in str(exc), str(exc)
else:
    raise AssertionError("guard accepted sibling-directory symlink")
fixture.modeld_socket = Path("/opt/btx/modeld.sock")
try:
    fixture._assert_scratch_socket()
except AssertionError as exc:
    assert "production helper socket" in str(exc), str(exc)
else:
    raise AssertionError("guard accepted production path")
preferred = private / ("a" * UNIX_PATH_MAX) / "modeld.sock"
selected = unix_socket_path(preferred)
assert len(os.fsencode(selected)) < UNIX_PATH_MAX
assert selected.parent.is_dir() and selected.parent.stat().st_mode & 0o077 == 0
fixture.modeld_socket_dir = selected.parent.resolve()
fixture.modeld_socket = selected
fixture._assert_scratch_socket()
print("scratch path accepted; sibling symlink and production path refused; private fallback accepted")
"""
    env = dict(env, PYTHONPATH=str(saved.PRODUCT/"test/functional"))
    saved.command([saved.PYTHON, "-c", code, saved.PRODUCT/"test/functional"/CASES[1], scratch],
                  "scratch-guard", env, timeout=30)


def run(phase, env):
    log = saved.OUT / f"{phase}.log"
    csv = saved.OUT / f"{phase}.csv"
    start = time.monotonic()
    with tempfile.TemporaryDirectory(prefix="btf-", dir="/tmp") as temp:
        scratch = Path(temp)
        env = dict(env, TMPDIR=str(scratch))
        args = [saved.PYTHON, saved.RUNNER, *CASES, "--jobs=2", f"--configfile={saved.CONFIG}",
                f"--resultsfile={csv}", f"--tmpdirprefix={scratch}", "--combinedlogslen=100"]
        with log.open("wb") as f:
            p = subprocess.Popen(args, cwd=saved.PRODUCT, env=env, stdout=f, stderr=subprocess.STDOUT,
                                 start_new_session=True)
            try:
                p.wait(timeout=600)
            finally:
                if p.poll() is None:
                    saved.stop_group(p)
        if p.returncode:
            saved.retain_cache_logs(scratch)
    cases, complete = saved.collect(log, csv, CASES)
    result = dict(exit_code=p.returncode, cases=cases, complete=complete, seconds=round(time.monotonic()-start, 2))
    saved.record(f"{phase}-result.json", result)
    print(f"{phase}: {result}", flush=True)
    return result


def main():
    restored = json.loads((saved.OUT/"restore-result.json").read_text())
    assert restored["status"] == "VERIFIED" and saved.verify_binaries() == restored["binaries"]
    env = saved.runtime_env()
    no_build = saved.ROOT / "no-build"
    no_build.mkdir()
    shim = no_build / "cmake"
    shim.write_text("#!/bin/sh\necho \"$0 $*\" >> \"$NO_BUILD_LOG\"\nexit 125\n")
    shim.chmod(0o755)
    for name in ("make", "ninja"):
        (no_build/name).symlink_to(shim.name)
    attempts = saved.OUT / "build-attempts.log"
    env["NO_BUILD_LOG"] = str(attempts)
    before = run("before", env)
    assert before["complete"] and before["exit_code"] == 1
    assert all(row["status"] == "Failed" for row in before["cases"].values())
    log = (saved.OUT/"before.log").read_text()
    assert "btx-capabilityd exited 2" in log and "socket not found:" in log
    subprocess.run(["git", "apply", "--check", PATCH], cwd=saved.PRODUCT, check=True)
    subprocess.run(["git", "apply", PATCH], cwd=saved.PRODUCT, check=True)
    changed = saved.command(["git", "diff", "--name-only"], "candidate-paths", cwd=saved.PRODUCT)
    assert set(changed.splitlines()) == {f"test/functional/{name}" for name in CASES}
    hashes = {name: saved.sha(saved.PRODUCT/"test/functional"/name) for name in CASES}
    saved.record("candidate-source-hashes.json", hashes)
    with tempfile.TemporaryDirectory(prefix="btf-", dir="/tmp") as temp:
        guard_checks(Path(temp), dict(env, TMPDIR=temp))
    after = run("after", env)
    assert saved.verify_binaries() == restored["binaries"]
    assert not attempts.exists()
    passed = after["complete"] and after["exit_code"] == 0 and all(
        row["status"] == "Passed" for row in after["cases"].values())
    saved.record("socket-pair-result.json", dict(status="PASS_MATCHED" if passed else "CANDIDATE_FAILED",
        pin=saved.PIN, checkpoint=saved.ARTIFACT, patch_sha256=saved.sha(PATCH),
        binary_manifest_unchanged=True, builds=0, before=before, after=after,
        scratch_guard_controls="passed"))
    return 0 if passed else 1


sys.exit(main())
