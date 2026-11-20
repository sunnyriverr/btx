"""Verify the AUTO assertion against the saved Mac release binaries."""
import json
from pathlib import Path
import re
import subprocess
import tempfile
import time

import default_suite as saved

NAME = "feature_swarm_profile_overrides.py"
FILE = saved.PRODUCT / "test/functional" / NAME
PATCH = Path(__file__).with_name("auto-quota.patch")


def run(phase, env):
    log = saved.OUT / f"{phase}.log"
    start = time.monotonic()
    with tempfile.TemporaryDirectory(prefix="btq-", dir="/tmp") as temp:
        root = Path(temp)
        runtime = root / "rt"
        runtime.mkdir(mode=0o700)
        env = dict(env, TMPDIR=temp, XDG_RUNTIME_DIR=str(runtime))
        datadir = root / ("profile-fixture-" + "x" * 48)
        command = [saved.PYTHON, FILE, f"--configfile={saved.CONFIG}",
                   f"--tmpdir={datadir}", "--portseed=8316", "--timeout-factor=1"]
        with log.open("wb") as f:
            child = subprocess.Popen(command, cwd=saved.PRODUCT, env=env, stdout=f,
                                     stderr=subprocess.STDOUT, start_new_session=True)
            try:
                child.wait(timeout=300)
            finally:
                if child.poll() is None:
                    saved.stop_group(child)
            if child.returncode:
                saved.stop_group(child)
        lines = []
        for path in datadir.glob("node0/stdout/*"):
            if path.is_file():
                lines.extend(l for l in path.read_text(errors="replace").splitlines() if "storage=AUTO" in l)
        (saved.OUT/f"{phase}-auto-startups.log").write_text("\n".join(lines)+"\n")
    result = {"exit_code": child.returncode, "seconds": round(time.monotonic()-start, 2)}
    saved.record(f"{phase}-result.json", result)
    print(f"{phase}: {result}", flush=True)
    return result


def main():
    restore = json.loads((saved.OUT/"restore-result.json").read_text())
    assert restore["status"] == "VERIFIED" and restore["binaries"] == saved.verify_binaries()
    env = saved.runtime_env()
    guard_dir = saved.ROOT / "no-build"
    guard_dir.mkdir()
    attempts = saved.OUT / "build-attempts.log"
    env["NO_BUILD_LOG"] = str(attempts)
    shim = guard_dir / "cmake"
    shim.write_text("#!/bin/sh\necho \"$0 $*\" >> \"$NO_BUILD_LOG\"\nexit 125\n")
    shim.chmod(0o755)
    for name in ("make", "ninja"):
        (guard_dir/name).symlink_to(shim.name)
    before_hash = saved.sha(FILE)
    before = run("before", env)
    baseline_output = (saved.OUT/"before.log").read_text()
    baseline_reproduced = (
        before["exit_code"] == 1 and 'assert_equal(node.getmodelnetworkinfo()["quota_bytes"], preset_quota)' in baseline_output
        and bool(re.search(r"AssertionError: not\(\d+ == \d+\)", baseline_output))
    )
    assert baseline_reproduced or before["exit_code"] == 0, baseline_output[-2000:]
    subprocess.run(["git", "apply", "--check", PATCH], cwd=saved.PRODUCT, check=True)
    subprocess.run(["git", "apply", PATCH], cwd=saved.PRODUCT, check=True)
    assert saved.command(["git", "diff", "--name-only"], "candidate-paths", cwd=saved.PRODUCT) == f"test/functional/{NAME}"
    after = run("after", env)
    assert restore["binaries"] == saved.verify_binaries()
    assert not attempts.exists()
    saved.record("quota-pair-result.json", {"source": saved.PIN, "checkpoint": saved.ARTIFACT,
        "before": before, "after": after, "baseline_reproduced": baseline_reproduced,
        "before_sha256": before_hash, "after_sha256": saved.sha(FILE),
        "patch_sha256": saved.sha(PATCH), "binary_manifest_unchanged": True, "builds": 0})
    return 0 if after["exit_code"] == 0 else 1


raise SystemExit(main())
