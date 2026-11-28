"""Gate and supervise the exact daemon-only Ninja invocation."""
from collections import Counter
import ctypes
from ctypes import wintypes
import hashlib
import json
import os
from pathlib import Path
import re
import runpy
import shutil
import signal
import struct
import subprocess
import threading
import time
import traceback

CONTROL = Path(__file__).resolve().parent
PREFLIGHT = runpy.run_path(str(CONTROL / "daemon-plan.py"))
BUILD = PREFLIGHT["BUILD"]
RECORDS = PREFLIGHT["RECORDS"]
RESULT = RECORDS / "link-result.json"
CANDIDATE = PREFLIGHT["CANDIDATE"]
PLAN_HASH = "036b579a598faeba88b192b6bb647875e6a4cb5d7f25e51c7a46cfd05c17e278"
BUILD_SECONDS = 62 * 60


def save(result):
    RESULT.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")


def choose_jobs():
    class MemoryStatus(ctypes.Structure):
        _fields_ = [
            ("length", wintypes.DWORD), ("load", wintypes.DWORD),
            *[(name, ctypes.c_uint64) for name in (
                "physical", "available", "pagefile", "available_pagefile", "virtual",
                "available_virtual", "available_extended_virtual",
            )],
        ]

    memory = MemoryStatus()
    memory.length = ctypes.sizeof(memory)
    assert ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(memory))
    assert memory.available >= 5 * 2**30, "Insufficient memory to compile safely"
    cpus = os.cpu_count() or 1
    jobs = min(4, cpus, max(1, int(memory.available / (2.75 * 2**30))))
    return jobs, cpus, memory.available


def gate(plan):
    assert plan["complete"] and plan["actions"] == 741
    assert plan["product_objects_after_configure_and_dry_run"] == 0
    assert plan["verified_dependency_files"] == 6675
    raw = (RECORDS / "ninja-commands.txt").read_text(encoding="utf-8").splitlines()
    commands = [line.strip() for line in raw if line.strip()]
    digest = hashlib.sha256(("\n".join(sorted(commands)) + "\n").encode()).hexdigest()
    assert len(commands) == 741 and digest == PLAN_HASH, (len(commands), digest)
    dry = (RECORDS / "ninja-dry-run.txt").read_text(encoding="utf-8")
    scheduled = re.findall(r"^\[\d+/\d+\]\s+(.*)$", dry, re.M)
    assert Counter(c.strip() for c in scheduled) == Counter(commands)
    assert "bin\\btxd.exe" in commands[-1] or "bin/btxd.exe" in commands[-1]
    assert all("test_btx.dir" not in c.lower() and "btx-cli.dir" not in c.lower() for c in commands)
    assert plan["free_after_bytes"] >= 20 * 2**30, "Build and retention require at least 20 GiB free"
    return digest


def stop_ninja(process):
    try:
        process.send_signal(signal.CTRL_BREAK_EVENT)
        return process.wait(timeout=20)
    except (subprocess.TimeoutExpired, OSError):
        subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"],
                       check=False, capture_output=True, timeout=30)
        return process.wait(timeout=20)


def build(env, jobs):
    env = {**env, "NINJA_STATUS": "[%f/%t] "}
    command = ["ninja", "-C", str(BUILD), "-j", str(jobs), "-k", "1", "btxd"]
    started = time.monotonic()
    budget_expired = False
    with (RECORDS / "ninja-build.log").open("w", encoding="utf-8", newline="\n") as log:
        process = subprocess.Popen(command, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                   text=True, encoding="utf-8", errors="replace",
                                   creationflags=subprocess.CREATE_NEW_PROCESS_GROUP)

        def copy_progress():
            for line in process.stdout:
                log.write(line)
                log.flush()
                print(line.rstrip("\n"), flush=True)

        drain = threading.Thread(target=copy_progress, daemon=True)
        drain.start()
        try:
            code = process.wait(timeout=BUILD_SECONDS)
        except subprocess.TimeoutExpired:
            budget_expired = True
            code = stop_ninja(process)
        finally:
            drain.join(timeout=20)
            process.stdout.close()
    log_lines = (RECORDS / "ninja-build.log").read_text(encoding="utf-8").splitlines()
    completed = [re.match(r"^\[(\d+)/741\]", line) for line in log_lines]
    return {
        "exit": code, "budget_expired": budget_expired, "seconds": round(time.monotonic() - started, 2),
        "last_ninja_progress": max((int(m[1]) for m in completed if m), default=0),
        "first_failure": next((line for line in log_lines if line.startswith("FAILED:")), None),
    }


