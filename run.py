from pathlib import Path
import hashlib
import json
import os
import subprocess
import sys

evidence = Path(__file__).resolve().parent
runtime = Path("/Volumes/BTXDeposit")
source = runtime / "source"
build = runtime / "build"
test = source / "test/functional/wallet_bcp1_deposit_notify_confirmed.py"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


phase, = sys.argv[1:]
assert phase in ("before", "after")
assert digest(test) == json.loads((evidence / "test-identity.json").read_text())["sha256"]
env = dict(os.environ, TMPDIR=str(runtime / "tmp"), PYTHONDONTWRITEBYTECODE="1")
for name in ("BITCOIND", "BITCOINCLI", "BTXD", "BTXCLI"):
    env.pop(name, None)
env["BTXD"] = str(runtime / "tools/daemon-wrapper")
tmp = runtime / f"regtest-{phase}"
log = evidence / f"{phase}.log"
args = [sys.executable, str(test), "--descriptors", f"--configfile={build / 'test/config.ini'}",
        f"--tmpdir={tmp}", "--portseed=528", "--nocleanup"]
with log.open("w") as out:
    process = subprocess.run(args, env=env, stdout=out, stderr=subprocess.STDOUT, timeout=420)
output = log.read_text()
matched = (
    "A spent deposit confirms again when its block reconnects" in output and
    "AssertionError: not(0 == 1)" in output and process.returncode == 1
) if phase == "before" else (process.returncode == 0 and "Tests successful" in output)
receipt = dict(phase=phase, exit=process.returncode, matched_expected=matched, test_sha256=digest(test),
               product_sha256=digest(source / "src/wallet/bcp1_deposit.cpp"),
               binaries={n:digest(build / "bin" / n) for n in ("btxd", "btx-cli")},
               wrapper_sha256=digest(runtime / "tools/daemon-wrapper"), log_sha256=digest(log))
(evidence / f"{phase}-result.json").write_text(json.dumps(receipt, indent=2) + "\n")
print(json.dumps(receipt))
raise SystemExit(0 if matched else 1)
