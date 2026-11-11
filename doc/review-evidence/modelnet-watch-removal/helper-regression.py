"""Exercise watch removal through the native helper's local socket."""
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
from uuid import uuid4
from contextlib import contextmanager


def request(endpoint, method, *params):
    payload = {"id": "watch-removal", "method": method, "params": list(params)}
    with socket.socket(socket.AF_UNIX) as conn:
        conn.settimeout(5)
        conn.connect(str(endpoint))
        conn.sendall(json.dumps(payload).encode() + b"\n")
        conn.shutdown(socket.SHUT_WR)
        with conn.makefile("rb") as wire:
            return json.loads(wire.readline())


def result(reply):
    assert reply["error"] is None, reply
    return reply["result"]


@contextmanager
def helper(binary, root, modeldir, endpoint):
    env = {k: v for k, v in os.environ.items() if not k.startswith(("BTX_", "DYLD_", "BITCOIN_"))}
    env["BTX_OPENSSL"] = os.environ.get("BTX_OPENSSL", "/opt/homebrew/opt/openssl@3/bin/openssl")
    with (root / "helper.log").open("a+") as log:
        proc = subprocess.Popen(
            [binary, f"-modeldir={modeldir}", f"-modelrpcsocket={endpoint}", "-modelstorage=8MiB",
             "-modellandiscovery=0", "-modelnatpmp=0", "-modelfollowpeers=0"],
            cwd=root, env=env, stdout=log, stderr=subprocess.STDOUT,
        )
        try:
            deadline = time.monotonic() + 20
            while True:
                assert proc.poll() is None, (root / "helper.log").read_text()
                try:
                    result(request(endpoint, "listmodelwatches"))
                    break
                except (FileNotFoundError, ConnectionRefusedError):
                    if time.monotonic() >= deadline:
                        raise
                    time.sleep(0.05)
            yield
            assert proc.poll() is None, (root / "helper.log").read_text()
        finally:
            if proc.poll() is None:
                proc.terminate()
                try:
                    proc.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.wait(timeout=5)
                    raise
                assert proc.returncode == 0, (root / "helper.log").read_text()


def exercise(binary, root, case):
    modeldir = root / case
    modeldir.mkdir()
    endpoint = root / "helper.sock"
    watches = modeldir / "watches.json"
    obstruction = modeldir / "watches.json.tmp"
    selector = {"publisher_id": "b" * 96}
    def mirror(keep_latest):
        return request(endpoint, "setmodelmirror", {
            **selector, "keep_latest": keep_latest, "idempotency_key": uuid4().hex,
        })

    def remove():
        if case == "mirror":
            return mirror(0)
        return request(endpoint, "unwatchmodel", {"watch_id": target})

    def live_ids():
        return {watch["watch_id"] for watch in result(request(endpoint, "listmodelwatches"))["watches"]}

    with helper(binary, root, modeldir, endpoint):
        started = mirror(1) if case == "mirror" else request(endpoint, "watchmodel", {"model_id": "a" * 96})
        target = result(started)["watch_id"]
        other = result(request(endpoint, "watchmodel", {"model_id": "c" * 96}))["watch_id"]
        assert live_ids() == {target, other}
        old = watches.read_bytes()
        obstruction.mkdir()
        failed = remove()
        live_after_fault = target in live_ids()
        assert other in live_ids() and watches.read_bytes() == old

    obstruction.rmdir()
    with helper(binary, root, modeldir, endpoint):
        assert live_ids() == {target, other}, "failed save should retain the durable state"
        recovered = result(remove())
        assert recovered["removed" if case == "direct" else "applied"] is True, recovered
        assert live_ids() == {other}
        assert result(request(endpoint, "unwatchmodel", {"watch_id": target}))["removed"] is False

    with helper(binary, root, modeldir, endpoint):
        assert live_ids() == {other}, "healthy retry should survive a restart"

    err = failed.get("error")
    print(json.dumps({"case": case, "fault_reply": failed, "retained_live_on_fault": live_after_fault,
                      "restart_after_fault": "watch present", "retry": "passed",
                      "restart_after_retry": "watch absent, unrelated watch intact"}), flush=True)
    return isinstance(err, dict) and err.get("code") == "IO_ERROR" and live_after_fault


if __name__ == "__main__":
    with tempfile.TemporaryDirectory(prefix="bw-", dir="/tmp") as directory:
        checks = [exercise(str(Path(sys.argv[1]).resolve()), Path(directory), case)
                  for case in ("direct", "mirror")]
    sys.exit(0 if all(checks) else 1)
