"""Check one contact catalog write failure, retry and two orderly reopens."""
import argparse
import errno
import json
import os
from pathlib import Path
import socket
import tempfile

from pr495 import Helper, sha


HEALTHY = "127.0.0.1:42001"
TARGET = "127.0.0.1:42002"
EXPECTED_HELPER = "28d7ecb6c611e5676d85de7a64038bc7d07cd0b6b2fb2606390d5e6405838ad2"


class ContactHelper(Helper):
    def call(self, method, params):
        self.seq += 1
        request = {"jsonrpc": "1.0", "id": self.seq, "method": method, "params": params}
        with socket.socket(socket.AF_UNIX) as client:
            client.settimeout(10)
            client.connect(str(self.sock))
            client.sendall(json.dumps(request).encode() + b"\n")
            client.shutdown(socket.SHUT_WR)
            with client.makefile("rb") as stream:
                raw = stream.read(1024 * 1024 + 1)
        assert len(raw) <= 1024 * 1024
        reply = json.loads(raw)
        assert reply["id"] == self.seq
        return reply

    def rpc(self, method, params):
        reply = self.call(method, params)
        assert reply["error"] is None, reply
        return reply["result"]


def acknowledged(reply, endpoint):
    value = reply.get("result") or {}
    return (reply["error"] is None and value.get("ok") is True
            and value.get("added") == endpoint)


def analyze(states):
    before = states["healthy"]["disk_sha256"]
    assert states["failed"]["disk_sha256"] == before
    assert TARGET not in states["failed"]["saved"]
    assert HEALTHY in states["after_stop"]["saved"]
    for label in ("healthy", "failed", "retry", "first_reopen", "healthy_retry", "final_reopen"):
        row = states[label]
        assert HEALTHY in row["live"] and HEALTHY in row["saved"], label
        assert len(row["saved"]) == len(set(row["saved"]))
        assert len(row["live"]) == len(set(row["live"]))
    assert states["healthy"]["live"] == states["healthy"]["saved"] == [HEALTHY]
    assert acknowledged(states["healthy"]["rpc"], HEALTHY)
    assert states["healthy_retry"]["live"] == states["healthy_retry"]["saved"] == [HEALTHY, TARGET]
    assert acknowledged(states["healthy_retry"]["rpc"], TARGET)
    assert states["final_reopen"]["live"] == states["final_reopen"]["saved"] == [HEALTHY, TARGET]
    failed = states["failed"]
    retry = states["retry"]
    reopened = states["first_reopen"]
    if (acknowledged(failed["rpc"], TARGET) and failed["live"] == [HEALTHY, TARGET]
            and acknowledged(retry["rpc"], TARGET) and retry["live"] == [HEALTHY, TARGET]
            and retry["saved"] == [HEALTHY] and retry["disk_sha256"] == before
            and states["after_stop"]["disk_sha256"] == before
            and reopened["live"] == reopened["saved"] == [HEALTHY]):
        return "ACKNOWLEDGED_IN_MEMORY_RETRY_SKIPS_SAVE_RESTART_LOSES_CONTACT"
    value = failed["rpc"].get("result") or {}
    if (failed["rpc"]["error"] is None and value.get("ok") is False
            and value.get("added") is False and value.get("reason") == "catalog write failed"
            and failed["live"] == [HEALTHY] and acknowledged(retry["rpc"], TARGET)
            and retry["live"] == retry["saved"] == [HEALTHY, TARGET]
            and retry["disk_sha256"] != before
            and states["after_stop"]["disk_sha256"] == retry["disk_sha256"]
            and reopened["live"] == reopened["saved"] == [HEALTHY, TARGET]
            and reopened["disk_sha256"] == retry["disk_sha256"]):
        return "FAILED_ADD_REPORTED_AND_RETRY_DURABLE"
    return "OBSERVED_OTHER_OUTCOME"


def observe(binary, output, result):
    root = Path(tempfile.mkdtemp(prefix="s2-contact-save-", dir="/tmp"))
    helper = ContactHelper(binary, root, output, "helper")
    catalog = helper.store / "catalog.json"
    obstacle = helper.store / "catalog.json.tmp"
    states = result["states"]

    def capture(label, reply=None, running=True):
        row = {"saved": helper.disk_peers(), "disk_sha256": sha(catalog)}
        if running:
            row["live"] = helper.peers()
        if reply is not None:
            row["rpc"] = reply
        states[label] = row

    try:
        helper.start()
        assert not helper.peers()
        capture("healthy", helper.call("addmodelnode", [HEALTHY]))
        assert states["healthy"]["saved"] == [HEALTHY]
        assert not obstacle.exists()
        obstacle.mkdir()
        sentinel = obstacle / "fixture-sentinel"
        sentinel.write_text("fixture")
        try:
            fd = os.open(obstacle, os.O_WRONLY)
        except OSError as error:
            assert error.errno == errno.EISDIR
            result["write_obstacle_errno"] = error.errno
        else:
            os.close(fd)
            raise AssertionError("expected temporary write to be blocked")
        capture("failed", helper.call("addmodelnode", [TARGET]))
        healthy_duplicate = helper.call("addmodelnode", [HEALTHY])
        assert acknowledged(healthy_duplicate, HEALTHY)
        assert sha(catalog) == states["healthy"]["disk_sha256"]
        result["existing_duplicate_during_write_failure"] = healthy_duplicate
        assert sentinel.read_text() == "fixture"
        sentinel.unlink()
        obstacle.rmdir()
        assert not obstacle.exists()
        capture("retry", helper.call("addmodelnode", [TARGET]))
        helper.stop()
        capture("after_stop", running=False)

        helper.start()
        capture("first_reopen")
        reply = helper.call("addmodelnode", [TARGET])
        capture("healthy_retry", reply)
        duplicate = helper.call("addmodelnode", [TARGET])
        assert acknowledged(duplicate, TARGET)
        assert helper.disk_peers() == helper.peers() == [HEALTHY, TARGET]
        assert sha(catalog) == states["healthy_retry"]["disk_sha256"]
        result["duplicate_did_not_rewrite"] = True
        result["duplicate_rpc"] = duplicate
        helper.stop()

        helper.start()
        capture("final_reopen")
        helper.stop()
        result["starts"] = helper.starts
        assert result["starts"] == 3
        result["verdict"] = analyze(states)
    finally:
        helper.cleanup()
        result["runtime_removed"] = not root.exists()
        result["forced_cleanup_signals"] = helper.cleanup_signals
    assert result["runtime_removed"] and not result["forced_cleanup_signals"]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--helper", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--expected-helper-sha", default=EXPECTED_HELPER)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    result = {"complete": False, "states": {}}
    try:
        result["helper_sha256"] = sha(args.helper)
        assert result["helper_sha256"] == args.expected_helper_sha
        observe(args.helper, args.out, result)
        result["complete"] = True
    except Exception as error:
        result["error"] = repr(error)
        raise
    finally:
        (args.out / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    if result["verdict"] == "FAILED_ADD_REPORTED_AND_RETRY_DURABLE":
        return 0
    if result["verdict"] == "ACKNOWLEDGED_IN_MEMORY_RETRY_SKIPS_SAVE_RESTART_LOSES_CONTACT":
        return 2
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