def verify_daemon(env):
    binary = BUILD / "bin" / "btxd.exe"
    with binary.open("rb") as stream:
        dos = stream.read(64)
        assert dos[:2] == b"MZ"
        stream.seek(struct.unpack_from("<I", dos, 60)[0])
        pe = stream.read(26)
    assert pe[:4] == b"PE\0\0" and struct.unpack_from("<H", pe, 4)[0] == 0x8664
    assert struct.unpack_from("<H", pe, 24)[0] == 0x20b
    build_info = BUILD / "src" / "bitcoin-build-info.h"
    assert CANDIDATE in build_info.read_text(encoding="utf-8")
    pinned_hash = PREFLIGHT["get_hash"](binary)
    export = RECORDS / "btxd.exe"
    shutil.copyfile(binary, export)
    assert PREFLIGHT["get_hash"](export) == pinned_hash
    verify = subprocess.run([str(binary), "-version"], cwd=binary.parent, env=env, capture_output=True, timeout=30)
    (RECORDS / "btxd-version.txt").write_bytes(verify.stdout + verify.stderr)
    return {
        "sha256": pinned_hash, "size_bytes": binary.stat().st_size, "machine": "x64 PE32+",
        "build_info_sha256": PREFLIGHT["get_hash"](build_info),
        "candidate_commit_in_generated_build_info": True,
        "version_exit": verify.returncode, "version_contains_0_34_17": b"0.34.17" in verify.stdout,
        "version_first_line": next(iter(verify.stdout.decode("utf-8", errors="replace").splitlines()), ""),
    }


def run(result):
    plan = {}
    PREFLIGHT["run"](plan)
    (RECORDS / "preflight-result.json").write_text(json.dumps(plan, indent=2) + "\n", encoding="utf-8")
    digest = gate(plan)
    _, env = PREFLIGHT["compiler_profile"]()
    jobs, cpus, available = choose_jobs()
    result.update(plan_admitted=True, plan_actions=741, command_closure_sha256=digest, jobs=jobs, cpus=cpus,
                  available_ram_bytes=available, build_cap_seconds=BUILD_SECONDS)
    save(result)
    print(f"Verified the exact 741-action plan. Building only btxd with {jobs} jobs.", flush=True)
    result["ninja"] = build(env, jobs)
    result["linked"] = (result["ninja"]["exit"] == 0 and not result["ninja"]["budget_expired"] and
                        (BUILD / "bin" / "btxd.exe").is_file())
    save(result)
    if result["linked"]:
        result["binary"] = verify_daemon(env)
    result["complete"] = bool(result.get("binary", {}).get("version_exit") == 0 and
                              result.get("binary", {}).get("version_contains_0_34_17"))


if __name__ == "__main__":
    RECORDS.mkdir(exist_ok=True)
    receipt = {"base": PREFLIGHT["BASE"], "candidate": CANDIDATE, "linked": False, "complete": False,
               "plan_admitted": False}
    try:
        run(receipt)
    except Exception:
        (RECORDS / "link-exception.txt").write_text(traceback.format_exc(), encoding="utf-8")
        raise
    finally:
        save(receipt)
    if not receipt["complete"]:
        raise SystemExit(1)
