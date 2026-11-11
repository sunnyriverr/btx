#!/usr/bin/env python3
# Copyright (c) 2026 The BTX developers
# Distributed under the MIT software license, see the accompanying
# file COPYING or https://opensource.org/license/mit/.
"""Matched baseline/candidate restore-copy qualification with synthetic wallets.

The same RPC/file sequence runs for both expectations. Product outcomes are
observed first; --expect classifies them after controls and owned cleanup.
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
        self.expected_product_exit = False
        self.result = {
            "schema_version": 2, "status": "setup_in_progress", "rpc_events": [],
            "expectation": args.expect, "fault_cases": {},
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
        except Exception as error:
            # NEW-directory stock cleanup may terminate the daemon. Preserve
            # transport failures as observations; they are not RPC refusals.
            record = {"label": label, "success": False,
                      "transport_exception": repr(error)}
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

    def retry_wallet(self, name, backup, address, label):
        retry = self.attempt(name + "_same_name_retry_without_manual_cleanup",
                             self.rpc.restorewallet, name, str(backup), False)
        if retry["success"]:
            first = self.verify_wallet(name, address, label)
            self.rpc.unloadwallet(name, False)
            loaded = self.attempt(name + "_reload", self.rpc.loadwallet, name, False)
            assert loaded["success"], loaded
            reopened = self.verify_wallet(name, address, label)
            self.rpc.unloadwallet(name, False)
            retry["wallet_verification"] = {"initial": first, "after_unload_reload": reopened}
        return retry

    def capped_copy(self, name, backup, sentinel=None, allow_product_exit=False):
        """No destination cleanup between fault and retry, for either binary."""
        target = self.runtime / "wallets" / name
        wallet_file = target / "wallet.dat"
        case = {"destination_before": file_record(wallet_file),
                "directory_before": target.exists()}
        self.result["fault_cases"][name] = case
        assert not wallet_file.exists()
        assert self.rpc.listwallets() == []
        before = resource.prlimit(self.process.pid, resource.RLIMIT_FSIZE)
        assert before[1] == resource.RLIM_INFINITY or before[1] >= SOFT_CAP
        self.original_limit = before
        case["limits_before"] = list(before)
        self.result["active_fault_case"] = name
        try:
            self.cap_active = True
            resource.prlimit(self.process.pid, resource.RLIMIT_FSIZE, (SOFT_CAP, before[1]))
            case["limits_during"] = list(resource.prlimit(self.process.pid, resource.RLIMIT_FSIZE))
            self.save()
            case["copy_reply"] = self.attempt(name + "_capped_restore", self.rpc.restorewallet,
                                               name, str(backup), False)
            if "transport_exception" in case["copy_reply"] and allow_product_exit:
                # A transport exception alone cannot establish daemon death.
                try:
                    self.process.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    pass
        finally:
            self.restore_limit()
        case["daemon_exit_after_copy"] = self.process.poll()
        case["daemon_alive_after_copy"] = self.process.poll() is None
        case["destination_after_copy"] = file_record(wallet_file)
        case["directory_after_copy"] = target.exists()
        case["directory_children_after_copy"] = sorted(p.name for p in target.iterdir()) if target.is_dir() else []
        if sentinel is not None:
            case["sentinel_after_copy"] = file_record(sentinel)
        case["backup_after_copy"] = file_record(backup)
        if case["daemon_alive_after_copy"]:
            case["loaded_wallets_after_copy"] = self.rpc.listwallets()
            assert case["loaded_wallets_after_copy"] == [], case
        else:
            self.expected_product_exit = bool(allow_product_exit)
            case["retry_not_attempted"] = "daemon exited during capped NEW-directory restore"
        self.save()
        return case

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
        self.args.records.mkdir(parents=True, exist_ok=True)
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

        # Refuse an existing wallet.dat symlink without following/truncating or
        # unlinking it. Its target is a real, unloaded synthetic wallet.
        link_dir = wallet_dir / "symlink-target"
        link_dir.mkdir(mode=0o700)
        link = link_dir / "wallet.dat"
        link.symlink_to(existing)
        link_text = os.readlink(link)
        linked_refusal = self.attempt("symlink_wallet_file_refused", self.rpc.restorewallet,
                                      "symlink-target", str(backup), False)
        link_preserved = link.is_symlink() and os.readlink(link) == link_text
        target_preserved = file_record(existing) == existing_before
        self.result["symlink_wallet_control"] = {
            "reply": linked_refusal, "is_symlink": link.is_symlink(),
            "link_text": link_text, "link_preserved": link_preserved,
            "target_before": existing_before, "target_after": file_record(existing),
            "target_preserved": target_preserved,
        }
        assert not linked_refusal["success"] and "error" in linked_refusal, linked_refusal
        assert link_preserved and target_preserved

        invalid = self.runtime / "invalid-regular-backup.dat"
        invalid.write_bytes(b"This regular file is not a wallet database.\n")
        invalid_before = file_record(invalid)
        invalid_target = wallet_dir / "invalid-backup-control"
        invalid_reply = self.attempt("invalid_regular_backup_refused", self.rpc.restorewallet,
                                      "invalid-backup-control", str(invalid), False)
        self.result["invalid_regular_backup_control"] = {
            "reply": invalid_reply, "before": invalid_before, "after": file_record(invalid),
            "target_directory_exists": invalid_target.exists(),
            "existing_wallet_unchanged": file_record(existing) == existing_before}
        assert not invalid_reply["success"] and "error" in invalid_reply, invalid_reply
        assert file_record(invalid) == invalid_before and not invalid_target.exists()
        assert file_record(existing) == existing_before and file_record(backup) == original_backup

        target_name = "fault-target"
        target = wallet_dir / target_name
        target.mkdir(mode=0o700)
        sentinel = target / "unrelated-sentinel.txt"
        sentinel.write_bytes(b"Preserve this unrelated pre-existing file.\n")
        sentinel_before = file_record(sentinel)
        partial_path = target / "wallet.dat"
        existing_case = self.capped_copy(target_name, backup, sentinel=sentinel)
        assert file_record(backup) == original_backup
        assert file_record(sentinel) == sentinel_before
        assert existing_case["daemon_alive_after_copy"], "existing-directory copy ended daemon"
        existing_case["retry_reply"] = self.retry_wallet(target_name, backup, address, label)
        existing_case["destination_after_retry"] = file_record(partial_path)
        existing_case["sentinel_after_retry"] = file_record(sentinel)
        existing_case["sentinel_preserved"] = file_record(sentinel) == sentinel_before
        existing_case["directory_preserved"] = target.is_dir()
        self.result["healthy_after"] = self.healthy_restore("healthy-after", backup, address, label)
        assert file_record(backup) == original_backup
        assert file_record(sentinel) == sentinel_before
        assert file_record(existing) == existing_before
        assert self.rpc.getblockcount() == 0
        assert self.rpc.getconnectioncount() == 0

        partial = existing_case["destination_after_copy"]
        failed_copy = existing_case["copy_reply"]
        retry = existing_case["retry_reply"]
        partial_copy = (partial["exists"] and 0 < partial.get("size", 0) < original_backup["size"])
        retry_blocked = (not retry["success"] and retry.get("error", {}).get("code") == -36
                         and "Database file exists" in retry.get("error", {}).get("message", ""))
        self.result["hypothesis_confirmed"] = bool(not failed_copy["success"] and partial_copy and retry_blocked)
        self.result["discriminators"] = {
            "capped_restore_failed": not failed_copy["success"],
            "nonempty_short_destination_left": partial_copy,
            "healthy_same_name_retry_refused_for_existing_database": retry_blocked,
            "backup_unchanged": True, "sentinel_unchanged": True,
            "preexisting_real_wallet_file_unchanged": True,
        }

        # NEW directory is deliberately last: stock's cleanup may assume an
        # interrupted copy left the directory empty and terminate the daemon.
        # Earlier independent controls remain recorded if that happens.
        new_name = "fault-new-directory"
        new_target = wallet_dir / new_name
        assert not new_target.exists()
        new_case = self.capped_copy(new_name, backup, allow_product_exit=True)
        if new_case["daemon_alive_after_copy"]:
            new_case["retry_reply"] = self.retry_wallet(new_name, backup, address, label)
            new_case["destination_after_retry"] = file_record(new_target / "wallet.dat")
        self.result["preservation_after_all_cases"] = {
            "backup_unchanged": file_record(backup) == original_backup,
            "sentinel_unchanged": file_record(sentinel) == sentinel_before,
            "existing_real_wallet_unchanged": file_record(existing) == existing_before,
            "symlink_and_target_unchanged": (link.is_symlink() and os.readlink(link) == link_text
                                            and file_record(existing) == existing_before),
        }
        self.result["backup_after_all_cases"] = file_record(backup)
        assert all(self.result["preservation_after_all_cases"].values())
        if self.process.poll() is None:
            assert self.rpc.getblockcount() == 0
            assert self.rpc.getconnectioncount() == 0
            assert self.rpc.listwallets() == []
        self.result["lifecycle_limit"] = "successful retry verified through unload/load; no whole-daemon restart"
        self.result["status"] = "observation_complete"
        self.save()

    def restore_limit(self):
        if self.cap_active:
            case = self.result["fault_cases"][self.result["active_fault_case"]]
            if self.process.poll() is not None:
                self.cap_active = False
                case["limit_restore_not_applicable"] = "capped child already exited; no live limited process"
                self.save()
                return
            resource.prlimit(self.process.pid, resource.RLIMIT_FSIZE, self.original_limit)
            self.cap_active = False
            observed = resource.prlimit(self.process.pid, resource.RLIMIT_FSIZE)
            case["limits_restored"] = list(observed)
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
        cleanup["new_directory_product_exit_observed"] = self.expected_product_exit
        self.result["cleanup"] = cleanup
        self.result["elapsed_seconds"] = round(time.monotonic() - self.started, 3)
        if errors or cleanup.get("sigterm_sent") or cleanup.get("sigkill_sent") or (
            self.process is not None and ((cleanup.get("daemon_exit") != 0 and not self.expected_product_exit)
                                         or not cleanup.get("log_thread_finished"))
        ) or (self.runtime is not None and not cleanup["runtime_removed"]):
            self.result["status"] = "fixture_or_cleanup_failure"
        self.save()

    def classify(self):
        existing = self.result.get("fault_cases", {}).get("fault-target", {})
        new = self.result.get("fault_cases", {}).get("fault-new-directory", {})
        cleanup = self.result.get("cleanup", {})
        source = self.result.get("source_wallet", {})
        address = source.get("address")
        def wallet_state_valid(state, name):
            if not isinstance(state, dict) or not isinstance(address, str) or not address:
                return False
            labels = state.get("labels", {})
            try:
                balance_ok = Decimal(str(state.get("balance"))) == 0
            except Exception:
                balance_ok = False
            return (state.get("address") == address and state.get("ismine") is True
                and state.get("wallet_name") == name and isinstance(labels, dict)
                and isinstance(labels.get(address), dict)
                and labels[address].get("purpose") == "receive" and balance_ok)
        def verification_valid(verification, name):
            return (isinstance(verification, dict)
                and wallet_state_valid(verification.get("initial"), name)
                and wallet_state_valid(verification.get("after_unload_reload"), name))
        def limits_valid(case):
            before, during = case.get("limits_before"), case.get("limits_during")
            if not (isinstance(before, list) and len(before) == 2
                    and isinstance(during, list) and len(during) == 2
                    and during == [SOFT_CAP, before[1]]
                    and (before[0] == resource.RLIM_INFINITY or before[0] > SOFT_CAP)
                    and (before[1] == resource.RLIM_INFINITY or before[1] >= SOFT_CAP)):
                return False
            if case.get("daemon_alive_after_copy"):
                return case.get("limits_restored") == before
            return (case.get("daemon_exit_after_copy") is not None
                    and bool(case.get("limit_restore_not_applicable")))
        backup = self.result.get("backup_before", {})
        backup_records_valid = (backup.get("exists") is True and backup.get("size", 0) > SOFT_CAP
            and bool(backup.get("sha256")) and existing.get("backup_after_copy") == backup
            and new.get("backup_after_copy") == backup
            and self.result.get("backup_after_all_cases") == backup)
        invalid = self.result.get("invalid_regular_backup_control", {})
        common = {
            "observation_complete": self.result.get("status") == "observation_complete",
            "source_wallet_valid": wallet_state_valid(source, "source"),
            "healthy_controls_completed": verification_valid(self.result.get("healthy_before"), "healthy-before")
                and verification_valid(self.result.get("healthy_after"), "healthy-after"),
            "preservation_controls": bool(self.result.get("preservation_after_all_cases"))
                and all(self.result.get("preservation_after_all_cases", {}).values()),
            "existing_copy_failed_via_rpc": (not existing.get("copy_reply", {}).get("success", True)
                                              and "error" in existing.get("copy_reply", {})),
            "raw_backup_records_preserved": backup_records_valid,
            "invalid_regular_backup_cleanup": (invalid.get("reply", {}).get("success") is False
                and "error" in invalid.get("reply", {}) and invalid.get("before", {}).get("exists") is True
                and invalid.get("before") == invalid.get("after")
                and invalid.get("target_directory_exists") is False
                and invalid.get("existing_wallet_unchanged") is True),
            "existing_limit_restored": limits_valid(existing),
            "new_copy_failed_observed": not new.get("copy_reply", {}).get("success", True),
            "new_limit_restored_or_child_exited": limits_valid(new),
            "owned_cleanup": cleanup.get("runtime_removed") and cleanup.get("daemon_exited")
                and cleanup.get("log_thread_finished") and not cleanup.get("errors")
                and not cleanup.get("sigterm_sent") and not cleanup.get("sigkill_sent"),
        }
        if self.args.expect == "baseline":
            expected = {
                "existing_partial_copy_and_retry_block": self.result.get("hypothesis_confirmed") is True,
                "retry_left_same_partial": existing.get("destination_after_retry") == existing.get("destination_after_copy"),
                # NEW-directory baseline outcome is observational: RPC error,
                # leftover partial, or actual process exit are all retained.
                "new_outcome_recorded": bool(new) and "daemon_alive_after_copy" in new,
            }
        else:
            def recovered(case, name):
                retry = case.get("retry_reply", {})
                return (retry.get("success") is True and retry.get("result", {}).get("name") == name
                    and verification_valid(retry.get("wallet_verification"), name))
            expected = {
                "existing_failed_output_removed": existing.get("destination_after_copy", {}).get("exists") is False,
                "existing_directory_and_sentinel_preserved": existing.get("directory_preserved")
                    and existing.get("sentinel_preserved"),
                "existing_same_name_retry_and_reload": recovered(existing, "fault-target"),
                "new_copy_failed_via_rpc": "error" in new.get("copy_reply", {}),
                "new_daemon_survived": new.get("daemon_alive_after_copy") is True,
                "new_failed_directory_removed": new.get("directory_after_copy") is False,
                "new_same_name_retry_and_reload": recovered(new, "fault-new-directory"),
                "normal_daemon_stop": cleanup.get("normal_rpc_stop_requested") and cleanup.get("daemon_exit") == 0,
            }
        checks = dict(common, **expected)
        self.result["classification"] = {"expect": self.args.expect, "checks": checks,
            "failed_checks": [name for name, ok in checks.items() if not ok],
            "passed": all(checks.values())}
        self.save()
        return self.result["classification"]["passed"]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--binary", required=True, type=Path)
    parser.add_argument("--records", required=True, type=Path)
    parser.add_argument("--functional-root", type=Path,
                        default=Path("accepted-source/test/functional"))
    parser.add_argument("--expected-sha256", default=BASE_SHA256)
    parser.add_argument("--expect", choices=("baseline", "candidate"), required=True)
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
    passed = observation.classify()
    print(json.dumps({"status": observation.result["status"],
                      "hypothesis_confirmed": observation.result["hypothesis_confirmed"],
                      "expect": args.expect, "qualification_passed": passed,
                      "result_file": str(args.records / "result.json")}))
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
