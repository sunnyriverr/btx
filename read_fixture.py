"""Matched observations for the interrupted read boundary of the real importlabels RPC."""
import argparse
import json
import os
import signal
import sqlite3
import sys
import time
import traceback
from pathlib import Path

from daemon_fixture import BASE_SHA256, Observation, sha256, work_deadline


def record(address, label):
    return json.dumps({"type": "addr", "ref": address, "label": label}).encode()


class Labels(Observation):
    def child_env(self):
        return dict(os.environ, LD_PRELOAD=str(self.args.shim.resolve(strict=True)),
                    BTX_LABEL_READ_TARGET=str(self.runtime / "read.jsonl"),
                    BTX_LABEL_READ_ARM=str(self.runtime / "read.arm"))

    def label(self, wallet, address):
        info = wallet.getaddressinfo(address)
        assert info["ismine"] is True
        labels = info["labels"]
        assert len(labels) == 1, labels
        return labels[0]

    def reopen(self, name):
        self.rpc.unloadwallet(name, False)
        self.rpc.loadwallet(name, False)
        return self.rpc_for_wallet(name)

    def read_case(self):
        name = "read-probe"
        self.rpc.createwallet(name, False, False, "", False, True, False, False)
        wallet = self.rpc_for_wallet(name)
        before = ["old-first", "old-second"]
        addresses = [wallet.getnewaddress(label, "p2mr") for label in before]
        after = ["new-first", "new-second"]
        source = self.runtime / "read.jsonl"
        prefix = record(addresses[0], after[0]).ljust(255, b" ") + b"\n"
        assert len(prefix) == 256
        source.write_bytes(prefix + record(addresses[1], after[1]))
        original = sha256(source)
        malformed = self.runtime / "malformed.jsonl"
        malformed.write_bytes(prefix + b"invalid json\n")
        rejected = self.attempt("malformed_control", wallet.importlabels, str(malformed))
        assert not rejected["success"]
        assert [self.label(wallet, a) for a in addresses] == before
        arm = self.runtime / "read.arm"
        arm.touch()
        try:
            reply = self.attempt("read_fault", wallet.importlabels, str(source))
        finally:
            arm.unlink()
        live = [self.label(wallet, a) for a in addresses]
        wallet = self.reopen(name)
        reopened = [self.label(wallet, a) for a in addresses]
        retry = self.attempt("read_retry", wallet.importlabels, str(source))
        wallet = self.reopen(name)
        recovered = [self.label(wallet, a) for a in addresses]
        self.rpc.unloadwallet(name, False)
        assert retry["success"] and retry["result"]["imported"] == 2 and recovered == after
        assert sha256(source) == original
        wallet = self.rpc_for_wallet(name)
        self.rpc.loadwallet(name, False)
        empty = self.runtime / "empty.jsonl"
        empty.touch()
        empty_reply = self.attempt("empty_control", wallet.importlabels, str(empty))
        assert empty_reply["success"] and empty_reply["result"]["imported"] == 0
        assert [self.label(wallet, a) for a in addresses] == after
        self.rpc.unloadwallet(name, False)
        self.result["read_probe"] = {
            "oracle_pass": not reply["success"] and reply["error"]["code"] == -4
                           and "Failed to read labels import file" in reply["error"]["message"]
                           and live == reopened == before,

            "fault": "read returns EIO after byte 256, immediately after one complete JSONL record",
            "live_labels": live, "reopened_labels": reopened, "healthy_retry_reopened_labels": recovered,
            "source_unchanged": True,
            "false_success": reply["success"] and reply["result"]["imported"] == 1
                             and reopened == [after[0], before[1]],
        }
        self.save()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--binary", type=Path, required=True)
    parser.add_argument("--records", type=Path, required=True)
    parser.add_argument("--shim", type=Path, required=True)
    parser.add_argument("--functional-root", type=Path, default=Path("accepted-source/test/functional"))
    parser.add_argument("--expected-sha256", default=BASE_SHA256)
    args = parser.parse_args()
    assert sys.platform == "linux"
    args.records = args.records.resolve()
    args.functional_root = args.functional_root.resolve(strict=True)
    sys.path.insert(0, str(args.functional_root))
    from test_framework.authproxy import AuthServiceProxy, JSONRPCException

    obs = Labels(args, AuthServiceProxy, JSONRPCException)
    obs.result["scope"] = "Linux synthetic wallet importlabels with exact input read EIO"
    obs.result["fixture_sha256"] = sha256(Path(__file__))
    obs.result["launcher_sha256"] = sha256(Path(__file__).with_name("daemon_fixture.py"))
    obs.result["shim_sha256"] = sha256(args.shim)
    signal.signal(signal.SIGALRM, work_deadline)
    signal.setitimer(signal.ITIMER_REAL, 165)
    try:
        obs.start()
        start = time.monotonic()
        obs.read_case()
        obs.result["read_elapsed_seconds"] = round(time.monotonic() - start, 3)
        obs.result["status"] = "observation_complete"
    except Exception:
        obs.result["read_error"] = traceback.format_exc()
        obs.result["status"] = "inconclusive"
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        obs.cleanup()
    log = (args.records / "daemon.log").read_text(errors="replace")
    obs.result["fault_hits"] = {"read": log.count("BTX_LABEL_PROBE: target read returned EIO after prefix")}
    if "read_probe" not in obs.result or obs.result["fault_hits"]["read"] != 1:
        obs.result["status"] = "inconclusive"
    obs.save()
    print(json.dumps(obs.result, indent=2, default=str))
    if obs.result["status"] != "observation_complete":
        return 2
    return 0 if obs.result["read_probe"]["oracle_pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
