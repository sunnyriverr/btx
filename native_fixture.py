#!/usr/bin/env python3
# Copyright (c) 2026 The BTX developers
# Distributed under the MIT software license, see the accompanying
# file COPYING or https://opensource.org/license/mit/.
"""Observe failed restore-copy cleanup and same-name retry, using no real funds.

Preparation only: this file is not a product fix. A successful fixture exit means
controls and cleanup completed, not that the restore-copy hypothesis was proven.
Read result.json's hypothesis_confirmed and individual RPC/file observations.
"""

import argparse
from decimal import Decimal
import hashlib
import json
import os
from pathlib import Path
import resource
import shutil
import signal
import socket
import subprocess
import sys
import tempfile
import threading
import time
import traceback
from urllib.parse import quote


BASE_SHA256 = "ffd6c2dc95df0111a8152b5d5f82244190cad2323981376ffed7c21a1cfd9fc6"
SOFT_CAP = 1024


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def file_record(path):
    record = {"path": str(path), "exists": path.exists()}
    if path.is_file():
        record.update(size=path.stat().st_size, sha256=sha256(path))
    return record


def free_local_port():
    # The daemon's exclusive bind is authoritative; a race is a setup failure.
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
        listener.bind(("127.0.0.1", 0))
        return listener.getsockname()[1]


def ignore_file_size_signal():
    # Ignored dispositions survive exec; exceeding the cap must become a copy
    # error rather than SIGXFSZ termination. Only this child is affected.
    signal.signal(signal.SIGXFSZ, signal.SIG_IGN)


def work_deadline(_signum, _frame):
    raise TimeoutError("Fixture work deadline reached; entering owned cleanup")


