#!/usr/bin/env python3
"""UNEXECUTED W3 launcher; file verification plus bounded disposable process group.

Do not invoke until native execution is authorized. Never uploads raw logs,
wallets, bundles or data directories. Writes a small public receipt only.
"""
import argparse
import configparser
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import time

PIN = "61f13b8870ed98c7b10db2e32c04fb647023f4ef"
EXPECTED = {
    "btxd": "92fc16404aa6021ab27757157771bbcaf0c595afba6d83e3daa63fc6ebbf644c",
    "btx-cli": "ae63c2874a71ab213886d50f12fc6d4cfee7a3af40609feb5c377c4b2005dfcf",
}


def file_hash(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for part in iter(lambda: stream.read(2**20), b""):
            h.update(part)
    return h.hexdigest()


def tree_bytes(root):
    return sum(p.lstat().st_size for p in root.rglob("*") if p.is_file() and not p.is_symlink())


def group_exists(pgid):
    try:
        os.killpg(pgid, 0)
        return True
    except ProcessLookupError:
        return False


def stop_owned_group(process):
    # Every descendant inherits the new group; no ambient process discovery/killing.
    assert process.pid != os.getpgrp()
    for sig, duration in [(signal.SIGTERM, 10), (signal.SIGKILL, 5)]:
        if not group_exists(process.pid):
            break
        os.killpg(process.pid, sig)
        deadline = time.monotonic() + duration
        while group_exists(process.pid) and time.monotonic() < deadline:
            process.poll()  # Reap the parent before testing group disappearance.
            time.sleep(0.1)
    process.wait(timeout=5)
    return not group_exists(process.pid)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--checkpoint-root", type=Path, required=True)
    parser.add_argument("--runtime-root", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    args = parser.parse_args()
    root = args.checkpoint_root.resolve(strict=True)
    runtime = args.runtime_root.resolve()
    receipt = args.receipt.resolve()
    assert not runtime.exists() and runtime.parent.is_dir()
    assert runtime.parent.resolve() == root and runtime.name == "w3-private-runtime"
    assert root in receipt.parents and runtime not in receipt.parents and not receipt.exists()
    assert shutil.disk_usage(root).free >= int(1.25 * 2**30) + 512 * 2**20
    binary_hashes = {}
    for name, wanted in EXPECTED.items():
        binary = root / "build/bin" / name
        assert file_hash(binary) == wanted and os.access(binary, os.X_OK)
        binary_hashes[name] = wanted
    config_path = root / "build/test/config.ini"
    config = configparser.ConfigParser()
    config.read(config_path)
    assert Path(config["environment"]["SRCDIR"]).resolve() == root / "source"
    assert Path(config["environment"]["BUILDDIR"]).resolve() == root / "build"
    assert config.getboolean("components", "ENABLE_WALLET")
    assert config.getboolean("components", "USE_SQLITE")
    # Verify prior independently restored source identity, not just an arbitrary same-named folder.
    producer = json.loads((root / "saved/producer.json").read_text())
    assert producer["source_identity"] == PIN
    for name, digest in producer["source_files_sha256"].items():
        if not name.startswith(".github/"):
            assert file_hash(root / "source" / name) == digest, name
    fixture = Path(__file__).with_name("wallet_seed_pruned_recovery.py").resolve()
    os.umask(0o077)
    runtime.mkdir(mode=0o700)
    events = runtime / "events.json"
    env = dict(os.environ, PYTHONPATH=str(root / "source/test/functional"),
               BTXD=str(root / "build/bin/btxd"), BITCOIND=str(root / "build/bin/btxd"),
               BTXCLI=str(root / "build/bin/btx-cli"), BITCOINCLI=str(root / "build/bin/btx-cli"))
    # Avoid inherited operators' endpoint/config overrides; datadirs/config are framework-owned.
    env.pop("BITCOIN_TESTS_LOGGING", None)
    cmd = [sys.executable, str(fixture), "--descriptors", "--configfile=" + str(config_path),
           "--tmpdir=" + str(runtime / "data"), "--cachedir=" + str(runtime / "cache"),
           "--w3-records=" + str(events), "--nocleanup"]
    process = None
    started = time.monotonic()
    stop_reason = None
    max_private = 0
    min_free = shutil.disk_usage(root).free
    record = {"source": PIN, "binary_sha256": binary_hashes, "fixture_sha256": file_hash(fixture),
              "budget_seconds": 1800, "scratch_limit_bytes": 512 * 2**20,
              "result": "SETUP_OR_EXECUTION_FAILED", "tests_executed": False}
    try:
        with (runtime / "private.log").open("w") as log:
            process = subprocess.Popen(cmd, env=env, cwd=root, stdout=log, stderr=subprocess.STDOUT,
                                       start_new_session=True)
            record["tests_executed"] = True
            while process.poll() is None:
                current_bytes = tree_bytes(runtime)
                current_free = shutil.disk_usage(root).free
                max_private = max(max_private, current_bytes)
                min_free = min(min_free, current_free)
                if time.monotonic() - started >= 1800:
                    stop_reason = "DEADLINE"
                elif current_bytes > 512 * 2**20:
                    stop_reason = "SCRATCH_LIMIT"
                elif current_free < int(1.25 * 2**30):
                    stop_reason = "DISK_RESERVE"
                if stop_reason:
                    break
                time.sleep(2)
        # Parent may have exited while a failed setup left a node behind.
        clean = stop_owned_group(process)
        result = json.loads(events.read_text()) if events.is_file() else {"status": "NO_RESULT"}
        required = ["HEALTHY_CONTROL", "PRUNE_ADMITTED", "INCOMPLETE_RECOVERY", "DURABLE_DATABASE", "CONFIRMED_CONTINUED_USE"]
        stages = [event["stage"] for event in result.get("events", [])]
        passed = (not stop_reason and clean and process.returncode == 0 and result["status"] == "PASS"
                  and stages == required)
        record.update(result="PASS" if passed else "FAIL", exit=process.returncode,
                      stop_reason=stop_reason, cleanup_group_absent=clean, observations=result)
    finally:
        # Retain private diagnostic log locally, but remove all disposable keys/chain state.
        if process is not None and group_exists(process.pid):
            record["cleanup_group_absent"] = stop_owned_group(process)
        if record.get("cleanup_group_absent", process is None):
            for name in ["data", "cache"]:
                p = runtime / name
                if p.exists():
                    shutil.rmtree(p)
        else:
            record["result"] = "FAIL"
        record["maximum_sampled_private_bytes"] = max_private
        record["minimum_sampled_free_bytes"] = min_free
        record["elapsed_seconds"] = round(time.monotonic() - started, 2)
        record["private_data_removed"] = not any((runtime / n).exists() for n in ["data", "cache"])
        if not record["private_data_removed"]:
            record["result"] = "FAIL"
        receipt.parent.mkdir(parents=True, exist_ok=True)
        receipt.write_text(json.dumps(record, indent=2) + "\n")
    return 0 if record["result"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
