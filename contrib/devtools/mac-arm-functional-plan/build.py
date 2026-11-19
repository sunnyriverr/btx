"""Build only the audited functional targets within the authorized time budget."""
from pathlib import Path
import hashlib
import json
import os
import platform
import re
import shutil
import signal
import subprocess
import sys
import time
import traceback

ROOT = Path(os.environ["GITHUB_WORKSPACE"])
BUILD = ROOT / "mac-config-build"
RECORDS = ROOT / "records"
MAX_SECONDS = 150 * 60
RESERVE_BYTES = 10 * 1024**3
TARGET = "26d5d2ddb0a27827b5b603a004177582747c294c"
TARGETS = (
    "btxd", "btx-cli", "btx-qt", "btx-util", "btx-tx", "btx-wallet", "btx-modeld",
    "btx-hcpd", "btx-hosted", "btx-open", "btx-capability", "btx-capabilityd",
    "btx-modelcheck", "btx-matmul-backend-info", "btx-security", "btx-guardd", "btx-native-qualify",
)
result = {"source": TARGET, "checkpoint": 14137836649, "cap_seconds": MAX_SECONDS,
          "workers": 2, "target_build_invoked": False, "tests_run": False, "status": "NOT_RUN"}


def save():
    (RECORDS / "build-result.json").write_text(json.dumps(result, indent=2) + "\n")


def count_progress(logfile):
    pattern = r"^\[(\d+)/(\d+)\] "
    last = None
    with logfile.open(errors="replace") as log:
        for line in log:
            if (match := re.match(pattern, line)):
                last = {"completed_actions": int(match[1]), "scheduled_actions": int(match[2])}
    return last


def signal_group(proc, sig):
    try:
        os.killpg(proc.pid, sig)
    except ProcessLookupError:
        pass


def build():
    admission = json.loads((RECORDS / "result.json").read_text())
    assert platform.machine() == "arm64" and admission["source"] == TARGET
    assert admission["checkpoint"] == 14137836649 and admission["restore_verified"]
    assert admission["status"] == "PASS_CONFIGURE_ONLY" and admission["btx_objects_unchanged"]
    assert admission["dry_run_objects_unchanged"] and tuple(admission["functional_profile_targets"]) == TARGETS
    assert subprocess.check_output(["git","-C",ROOT/"product","rev-parse","HEAD"], text=True).strip() == TARGET
    edges = admission["plans"]["functional-dry-run"]["edges"]
    assert 0 <= edges <= 3404, f"Plan exceeds the 3,404-action admission: {edges}"
    assert shutil.disk_usage(ROOT).free > RESERVE_BYTES
    openssl = Path((RECORDS / "openssl-prefix.log").read_text().strip()) / "bin"
    env = dict(os.environ, NINJA_STATUS="[%f/%t] ", BTX_OPENSSL=str(openssl / "openssl"),
               PATH=f'{ROOT / "test-env/bin"}:{openssl}:{os.environ["PATH"]}')
    args = ["ninja", "-C", str(BUILD), "-j2", *TARGETS]
    result.update(target_build_invoked=True, status="RUNNING", planned_actions=edges, command=args)
    save()
    started = time.monotonic()
    last_report = started
    stop = None
    logfile = RECORDS / "functional-target-build.log"
    with logfile.open("wb") as output:
        with subprocess.Popen(args, cwd=ROOT, env=env, stdout=output,
                              stderr=subprocess.STDOUT, start_new_session=True) as proc:
            try:
                while proc.poll() is None:
                    now = time.monotonic()
                    elapsed = now - started
                    if elapsed >= MAX_SECONDS - 8:
                        stop = "compile_time_cap"
                        break
                    if shutil.disk_usage(ROOT).free < RESERVE_BYTES:
                        stop = "checkpoint_storage_reserve"
                        break
                    if now - last_report >= 30:
                        result["progress"] = count_progress(logfile)
                        print(f"{elapsed:.0f}s: {result['progress']}", flush=True)
                        save()
                        last_report = now
                    time.sleep(min(2, max(0, MAX_SECONDS - 8 - elapsed)))
            finally:
                if proc.poll() is None:
                    signal_group(proc, signal.SIGTERM)
                    try:
                        proc.wait(timeout=min(6, max(0, MAX_SECONDS-(time.monotonic()-started))))
                    except subprocess.TimeoutExpired:
                        pass
                    signal_group(proc, signal.SIGKILL)
                    proc.wait()
            result.update(exit_code=proc.returncode, stop_reason=stop,
                          seconds=round(time.monotonic()-started, 2), progress=count_progress(logfile))
    if stop:
        result["status"] = "BOUNDED_STOP"
        return
    if result["exit_code"]:
        result["status"] = "BUILD_FAILED"
        return
    manifest = {}
    for target in TARGETS:
        binary = BUILD/"bin"/target
        assert binary.is_file(), f"Missing built output {target}"
        with binary.open("rb") as f:
            digest = hashlib.file_digest(f, "sha256").hexdigest()
        manifest[target] = {"bytes": binary.stat().st_size, "sha256": digest}
    result.update(status="PASS_17_TARGETS", binaries=manifest)


try:
    build()
except Exception as error:
    result.update(status="BLOCKED_OR_FAILED", error=str(error))
    (RECORDS / "build-exception.txt").write_text(traceback.format_exc())
finally:
    save()
sys.exit(0 if result["status"] == "PASS_17_TARGETS" else 1)