class Observation:
    def __init__(self, args, AuthServiceProxy, JSONRPCException):
        self.args = args
        self.AuthServiceProxy = AuthServiceProxy
        self.JSONRPCException = JSONRPCException
        self.started = time.monotonic()
        self.deadline = self.started + 180
        self.process = None
        self.log_thread = None
        self.log_error = None
        self.rpc = None
        self.base_url = None
        self.runtime = None
        self.original_limit = None
        self.cap_active = False
        self.result = {
            "schema_version": 1, "status": "setup_in_progress", "rpc_events": [],
            "hypothesis_confirmed": None,
            "scope": "Linux zero-funds plain restore copy; kernel RLIMIT_FSIZE fault; no mining",
        }

    def save(self):
        self.args.records.mkdir(parents=True, exist_ok=True)
        temporary = self.args.records / "result.json.tmp"
        temporary.write_text(json.dumps(self.result, indent=2, sort_keys=True, default=str) + "\n")
        temporary.replace(self.args.records / "result.json")

    def rpc_for_wallet(self, name):
        return self.AuthServiceProxy(self.base_url + "/wallet/" + quote(name, safe=""), timeout=10)

    def attempt(self, label, method, *args):
        started = time.monotonic()
        try:
            value = method(*args)
            record = {"label": label, "success": True, "result": value}
        except self.JSONRPCException as error:
            record = {"label": label, "success": False, "error": error.error}
        record["elapsed_seconds"] = round(time.monotonic() - started, 6)
        self.result["rpc_events"].append(record)
        self.save()
        return record

    def verify_wallet(self, name, address, label):
        wallet = self.rpc_for_wallet(name)
        info = wallet.getaddressinfo(address)
        mapping = wallet.getaddressesbylabel(label)
        balance = wallet.getbalance()
        assert info["ismine"] is True, info
        assert address in mapping and mapping[address]["purpose"] == "receive", mapping
        assert Decimal(str(balance)) == 0, balance
        return {"address": address, "ismine": info["ismine"], "labels": mapping,
                "balance": balance, "wallet_name": name}

    def healthy_restore(self, name, backup, address, label):
        restored = self.attempt(name + "_restore", self.rpc.restorewallet, name, str(backup), False)
        assert restored["success"] and restored["result"]["name"] == name, restored
        first = self.verify_wallet(name, address, label)
        self.rpc.unloadwallet(name, False)
        self.rpc.loadwallet(name, False)
        reopened = self.verify_wallet(name, address, label)
        self.rpc.unloadwallet(name, False)
        return {"initial": first, "after_unload_reload": reopened}

    def capture_daemon_output(self):
        # Child output is a PIPE. The uncapped controller writes the retained
        # log, so the daemon's file-size cap cannot truncate its own evidence.
        try:
            with (self.args.records / "daemon.log").open("wb") as output:
                while True:
                    block = self.process.stdout.read(65536)
                    if not block:
                        break
                    output.write(block)
                    output.flush()
        except Exception as error:
            self.log_error = repr(error)

    def start(self):
        binary = self.args.binary.resolve(strict=True)
        observed_hash = sha256(binary)
        assert observed_hash == self.args.expected_sha256, (observed_hash, self.args.expected_sha256)
        self.runtime = Path(tempfile.mkdtemp(prefix="btx-restore-copy-", dir="/tmp"))
        self.runtime.chmod(0o700)
        wallet_dir = self.runtime / "wallets"
        wallet_dir.mkdir(mode=0o700)
        port = free_local_port()
        command = [
            str(binary), f"-datadir={self.runtime}", "-regtest=1", "-server=1",
            "-disablewallet=0", f"-walletdir={wallet_dir}", "-keypool=2",
            "-modelnet=0", "-networkactive=0", "-listen=0", "-connect=0",
            "-dnsseed=0", "-discover=0", "-upnp=0", "-natpmp=0",
            "-walletbroadcast=0", "-flushwallet=0", "-persistmempool=0",
            "-nosettings", "-nodebuglogfile", "-printtoconsole=1", "-debug=rpc",
            f"-rpcport={port}", "-rpcbind=127.0.0.1", "-rpcallowip=127.0.0.1",
        ]
        self.result["inputs"] = {
            "binary": str(binary), "binary_sha256": observed_hash,
            "expected_sha256": self.args.expected_sha256,
            "base_source": "dac9aee53520bd49ed320ec7a49b9072fc7d88d9",
            "fixture_sha256": sha256(Path(__file__).resolve()),
            "functional_root": str(self.args.functional_root),
            "command": command, "runtime": str(self.runtime), "rpc_port": port,
            "soft_file_size_cap": SOFT_CAP,
            "debug_file_disabled_by": "-nodebuglogfile (negated debuglogfile option)",
        }
        self.process = subprocess.Popen(
            command, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT, preexec_fn=ignore_file_size_signal,
            start_new_session=True,
        )
        self.result["daemon_pid"] = self.process.pid
        self.log_thread = threading.Thread(target=self.capture_daemon_output, daemon=True)
        self.log_thread.start()
        cookie = self.runtime / "regtest" / ".cookie"
        last_error = None
        until = min(self.deadline - 20, time.monotonic() + 45)
        while time.monotonic() < until:
            if self.process.poll() is not None:
                raise AssertionError(f"Daemon exited during startup: {self.process.returncode}")
            if cookie.is_file():
                try:
                    user, password = cookie.read_text().strip().split(":", 1)
                    self.base_url = f"http://{quote(user, safe='')}:{quote(password, safe='')}@127.0.0.1:{port}"
                    self.rpc = self.AuthServiceProxy(self.base_url, timeout=5)
                    if self.rpc.getblockchaininfo()["chain"] == "regtest":
                        break
                except Exception as error:
                    last_error = str(error)
            time.sleep(0.1)
        else:
            raise AssertionError(f"RPC startup unavailable: {last_error}")
        assert self.rpc.getblockcount() == 0
        assert self.rpc.getnetworkinfo()["networkactive"] is False
        assert self.rpc.getconnectioncount() == 0
        assert self.rpc.listwallets() == [], "Fresh isolated runtime unexpectedly loaded wallets"
        self.result["startup"] = {"chain": "regtest", "height": 0, "networkactive": False,
                                  "connections": 0, "loaded_wallets": []}
        self.save()

    def observe(self):
        self.start()
        wallet_dir = self.runtime / "wallets"
        label = "restore-copy-original-label"
        self.rpc.createwallet("source", False, False, "", False, True, False, False)
        source = self.rpc_for_wallet("source")
        address = source.getnewaddress(label, "p2mr")
        backup = self.runtime / "source.backup.dat"
        source.backupwallet(str(backup))
        original_backup = file_record(backup)
        assert original_backup["size"] > SOFT_CAP, original_backup
        self.result["backup_before"] = original_backup
        self.result["source_wallet"] = self.verify_wallet("source", address, label)
        self.rpc.unloadwallet("source", False)
        self.result["healthy_before"] = self.healthy_restore("healthy-before", backup, address, label)

        # Preserve an actual existing valid wallet.dat, not an arbitrary marker.
        existing = wallet_dir / "healthy-before" / "wallet.dat"
        existing_before = file_record(existing)
        refusal = self.attempt("existing_wallet_file_refused", self.rpc.restorewallet,
                               "healthy-before", str(backup), False)
        assert not refusal["success"] and refusal["error"]["code"] == -36, refusal
        assert "Database file exists" in refusal["error"]["message"], refusal
        assert file_record(existing) == existing_before
        self.result["existing_wallet_file_control"] = {
            "before": existing_before, "after": file_record(existing), "preserved": True,
        }

        target_name = "fault-target"
        target = wallet_dir / target_name
        target.mkdir(mode=0o700)
        sentinel = target / "unrelated-sentinel.txt"
        sentinel.write_bytes(b"Preserve this unrelated pre-existing file.\n")
        sentinel_before = file_record(sentinel)
        partial_path = target / "wallet.dat"
        assert not partial_path.exists()
        assert self.rpc.listwallets() == [], "Fault interval must have no loaded wallet writers"
        self.original_limit = resource.prlimit(self.process.pid, resource.RLIMIT_FSIZE)
        assert self.original_limit[1] == resource.RLIM_INFINITY or self.original_limit[1] >= SOFT_CAP
        self.result["file_size_limits"] = {"before": list(self.original_limit)}
        self.save()
        try:
            # Mark first so an alarm immediately after the syscall still takes
            # the finally restoration path. Restoring after a failed syscall is
            # harmless and preserves the original hard limit.
            self.cap_active = True
            resource.prlimit(self.process.pid, resource.RLIMIT_FSIZE, (SOFT_CAP, self.original_limit[1]))
            self.result["file_size_limits"]["during"] = list(resource.prlimit(self.process.pid, resource.RLIMIT_FSIZE))
            self.save()
            failed_copy = self.attempt("capped_restore", self.rpc.restorewallet,
                                       target_name, str(backup), False)
        finally:
            self.restore_limit()
        partial = file_record(partial_path)
        self.result["after_fault"] = {
            "destination": partial, "backup": file_record(backup),
            "sentinel": file_record(sentinel), "loaded_wallets": self.rpc.listwallets(),
        }
        assert file_record(backup) == original_backup
        assert file_record(sentinel) == sentinel_before
        assert self.rpc.listwallets() == [], "Fault unexpectedly loaded a wallet; invalid fault boundary"
        assert self.process.poll() is None, "Daemon died instead of returning a controlled copy error"
        self.save()

        # No unlink, rename or repair of the partial destination occurs here.
        retry = self.attempt("same_name_retry_without_manual_cleanup", self.rpc.restorewallet,
                             target_name, str(backup), False)
        if retry["success"]:
            self.result["successful_retry_wallet"] = self.verify_wallet(target_name, address, label)
            self.rpc.unloadwallet(target_name, False)
        self.result["destination_after_retry"] = file_record(partial_path)
        self.result["healthy_after"] = self.healthy_restore("healthy-after", backup, address, label)
        assert file_record(backup) == original_backup
        assert file_record(sentinel) == sentinel_before
        assert file_record(existing) == existing_before
        assert self.rpc.getblockcount() == 0
        assert self.rpc.getconnectioncount() == 0

        partial_copy = (partial["exists"] and 0 < partial.get("size", 0) < original_backup["size"])
        retry_blocked = (not retry["success"] and retry["error"]["code"] == -36
                         and "Database file exists" in retry["error"]["message"])
        self.result["hypothesis_confirmed"] = bool(not failed_copy["success"] and partial_copy and retry_blocked)
        self.result["discriminators"] = {
            "capped_restore_failed": not failed_copy["success"],
            "nonempty_short_destination_left": partial_copy,
            "healthy_same_name_retry_refused_for_existing_database": retry_blocked,
            "backup_unchanged": True, "sentinel_unchanged": True,
            "preexisting_real_wallet_file_unchanged": True,
        }
        self.result["status"] = "observation_complete"
        self.save()

    def restore_limit(self):
        if self.cap_active:
            resource.prlimit(self.process.pid, resource.RLIMIT_FSIZE, self.original_limit)
            self.cap_active = False
            observed = resource.prlimit(self.process.pid, resource.RLIMIT_FSIZE)
            self.result["file_size_limits"]["restored"] = list(observed)
            assert observed == self.original_limit, (observed, self.original_limit)
            self.save()

    def cleanup(self):
        cleanup = {"normal_rpc_stop_requested": False, "sigterm_sent": False,
                   "sigkill_sent": False, "runtime_removed": False}
        errors = []
        try:
            self.restore_limit()
        except Exception as error:
            errors.append("restore_limit: " + repr(error))
        if self.process is not None:
            if self.process.poll() is None and self.rpc is not None:
                try:
                    # New bounded connection; never expose cookie credentials.
                    stop_rpc = self.AuthServiceProxy(self.base_url, timeout=3)
                    stop_rpc.stop()
                    cleanup["normal_rpc_stop_requested"] = True
                except Exception as error:
                    errors.append("rpc_stop: " + repr(error))
            if self.process.poll() is None:
                try:
                    self.process.wait(timeout=max(0.1, min(5, self.deadline - time.monotonic() - 3)))
                except subprocess.TimeoutExpired:
                    self.process.terminate()  # Only our exact Popen child.
                    cleanup["sigterm_sent"] = True
            if self.process.poll() is None:
                try:
                    self.process.wait(timeout=max(0.1, min(3, self.deadline - time.monotonic() - 1)))
                except subprocess.TimeoutExpired:
                    self.process.kill()
                    cleanup["sigkill_sent"] = True
                    self.process.wait(timeout=1)
            cleanup["daemon_exit"] = self.process.returncode
            cleanup["daemon_exited"] = self.process.poll() is not None
        if self.log_thread is not None:
            self.log_thread.join(timeout=1)
            cleanup["log_thread_finished"] = not self.log_thread.is_alive()
        if self.log_error:
            errors.append("daemon_log: " + self.log_error)
        if self.runtime is not None:
            # mkdtemp-created exact path only; never a user-supplied datadir.
            assert self.runtime.parent == Path("/tmp") and self.runtime.name.startswith("btx-restore-copy-")
            shutil.rmtree(self.runtime)
            cleanup["runtime_removed"] = not self.runtime.exists()
        cleanup["errors"] = errors
        self.result["cleanup"] = cleanup
        self.result["elapsed_seconds"] = round(time.monotonic() - self.started, 3)
        if errors or cleanup.get("sigterm_sent") or cleanup.get("sigkill_sent") or (
            self.process is not None and (cleanup.get("daemon_exit") != 0 or not cleanup.get("log_thread_finished"))
        ) or (self.runtime is not None and not cleanup["runtime_removed"]):
            self.result["status"] = "fixture_or_cleanup_failure"
        self.save()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--binary", required=True, type=Path)
    parser.add_argument("--records", required=True, type=Path)
    parser.add_argument("--functional-root", type=Path,
                        default=Path("accepted-source/test/functional"))
    parser.add_argument("--expected-sha256", default=BASE_SHA256)
    args = parser.parse_args()
    if sys.platform != "linux" or not hasattr(resource, "prlimit"):
        parser.error("This fixture requires Linux resource.prlimit; no alternate fault is implied")
    args.records = args.records.resolve()
    args.functional_root = args.functional_root.resolve(strict=True)
    sys.path.insert(0, str(args.functional_root))
    from test_framework.authproxy import AuthServiceProxy, JSONRPCException

    observation = Observation(args, AuthServiceProxy, JSONRPCException)
    signal.signal(signal.SIGALRM, work_deadline)
    # Reserve the final 15 seconds of the 180-second process budget for cleanup.
    signal.setitimer(signal.ITIMER_REAL, 165)
    try:
        observation.observe()
    except Exception:
        observation.result["status"] = "fixture_or_control_failure"
        observation.result["exception"] = traceback.format_exc()
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        try:
            observation.cleanup()
        except Exception:
            observation.result["status"] = "fixture_or_cleanup_failure"
            observation.result["cleanup_exception"] = traceback.format_exc()
            observation.save()
    print(json.dumps({"status": observation.result["status"],
                      "hypothesis_confirmed": observation.result["hypothesis_confirmed"],
                      "result_file": str(args.records / "result.json")}))
    return 0 if observation.result["status"] == "observation_complete" else 1


if __name__ == "__main__":
    sys.exit(main())
