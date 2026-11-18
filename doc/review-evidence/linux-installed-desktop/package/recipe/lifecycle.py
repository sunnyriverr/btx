"""Source-reviewed draft only: ordinary installed helper/guard startup and restart.

Derived from Session 2's retained runtime/case.py. No model download, inference,
peer traffic, wallet, funding, signing or adverse-input scenario is exercised.
The parent must admit/install the exact retained archive before calling this.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import socket
import subprocess
import time
import traceback

SOURCE = "074dac167c26c1e091198f691ed5727817dba88a"
PROFILE = "Ubuntu 24.04 x86_64; disposable wallet-disabled offline regtest"
OVERRIDES = ("LD_LIBRARY_PATH", "LD_PRELOAD", "BTX_MODELD", "BTX_MODELHELPER",
             "PYTHONPATH", "PYTHONHOME", "BTX_GUARDD")


def sha(path):
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def proc_record(pid):
    process = Path("/proc") / str(pid)
    fields = (process / "stat").read_text().rsplit(")", 1)[1].split()
    return {"pid": pid, "ppid": int(fields[1]), "start_ticks": fields[19],
            "exe": os.readlink(process / "exe"),
            "argv": (process / "cmdline").read_bytes().decode().rstrip("\0").split("\0")}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prefix", required=True, type=Path)
    parser.add_argument("--runtime", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    assert all(path.is_absolute() for path in (args.prefix, args.runtime, args.out))
    prefix, runtime, out = args.prefix.resolve(), args.runtime.resolve(), args.out.resolve()
    assert prefix.is_dir() and prefix != Path("/") and not runtime.exists()
    assert not out.is_relative_to(prefix) and not runtime.is_relative_to(prefix)
    assert not out.is_relative_to(runtime) and not prefix.is_relative_to(runtime)
    out.mkdir(parents=True, exist_ok=True)
    state = {"overall": "FAIL", "compiled_source": SOURCE, "profile": PROFILE,
             "fixture_origin": "Session 2 retained ordinary lifecycle recipe",
             "boots": [], "checks": [], "cleanup_signals": [],
             "manual_helper_launch": False, "model_transfers": False,
             "inference": False, "release_qualification": False}
    node = None
    node_log = None
    owned = False
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    for key in OVERRIDES:
        env.pop(key, None)
    env.update(HOME=str(runtime / "home"), XDG_CONFIG_HOME=str(runtime / "config"),
               XDG_DATA_HOME=str(runtime / "data"), XDG_CACHE_HOME=str(runtime / "cache"))

    def save():
        (out / "result.json").write_text(json.dumps(state, indent=2) + "\n")

    def check(name, condition):
        state["checks"].append({"name": name, "pass": bool(condition)})
        save()
        if not condition:
            raise AssertionError(name)

    def files():
        return {str(path.relative_to(prefix)): sha(path)
                for path in prefix.rglob("*") if path.is_file()}

    def processes():
        rows = []
        for path in Path("/proc").iterdir():
            if not path.name.isdigit():
                continue
            try:
                row = proc_record(int(path.name))
                if Path(row["exe"]).is_relative_to(prefix):
                    rows.append(row)
            except (OSError, ValueError, ProcessLookupError):
                pass
        return rows

    def rpc(method, *params):
        reply = subprocess.run(
            [str(prefix / "bin/btx-cli"), "-regtest", "-datadir=" + str(runtime / "node"),
             "-rpcport=" + str(port), "-rpcclienttimeout=5", method, *params],
            env=env, cwd=runtime, text=True, capture_output=True, timeout=8)
        if reply.returncode:
            raise RuntimeError((method, reply.returncode, reply.stderr[:1000]))
        if method == "stop":
            return reply.stdout.strip()
        return json.loads(reply.stdout)

    def wait_for(fn, seconds, description):
        until = time.monotonic() + seconds
        latest = None
        while time.monotonic() < until:
            if node is not None and node.poll() is not None:
                raise RuntimeError(("node exited", node.returncode, description))
            try:
                value = fn()
                if value:
                    return value
            except (RuntimeError, OSError, subprocess.TimeoutExpired, ValueError) as error:
                latest = repr(error)
            time.sleep(0.25)
        raise TimeoutError((description, latest))

    def live_info():
        value = rpc("getmodelnetworkinfo")
        if (value.get("helper_ready") is True and value.get("helper_state") == "READY"
                and value.get("helper_managed_by_btxd") is True
                and value.get("owner_helper_pid", 0) > 0):
            return value
        return None

    def guard_status():
        value = rpc("modelsecurity", '{"op":"status"}')
        rows = [row for row in processes()
                if Path(row["exe"]) == prefix / "libexec/btx-guardd"]
        good = (value.get("ok") is True and value.get("automatic_spend_atoms") == "0"
                and value.get("policy_installed") is False and value.get("journal_valid") is True
                and len(rows) == 1 and rows[0]["ppid"] == node.pid)
        return {"ready": good, "reply": value, "processes": rows}

    def ready_guard():
        value = guard_status()
        return value if value["ready"] else None

    def boot(number):
        nonlocal node, node_log
        check("no installed processes before boot " + str(number), not processes())
        node_log = (out / ("boot" + str(number) + "-console.log")).open("wb")
        node = subprocess.Popen([str(prefix / "bin/btxd"), *node_args],
                                env=env, cwd=runtime, stdout=node_log,
                                stderr=subprocess.STDOUT, start_new_session=True)
        wait_for(lambda: rpc("getblockchaininfo"), 45, "RPC ready")
        info = wait_for(live_info, 60, "owned helper READY")
        parent = proc_record(node.pid)
        helper = proc_record(info["owner_helper_pid"])
        check("installed daemon executable", Path(parent["exe"]) == prefix / "libexec/btxd.real")
        check("installed direct-child helper", helper["ppid"] == node.pid
              and Path(helper["exe"]) == prefix / "libexec/btx-modeld.real")
        check("offline helper arguments", all(
            value in helper["argv"] for value in ("-modelseed=off", "-modelfollowpeers=0",
                                                   "-modellandiscovery=0", "-modelstorage=16MiB")))
        check("no helper network listener arguments", not any(
            value.split("=", 1)[0] in ("-modelbind", "-modelpeer", "-modelseednode")
            for value in helper["argv"]))
        check("isolated storage and seed policy", info.get("quota_bytes") == 16 * 1024**2
              and info.get("seed_mode") == "off" and info.get("follow_configured_peers") is False)
        identities = rpc("listmodelidentities")["identities"]
        check("default local identity exists", bool(identities))
        guard = wait_for(ready_guard, 10, "ordinary guard status")
        current_boot = {"number": number, "node": parent, "helper": helper,
                        "guard": guard, "identities": identities, "health": []}
        state["boots"].append(current_boot)
        save()
        for sample in range(10):
            now = rpc("getmodelnetworkinfo")
            chain = rpc("getblockchaininfo")
            peers = rpc("getconnectioncount")
            current = proc_record(helper["pid"])
            guard_now = guard_status()
            healthy = (
                now.get("helper_ready") is True and now.get("helper_state") == "READY"
                and now.get("helper_managed_by_btxd") is True
                and now.get("owner_helper_pid") == helper["pid"]
                and now.get("helper_restart_count") == 0
                and current["ppid"] == node.pid and current["start_ticks"] == helper["start_ticks"]
                and Path(current["exe"]) == prefix / "libexec/btx-modeld.real"
                and chain["chain"] == "regtest" and chain["blocks"] == 0 and peers == 0
                and now.get("peers_connected") == 0 and now.get("automatic_spend_atoms") == 0
                and now.get("advertised_host") is False and now.get("public_host_reachable") is False
                and guard_now["ready"]
                and guard_now["processes"][0]["start_ticks"] == guard["processes"][0]["start_ticks"]
                and guard_now["reply"].get("guard_boot") == guard["reply"].get("guard_boot"))
            current_boot["health"].append({"sample": sample, "pass": healthy,
                                           "guard": guard_now, "helper_pid": helper["pid"]})
            check("ordinary helper/guard health boot%s sample%s" % (number, sample), healthy)
            time.sleep(0.5)
        return current_boot

    def stop(number):
        nonlocal node_log
        rpc("stop")
        node.wait(timeout=30)
        node_log.close()
        node_log = None
        check("normal daemon exit boot " + str(number), node.returncode == 0)
        deadline = time.monotonic() + 5
        while processes() and time.monotonic() < deadline:
            time.sleep(0.1)
        check("no installed process after stop " + str(number), not processes())
        debug = runtime / "node/regtest/debug.log"
        if debug.exists():
            shutil.copyfile(debug, out / ("through-boot%s-debug.log" % number))

    def interrupted(signum, _frame):
        raise InterruptedError("controller signal " + str(signum))

    signal.signal(signal.SIGTERM, interrupted)
    signal.signal(signal.SIGINT, interrupted)
    try:
        runtime.mkdir(mode=0o700)
        owned = True
        for name in ("home", "config", "data", "cache", "node"):
            (runtime / name).mkdir(mode=0o700)
        state["package_before"] = files()
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            port = sock.getsockname()[1]
        node_args = ["-regtest", "-datadir=" + str(runtime / "node"), "-server=1",
                     "-disablewallet=1", "-listen=0", "-networkactive=0", "-connect=0",
                     "-dnsseed=0", "-discover=0", "-natpmp=0",
                     "-rpcbind=127.0.0.1", "-rpcallowip=127.0.0.1", "-rpcport=" + str(port),
                     "-modelbind=off", "-modelhost=0", "-modelseed=off",
                     "-modelfollowpeers=0", "-modellandiscovery=0", "-modelstorage=16MiB",
                     "-dbcache=32", "-printtoconsole=1"]
        state["node_arguments"] = node_args
        first = boot(1)
        stop(1)
        second = boot(2)
        check("new daemon process identity on restart",
              (first["node"]["pid"], first["node"]["start_ticks"])
              != (second["node"]["pid"], second["node"]["start_ticks"]))
        check("new helper process identity on restart",
              (first["helper"]["pid"], first["helper"]["start_ticks"])
              != (second["helper"]["pid"], second["helper"]["start_ticks"]))
        check("default identity survives ordinary restart", first["identities"] == second["identities"])
        check("fresh guard boot",
              first["guard"]["reply"].get("guard_boot") is not None
              and second["guard"]["reply"].get("guard_boot") is not None
              and first["guard"]["reply"]["guard_boot"] != second["guard"]["reply"]["guard_boot"])
        stop(2)
        state["package_after"] = files()
        check("installed file bytes unchanged", state["package_before"] == state["package_after"])
        state["overall"] = "PASS"
    except Exception as error:
        state["error"] = repr(error)
        state["traceback"] = traceback.format_exc()
    finally:
        # Normal shutdown first even on an intermediate assertion failure.
        if node is not None and node.poll() is None:
            try:
                rpc("stop")
                node.wait(timeout=30)
            except Exception as error:
                state["cleanup_stop_error"] = repr(error)
        # Only executable + start-ticks matched records from this unique prefix.
        # Signals are containment only and can never count as normal acceptance.
        rows = processes()
        for row in rows:
            try:
                current = proc_record(row["pid"])
                if (current["exe"], current["start_ticks"]) == (row["exe"], row["start_ticks"]):
                    os.kill(row["pid"], signal.SIGTERM)
                    state["cleanup_signals"].append({"pid": row["pid"], "signal": "SIGTERM"})
            except OSError:
                pass
        deadline = time.monotonic() + 10
        while processes() and time.monotonic() < deadline:
            time.sleep(0.1)
        state["cleanup_remaining"] = processes()
        if node_log is not None:
            node_log.close()
        if owned and not state["cleanup_remaining"]:
            shutil.rmtree(runtime)
        state["runtime_removed"] = owned and not runtime.exists()
        if state["cleanup_signals"] or state["cleanup_remaining"] or not state["runtime_removed"]:
            state["overall"] = "FAIL"
        save()
    return 0 if state["overall"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
