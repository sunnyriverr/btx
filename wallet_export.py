"""One Windows wallet export matrix, using only a generated zero-funds regtest wallet."""
import base64
import hashlib
import json
import os
from pathlib import Path
import secrets
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request

MOUNT, BASELINE, CANDIDATE = map(Path, sys.argv[1:4])
record = Path(os.environ["GITHUB_WORKSPACE"]) / "pr470-records/wallet-results.json"
expected_hashes = json.loads(record.with_name("build.json").read_text())
os.chdir(record.parent)
state = {"status": "RUNNING", "cap_bytes": 64 * 1024**2, "variants": {}}
phases = ("normal", "full")


def save():
    record.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")


def request(port, cookie, method, params=None, wallet=None):
    authorization = base64.b64encode(cookie.read_bytes().strip()).decode()
    endpoint = "/wallet/" + wallet if wallet else "/"
    req = urllib.request.Request(f"http://127.0.0.1:{port}{endpoint}",
        data=json.dumps({"jsonrpc": "2.0", "id": "wallet-fixture", "method": method, "params": params or []}).encode(),
        headers={"Authorization": "Basic " + authorization, "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=60) as response:
            return json.load(response)
    except urllib.error.HTTPError as error:
        return json.load(error)


def fill(path):
    available = shutil.disk_usage(MOUNT).free
    assert 0 < available <= state["cap_bytes"]
    with path.open("xb", buffering=0) as padding:
        block = bytes(1024 * 1024)
        while available:
            amount = min(available, len(block))
            assert padding.write(block[:amount]) == amount
            available -= amount
        os.fsync(padding.fileno())
    assert shutil.disk_usage(MOUNT).free == 0


def run(node, label, fixture_seed):
    with node.open("rb") as binary:
        entry = {"cases": {}, "sha256": hashlib.file_digest(binary, "sha256").hexdigest()}
    state["variants"][label] = entry
    save()
    assert entry["sha256"] == expected_hashes[label + "_sha256"]
    with tempfile.TemporaryDirectory(prefix="wallet-470-", dir=os.environ["RUNNER_TEMP"]) as root:
        data = Path(root)
        cookie = data / "regtest/.cookie"
        with socket.socket() as listener:
            listener.bind(("127.0.0.1", 0))
            port = listener.getsockname()[1]
        args = [str(node), "-regtest", f"-datadir={data}", "-server=1",
                "-rpcbind=127.0.0.1", "-rpcallowip=127.0.0.1", f"-rpcport={port}",
                "-listen=0", "-listenonion=0", "-networkactive=0", "-connect=0",
                "-dnsseed=0", "-fixedseeds=0", "-discover=0", "-natpmp=0", "-autoupdate=0",
                "-modelnet=0", "-autoshieldcoinbase=0", "-keypool=4", "-dbcache=32"]
        process = subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        def wire(method, params=None, wallet=None):
            return request(port, cookie, method, params, wallet)
        def call(method, params=None, wallet=None):
            reply = wire(method, params, wallet)
            if reply.get("error"):
                raise RuntimeError(f"{method} returned RPC error {reply['error']['code']}")
            return reply["result"]

        def validate(path, reply):
            assert reply.get("error") is None and reply["result"]["labels"] == len(expected_labels)
            payload = path.read_bytes()
            rows = [json.loads(line) for line in payload.splitlines()]
            assert len(rows) == len(expected_labels)
            assert all(row["type"] == "addr" for row in rows)
            assert {row["ref"]: row["label"] for row in rows} == expected_labels
            assert 512 < len(payload) < 4096, "Expected one buffered label export"
            return {"bytes": len(payload), "complete_jsonl": True, "labels": len(rows),
                    "sha256": hashlib.sha256(payload).hexdigest()}

        def export(path):
            return wire("exportlabels", [str(path)], "export")

        padding = MOUNT / "padding.bin"
        outputs = [MOUNT / f"{label}-{phase}.jsonl" for phase in phases]
        try:
            deadline = time.monotonic() + 50
            while True:
                try:
                    chain = call("getblockchaininfo")
                    break
                except (OSError, RuntimeError):
                    if process.poll() is not None or time.monotonic() >= deadline:
                        raise
                    time.sleep(.3)
            assert chain["chain"] == "regtest" and chain["blocks"] == 0
            assert call("getconnectioncount") == 0 and not call("getnetworkinfo")["networkactive"]
            assert call("getrawmempool") == []
            fixture = data / "synthetic.btxwallet"
            fixture.write_text(json.dumps({"format":"btx-wallet-bundle","version":1,"network":"regtest",
                "pq_master_seed":fixture_seed,"coin_type":1,"account":0,"birthday":1,
                "algorithms":["ml-dsa-44","slh-dsa-128s"]}), encoding="utf-8")
            restored = call("restorewalletbundle", ["export", str(fixture), None, False])
            fixture.unlink()
            assert restored["success"] and restored["descriptors_imported"] == 2
            assert call("getbalance", wallet="export") == 0
            expected_labels = {}
            for index in range(8):
                text = f"disposable label {index}"
                address = call("getnewaddress", [text, "p2mr"], "export")
                expected_labels[address] = text
            assert len(expected_labels) == 8
            normal, fault = outputs
            reply = export(normal)
            entry["cases"]["normal"] = validate(normal, reply)
            normal_length = normal.stat().st_size
            existing_bytes = normal.read_bytes()
            denied = export(normal)
            assert denied.get("error", {}).get("code") == -8 and normal.read_bytes() == existing_bytes
            entry["cases"]["existing_file_refusal"] = {"code": denied["error"]["code"], "bytes_unchanged": True}
            fill(padding)
            entry["free_bytes_at_fault"] = shutil.disk_usage(MOUNT).free
            reply = export(fault)
            error = reply.get("error")
            returned = (reply.get("result") or {}).get("labels") == len(expected_labels) and error is None
            file_bytes = fault.stat().st_size if fault.exists() else None
            write_error = bool(error and error["message"] == "Failed to write labels export file")
            entry["cases"]["full"] = {"success": returned, "rpc_error_code": error["code"] if error else None,
                "write_error": write_error, "remaining_file_bytes": file_bytes}
            save()
            padding.unlink()
            if fault.exists() and label == "baseline":
                fault.unlink()
            entry["cases"]["retry"] = validate(fault, export(fault))
            entry["cases"]["retry"]["same_destination"] = True
            entry["cases"]["retry"]["manual_partial_removal"] = label == "baseline" and file_bytes is not None
            assert call("getrawmempool") == [] and call("getblockcount") == 0
            assert call("getbalance", wallet="export") == 0
            entry["outcome"] = ("FALSE_SUCCESS" if returned is True and file_bytes is not None and file_bytes < normal_length
                else "FAILURE_AND_CLEANUP" if returned is not True and error and error["code"] == -4 and write_error and file_bytes is None
                else "UNEXPECTED")
        finally:
            for path in [padding, *outputs]:
                path.unlink(missing_ok=True)
            if process.poll() is None:
                try:
                    call("stop")
                    process.wait(timeout=30)
                except Exception:
                    process.kill()
                    process.wait(timeout=15)
                    entry["forced_stop"] = True
            entry["node_clean_exit"] = process.returncode == 0 and not entry.get("forced_stop") and not cookie.exists()
            save()
    entry["runtime_removed"] = not data.exists()
    assert entry["node_clean_exit"] and entry["runtime_removed"]
    save()


try:
    assert MOUNT.is_absolute() and MOUNT.parent == MOUNT
    assert MOUNT.drive.upper() != os.environ["SystemDrive"].upper()
    assert 0 < shutil.disk_usage(MOUNT).total < 64 * 1024**2
    seed = secrets.token_hex(32)
    run(BASELINE, "baseline", seed)
    run(CANDIDATE, "candidate", seed)
    assert state["variants"]["baseline"]["outcome"] == "FALSE_SUCCESS"
    assert state["variants"]["candidate"]["outcome"] == "FAILURE_AND_CLEANUP"
    state["status"] = "BEFORE_AFTER_AND_RETRY_PASS"
finally:
    save()
