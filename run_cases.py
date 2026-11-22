"""Run the two pinned PR 921 cases using retained binaries only."""
import hashlib
import json
import os
import signal
import subprocess
import sys
import tempfile
import time
from pathlib import Path

root = Path.cwd()
identity = json.loads((root / "input.json").read_text())
product = root / "product"
runtime = root / "runtime"
out = root / "receipt"
tests = identity["tested_scripts"]


def git(*args):
    return subprocess.check_output(["git", "-C", str(product), *args], text=True).strip()


def sha(path):
    with path.open("rb") as f:
        return hashlib.file_digest(f, "sha256").hexdigest()


def verify():
    assert sha(runtime / "bin/btxd") == identity["daemon_sha256"]
    assert sha(runtime / "bin/btx-cli") == identity["cli_sha256"]
    assert all(sha(product / path) == value for path, value in tests.items())


assert git("rev-parse", "HEAD") == identity["tested_patch_commit"]
assert git("rev-parse", "HEAD^") == identity["source"]
assert set(git("diff", "--name-only", "HEAD^", "HEAD").splitlines()) == set(tests)
verify()
with tempfile.TemporaryDirectory(prefix="btx-linux-921-") as temp:
    scratch = Path(temp)
    config = scratch / "config.ini"
    config.write_text(f"""[environment]
CLIENT_NAME=BTX
CLIENT_BUGREPORT=https://github.com/btxchain/btx/issues
SRCDIR={product}
BUILDDIR={runtime}
EXEEXT=
RPCAUTH={product}/share/rpcauth/rpcauth.py
[components]
ENABLE_BITCOIND=true
ENABLE_CLI=true
ENABLE_WALLET=true
USE_SQLITE=true
""")
    shims = scratch / "no-build"
    shims.mkdir()
    shim = shims / "cmake"
    shim.write_text('#!/bin/sh\nprintf "%s\\n" "$0" >> "$BTX_BUILD_ATTEMPTS"\nexit 125\n')
    shim.chmod(0o755)
    for tool in ("make", "ninja"):
        (shims / tool).symlink_to("cmake")
    env = dict(os.environ, PATH=f"{shims}:{os.environ['PATH']}",
               BTX_BUILD_ATTEMPTS=str(out / "build-attempts.log"), PYTHONDONTWRITEBYTECODE="1")
    for name in ("BTXD", "BTXCLI", "BITCOIND", "BITCOINCLI"):
        env.pop(name, None)
    receipt = dict(source=identity["source"], pr_head=identity["tested_patch_commit"],
                   artifact=identity["checkpoint"], cases={})
    for test in sorted(tests):
        name = Path(test).stem
        log = out / f"{name}.log"
        args = [sys.executable, "-B", str(product / test), f"--configfile={config}",
                f"--tmpdir={scratch / name}", "--timeout-factor=1", "--portseed=3341"]
        start = time.monotonic()
        timeout = False
        with log.open("x") as f:
            proc = subprocess.Popen(args, env=env, stdout=f, stderr=subprocess.STDOUT, start_new_session=True)
            try:
                code = proc.wait(timeout=240)
            except subprocess.TimeoutExpired:
                timeout = True
                os.killpg(proc.pid, signal.SIGTERM)
                try:
                    code = proc.wait(timeout=8)
                except subprocess.TimeoutExpired:
                    os.killpg(proc.pid, signal.SIGKILL)
                    code = proc.wait()
        text = log.read_text()
        status = ("timeout" if timeout else "skip" if code == 77 or "Test skipped" in text
                  else "pass" if code == 0 and "Tests successful" in text else "fail")
        result = dict(status=status, exit=code, seconds=round(time.monotonic() - start, 2))
        receipt["cases"][name] = result
        print(name, result, flush=True)
    verify()
    receipt["hashes_unchanged"] = True
    receipt["build_attempts"] = (out / "build-attempts.log").exists()
    (out / "results.json").write_text(json.dumps(receipt, indent=2) + "\n")
    sys.exit(receipt["build_attempts"] or not all(v["status"] == "pass" for v in receipt["cases"].values()))
