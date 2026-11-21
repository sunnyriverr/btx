"""Run only the original fixture with digest-pinned saved binaries."""
import configparser
import csv
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time

root = Path(os.environ["GITHUB_WORKSPACE"])
records = root / "records"
product = root / "product"
build = root / "mac-config-build"
fixture = product / "test/functional/wallet_importbundle_shielded.py"
case = "wallet_importbundle_shielded.py --descriptors"
pin = "63c0475d4a8b11e80f727688c5c6d203a0ab938f"

def sha(path):
    with path.open("rb") as f:
        return hashlib.file_digest(f, "sha256").hexdigest()


fixture_digest = "b2dde2912902931b63ade652ee1f9016edb65f009319b81540303bcc9ea7bdc8"
assert sha(fixture) == fixture_digest
receipt = json.loads((records / "build-result.json").read_text())
assert receipt["source"] == pin and receipt["status"] == "PASS" and receipt["targets"] == ["btxd", "btx-cli"]
checkpoint = receipt["checkpoint"]
expected = receipt["binary_sha256"]
assert set(expected) == {"btxd", "btx-cli"}
ssl = Path("/opt/homebrew/opt/openssl@3/bin/openssl")


def binary_hashes():
    return {name: sha(build / "bin" / name) for name in expected}


assert binary_hashes() == expected
config = build / "test/config.ini"
cfg_sha = sha(config)
parsed = configparser.ConfigParser()
parsed.read(config)
assert parsed["environment"]["SRCDIR"] == str(product) and parsed["environment"]["BUILDDIR"] == str(build)
assert parsed["components"].getboolean("ENABLE_WALLET")
assert not subprocess.check_output(["git", "-C", str(product), "status", "--porcelain",
                                    "--untracked-files=no"], text=True).strip()
env = os.environ.copy()
for name in ("BTX_RUN_UPSTREAM_BASE_SUITE", "CI_FAILFAST_TEST_LEAVE_DANGLING", "BITCOIN_TESTS_LOGGING"):
    env.pop(name, None)
env.update(BTXD=str(build / "bin/btxd"), BITCOIND=str(build / "bin/btxd"),
           BTXCLI=str(build / "bin/btx-cli"), BITCOINCLI=str(build / "bin/btx-cli"),
           BTX_OPENSSL=str(ssl), PYTHONUNBUFFERED="1")
start = time.monotonic()
with tempfile.TemporaryDirectory(prefix="btx-wbf-", dir="/tmp") as temp:
    scratch = Path(temp)
    shim = scratch / "no-build"
    shim.mkdir()
    guard = shim / "cmake"
    guard.write_text('#!/bin/sh\nprintf "%s\\n" "$0" >> "$BTX_NO_BUILD_LOG"\nexit 125\n')
    guard.chmod(0o755)
    for name in ("ninja", "make", "cc", "gcc", "g++", "clang", "clang++", "c++"):
        (shim / name).symlink_to(guard.name)
    env.update(TMPDIR=temp, XDG_RUNTIME_DIR=temp, BTX_NO_BUILD_LOG=str(scratch/"build-attempts.txt"),
               PATH=f"{shim}:{Path(sys.executable).parent}:{ssl.parent}:" + env["PATH"])
    csv_path = scratch / "results.csv"
    cmd = [sys.executable, str(product/"test/functional/test_runner.py"), case,
           "--configfile="+str(config), "-j1", "--tmpdirprefix="+temp,
           "--resultsfile="+str(csv_path), "--nocleanup"]
    timed_out = False
    with (scratch / "private-run.log").open("wb") as log:
        with subprocess.Popen(cmd, cwd=product, env=env, stdout=log, stderr=subprocess.STDOUT,
                              start_new_session=True) as proc:
            try:
                proc.wait(timeout=720)
            except subprocess.TimeoutExpired:
                timed_out = True
            finally:
                try:
                    os.killpg(proc.pid, signal.SIGTERM)
                except ProcessLookupError:
                    pass
                else:
                    try:
                        proc.wait(timeout=6)
                    except subprocess.TimeoutExpired:
                        os.killpg(proc.pid, signal.SIGKILL)
                        proc.wait(timeout=6)
    if csv_path.exists():
        with csv_path.open(newline="") as f:
            rows = list(csv.DictReader(f))
        (records / "wallet-results.csv").write_bytes(csv_path.read_bytes())
    else:
        rows = []
    raw = (scratch/"private-run.log").read_text(errors="replace")
    # The maintained test logs the stage names and returns success only after its final
    # funded-wallet spendability assertion. Retain those stage markers, not wallet logs.
    logs = [line for f in scratch.glob("test_runner*/wallet_importbundle_shielded_*/test_framework.log")
            for line in f.read_text(errors="replace").splitlines()]
    stages = {name: needle in raw or any(needle in line for line in logs) for name, needle in (
        ("import_and_restart", "import into a wallet with no shielded keys"),
        ("post_import_export_and_same_seed_refusal", "re-importing the wallet's own bundle"),
        ("funded_wallet_control", "with its own shielded note is refused"),
    )}
    blockers = (scratch/"build-attempts.txt").exists()
    exact = len(rows) == 2 and {r["test"] for r in rows} == {case,"ALL"}
    passed = exact and all(r["status"] == "Passed" for r in rows) and proc.returncode == 0 and not timed_out and not blockers
    result = dict(platform="mac-arm64", source=pin, checkpoint=checkpoint, fixture_sha256=fixture_digest,
                  verified_binaries=len(expected), status="PASS" if passed else "FAIL",
                  runner_exit=proc.returncode, exact_selection=exact, timed_out=timed_out,
                  stage_markers=stages, original_export_and_import_guards_passed=passed,
                  build_invocation_attempted=blockers, seconds=round(time.monotonic()-start, 2))
    if not passed:
        result["terminal_diagnostics"] = [line[:380] for line in raw.splitlines()
               if line.startswith(("ERROR:","WARNING:","AssertionError:","test_framework.authproxy.JSONRPCException:"))][-12:]
assert not scratch.exists()
assert binary_hashes() == expected and sha(config) == cfg_sha and sha(fixture) == fixture_digest
result.update(binary_hashes_unchanged=True, scratch_removed=True)
(records / "wallet-fixture-result.json").write_text(json.dumps(result, indent=2)+"\n")
print(json.dumps(result, indent=2), flush=True)
raise SystemExit(0 if passed else 1)
