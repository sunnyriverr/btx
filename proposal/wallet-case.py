"""Run only the maintained shielded wallet import case in disposable regtest."""
from pathlib import Path
import csv
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import time

root = Path(os.environ["GITHUB_WORKSPACE"])
records = root / "records"
build = root / "gui-pilot-runtime/qtbuild"
product = root / "product"
fixture = product / "test/functional/wallet_importbundle_shielded.py"
case = "wallet_importbundle_shielded.py --descriptors"
source = "2c4da891f0089ebc0fb082e65d03a4efda4488a3"
fixture_digest = hashlib.sha256(fixture.read_bytes()).hexdigest()
assert fixture_digest == "b2dde2912902931b63ade652ee1f9016edb65f009319b81540303bcc9ea7bdc8"
assert json.loads((records / "source-sync.json").read_text())["exact_source"] == source
manifest = records / "built-binaries.sha256"
subprocess.run(["sha256sum", "-c", str(manifest)], check=True)
env = os.environ.copy()
for key in ("BTX_RUN_UPSTREAM_BASE_SUITE", "CI_FAILFAST_TEST_LEAVE_DANGLING", "BITCOIN_TESTS_LOGGING"):
    env.pop(key, None)
env.update(BTXD=str(build / "bin/btxd"), BITCOIND=str(build / "bin/btxd"),
           BTXCLI=str(build / "bin/btx-cli"), BITCOINCLI=str(build / "bin/btx-cli"),
           BTX_OPENSSL=str(root / "gui-pilot-runtime/openssl/bin/openssl"),
           PYTHONUNBUFFERED="1")
started = time.monotonic()
with tempfile.TemporaryDirectory(prefix="wallet-2c4-") as directory:
    scratch = Path(directory)
    env.update(TMPDIR=directory, XDG_RUNTIME_DIR=directory)
    rows_path = scratch / "results.csv"
    cmd = ["timeout", "--kill-after=15s", "12m", sys.executable,
           str(product / "test/functional/test_runner.py"), case,
           "--configfile=" + str(build / "test/config.ini"), "-j1",
           "--tmpdirprefix=" + directory, "--resultsfile=" + str(rows_path)]
    with (scratch / "private.log").open("wb") as log:
        proc = subprocess.run(cmd, cwd=product, env=env, stdout=log, stderr=subprocess.STDOUT)
    raw = (scratch / "private.log").read_text(errors="replace")
    if rows_path.exists():
        with rows_path.open(newline="") as f:
            rows = list(csv.DictReader(f))
        (records / "wallet-results.csv").write_bytes(rows_path.read_bytes())
    else:
        rows = []
    names = [item["test"] for item in rows]
    exact = len(names) == 2 and set(names) == {case, "ALL"}
    refusal = "Wallet contains multiple PQ master seeds; exportwalletbundle only supports single-seed browser wallet exports (-4)"
    error_lines = [line for line in raw.splitlines() if re.match(
        r"^(?:test_framework\.[\w.]+(?:Exception|Error):|[A-Za-z_]+Error:)", line)]
    frames = [f"{Path(path).name}:{line}" for path, line in re.findall(r'File "([^"\n]+)", line (\d+)', raw)]
    status = next((item["status"] for item in rows if item["test"] == case), None)
    same = exact and status == "Failed" and refusal in error_lines[-4:]
    if exact and status == "Failed":
        same = any(line.endswith(refusal) for line in error_lines) and "wallet_importbundle_shielded.py:87" in frames
    verdict = "MATCHED_MAC_EXPORT_REFUSAL" if same else (
        "PASS" if exact and status == "Passed" and proc.returncode == 0 else "UNRESOLVED")
    result = dict(source=source, case=case, fixture_sha256=fixture_digest, runner_exit=proc.returncode,
                  seconds=round(time.monotonic()-started, 2), exact_selection=exact,
                  status=status, verdict=verdict, source_frames=frames[-12:],
                  multiple_seed_export_refusal=any(line.endswith(refusal) for line in error_lines),
                  error_classes=[line.split(":", 1)[0] for line in error_lines[-8:]],
                  reached_own_bundle_export="re-importing the wallet's own bundle" in raw,
                  owned_scratch_removed=False)
    if same:
        result["matched_rpc_error"] = refusal
    elif verdict == "UNRESOLVED":
        result["terminal_summary"] = [
            line[:400] for line in raw.splitlines() if line.startswith(("ERROR:", "WARNING:", "Failed to start "))
        ][-8:]
subprocess.run(["sha256sum", "-c", str(manifest)], check=True)
result["owned_scratch_removed"] = not scratch.exists()
(records / "wallet-case.json").write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps(result, indent=2), flush=True)
raise SystemExit(0 if verdict in {"MATCHED_MAC_EXPORT_REFUSAL", "PASS"} else 1)
