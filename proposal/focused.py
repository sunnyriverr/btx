"""Run only the edited fixture with digest-pinned saved binaries."""
import configparser
import csv
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import tempfile
import time

root = Path(os.environ["GITHUB_WORKSPACE"])
records = root / "records"
product = root / "product"
proposal = root / "proposal"
kind = sys.argv[1]
assert kind in {"linux", "mac"}
build = root / ("gui-pilot-runtime/qtbuild" if kind == "linux" else "mac-config-build")
fixture = product / "test/functional/wallet_importbundle_shielded.py"
case = "wallet_importbundle_shielded.py --descriptors"
pin = "2c4da891f0089ebc0fb082e65d03a4efda4488a3"


def sha(path):
    with path.open("rb") as f:
        return hashlib.file_digest(f, "sha256").hexdigest()


candidate = proposal / fixture.name
base_sha = "b2dde2912902931b63ade652ee1f9016edb65f009319b81540303bcc9ea7bdc8"
patch_sha = "2a8b7b7a7f1a3a3b776fec970560dfd014d6b2ee3c6fb6cfe7f562479dfe95a4"
assert sha(fixture) == base_sha and sha(candidate) == patch_sha
if kind == "linux":
    restored = json.loads((records / "staging.json").read_text())
    assert restored["complete"] and restored["source"] == pin and restored["artifact"] == 14707154639
    checkpoint = restored["artifact"]
    expected = {Path(path).name: digest for digest, path in (
        row.split() for row in (proposal / "linux-binaries.sha256").read_text().splitlines())}
    ssl = root / "gui-pilot-runtime/openssl/bin/openssl"
else:
    restored = json.loads((records / "restore-result.json").read_text())
    assert restored["status"] == "VERIFIED" and restored["source"] == pin and restored["artifact"] == 14703680085
    checkpoint = restored["artifact"]
    expected = {name: row["sha256"] for name, row in restored["binaries"].items()}
    assert len(expected) == 17
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
shutil.copyfile(candidate, fixture)
if kind == "mac":
    paths = subprocess.check_output(["git", "-C", str(product), "diff", "--name-only"], text=True).splitlines()
    assert paths == [str(fixture.relative_to(product))], paths
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
    stages = {"export_refusal": "Browser export refuses the imported wallet" in raw,
              "same_seed_import_refusal": "re-importing the original bundle is refused" in raw,
              "funded_wallet_control": "with its own shielded note is refused" in raw}
    logs = [line for f in scratch.glob("test_runner*/wallet_importbundle_shielded_*/test_framework.log")
            for line in f.read_text(errors="replace").splitlines()]
    for mark, needle in (("export_refusal","Browser export refuses the imported wallet"),
                         ("same_seed_import_refusal","re-importing the original bundle is refused"),
                         ("funded_wallet_control","with its own shielded note is refused")):
        stages[mark] = stages[mark] or any(needle in line for line in logs)
    blockers = (scratch/"build-attempts.txt").exists()
    exact = len(rows) == 2 and {r["test"] for r in rows} == {case,"ALL"}
    passed = exact and all(r["status"] == "Passed" for r in rows) and proc.returncode == 0 and not timed_out and not blockers
    result = dict(platform=kind, source=pin, checkpoint=checkpoint, fixture_sha256=patch_sha,
                  verified_binaries=len(expected), status="PASS" if passed else "FAIL",
                  runner_exit=proc.returncode, exact_selection=exact, timed_out=timed_out,
                  stage_markers=stages, both_refusals_and_spendability_passed=passed,
                  build_invocation_attempted=blockers, seconds=round(time.monotonic()-start, 2))
    if not passed:
        result["terminal_diagnostics"] = [line[:380] for line in raw.splitlines()
               if line.startswith(("ERROR:","WARNING:","AssertionError:","test_framework.authproxy.JSONRPCException:"))][-12:]
assert not scratch.exists()
assert binary_hashes() == expected and sha(config) == cfg_sha and sha(fixture) == patch_sha
result.update(binary_hashes_unchanged=True, scratch_removed=True)
(records / "wallet-fixture-result.json").write_text(json.dumps(result, indent=2)+"\n")
print(json.dumps(result, indent=2), flush=True)
raise SystemExit(0 if passed else 1)
