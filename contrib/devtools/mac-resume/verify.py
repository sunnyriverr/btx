"""Bounded native build and #472 regression using the verified Mac checkpoint."""
from pathlib import Path
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
import traceback

W = Path(os.environ["GITHUB_WORKSPACE"])
HERE = Path(__file__).resolve().parent
OUT = W / "pr472-records"
OUT.mkdir(exist_ok=True)
SRC = W / "product"
BUILD = W / "mac-config-build"
BASE = "dac9aee53520bd49ed320ec7a49b9072fc7d88d9"
state = {"source": BASE, "steps": [], "complete": False}

def run(args, label, timeout=120, env=None, expected=0):
    print("START", label, flush=True)
    started = time.monotonic()
    with (OUT / (label + ".log")).open("w") as log:
        proc = subprocess.Popen(list(map(str, args)), env=env, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
        try:
            code = proc.wait(timeout)
        except subprocess.TimeoutExpired:
            import signal
            os.killpg(proc.pid, signal.SIGTERM)
            try: proc.wait(10)
            except subprocess.TimeoutExpired:
                os.killpg(proc.pid, signal.SIGKILL)
                proc.wait(5)
            raise RuntimeError(label + " timed out")
    state["steps"].append({"label": label, "exit": code, "seconds": time.monotonic() - started})
    (OUT / "result.json").write_text(json.dumps(state, indent=2) + "\n")
    assert code == expected, (label, code, expected)

def real_regression(phase, expected):
    destination = OUT / phase
    destination.mkdir()
    identity = {"source": BASE, "artifact": "native incremental build; see input checkpoint and compile records", "members": {}}
    for name in ("btxd", "btx-modeld", "btx-guardd", "btx-cli"):
        path = BUILD / "bin" / name
        assert path.is_file()
        identity["members"]["bin/" + name] = hashlib.sha256(path.read_bytes()).hexdigest()
    (destination / "mac-baseline-identity.json").write_text(json.dumps(identity, indent=2))
    env = dict(os.environ, BTX472_PACKAGE=str(BUILD), BTX472_OUTPUT=str(destination))
    run([sys.executable, HERE / "run-focused-regression.py"], phase + "-real-regression", 240, env=env, expected=expected)
    result = json.loads((destination / "mac-regression-result.json").read_text())
    assert all(result["controls"].values()) and result["node_exit"] == 0 and result["disposable_runtime_removed"]
    assert result["regression_passed"] == (expected == 0)
    if expected: assert result["matches_reported_failure"]
    return identity

try:
    assert json.loads((W / "restore-records/restore-result.json").read_text())["complete"]
    run(["git", "-C", SRC, "fetch", "--depth=1", "origin", BASE], "fetch-current-base")
    run(["git", "-C", SRC, "checkout", "--detach", BASE], "select-current-base")
    run(["cmake", "-S", SRC, "-B", BUILD], "current-configure", 300)
    run(["ninja", "-C", BUILD, "-n", "btxd", "btx-modeld", "btx-cli", "btx-guardd"], "current-dry-plan")
    run(["ninja", "-C", BUILD, "-j2", "btxd", "btx-modeld", "btx-cli", "btx-guardd"], "baseline-build", 1500)
    state["baseline"] = real_regression("baseline", 1)
    manifest = json.loads((HERE / "candidate-manifest.json").read_text())
    for relative, digests in manifest.items():
        target = SRC / relative
        assert hashlib.sha256(target.read_bytes()).hexdigest() == digests["before"], relative
        replacement = HERE / "candidate" / relative
        assert hashlib.sha256(replacement.read_bytes()).hexdigest() == digests["after"], relative
        shutil.copy2(replacement, target)
        # Ninja must observe candidate headers newer than the restored objects.
        os.utime(target, None)
    run(["git", "-C", SRC, "diff", "--check"], "candidate-whitespace")
    run(["git", "-C", SRC, "diff", "--stat"], "candidate-source-stat")
    run(["ninja", "-C", BUILD, "-n", "btxd", "btx-modeld"], "candidate-dry-plan")
    run(["ninja", "-C", BUILD, "-j2", "btxd", "btx-modeld"], "candidate-build", 1500)
    state["candidate"] = real_regression("candidate", 0)
    env = dict(os.environ, BTXD=str(BUILD / "bin/btxd"), BTXCLI=str(BUILD / "bin/btx-cli"))
    run([sys.executable, SRC / "test/functional/rpc_modelnet_wallet_restriction.py",
         "--configfile=" + str(BUILD / "test/config.ini"),
         "--tmpdir=/private/tmp/pr472-functional",
         "--timeout-factor=2"], "maintained-stateful-regression", 300, env=env)
    state["complete"] = True
except Exception as error:
    state["error"] = repr(error)
    state["traceback"] = traceback.format_exc()
finally:
    state["free_bytes"] = shutil.disk_usage(W).free
    (OUT / "result.json").write_text(json.dumps(state, indent=2) + "\n")
sys.exit(0 if state["complete"] else 1)
