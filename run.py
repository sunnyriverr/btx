"""Compare the real helper with persistence alone and with reservation rollback."""
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import signal
import socket
import subprocess
import sys
import tempfile
import time


@contextmanager
def helper(binary, scratch, log):
    endpoint = scratch / "rpc.sock"
    store = scratch / "store"
    home = scratch / "home"
    store.mkdir(exist_ok=True)
    home.mkdir(exist_ok=True)
    assert not endpoint.exists()
    args = [str(binary), f"-modeldir={store}", f"-modelrpcsocket={endpoint}",
            "-modelstorage=8MiB", "-modellandiscovery=0", "-modelfollowpeers=0",
            "-modelnatpmp=0", "-modelhost=0", "-modelseed=off", "-pwcchain=regtest"]
    env = dict(os.environ, HOME=str(home), XDG_DATA_HOME=str(home / "data"),
               XDG_RUNTIME_DIR=str(scratch))
    with log.open("wb") as out, subprocess.Popen(args, env=env, stdout=out, stderr=subprocess.STDOUT) as proc:
        sequence = 0
        try:
            until = time.monotonic() + 25
            while not endpoint.exists():
                assert proc.poll() is None and time.monotonic() < until, "Helper startup failed"
                time.sleep(0.05)

            def call(method, params=(), reject=False):
                nonlocal sequence
                assert proc.poll() is None
                sequence += 1
                req = dict(jsonrpc="1.0", id=sequence, method=method, params=params)
                with socket.socket(socket.AF_UNIX) as conn:
                    conn.settimeout(20)
                    conn.connect(str(endpoint))
                    conn.sendall(json.dumps(req).encode() + b"\n")
                    conn.shutdown(socket.SHUT_WR)
                    with conn.makefile("rb") as stream:
                        raw = stream.read(1024 * 1024 + 1)
                assert 0 < len(raw) <= 1024 * 1024
                ans = json.loads(raw)
                assert ans["id"] == sequence
                if reject:
                    assert ans["error"] and ans["error"]["code"] == "REJECTED", ans
                    return ans["error"]
                assert ans["error"] is None, (method, ans["error"])
                return ans["result"]

            assert isinstance(call("getmodelnetworkinfo"), dict)
            yield call, proc.pid
        finally:
            if proc.poll() is None:
                proc.send_signal(signal.SIGTERM)
                try:
                    proc.wait(timeout=20)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.wait(timeout=10)
                    raise
            assert proc.returncode == 0 and not endpoint.exists(), (proc.returncode, log)


ID = {"mandate_id": "test-mandate"}
PUB = "b" * 96
NETWORK = "0" * 64
MANDATE = dict(**ID, mandate_version=1, owner_identity="a" * 96, network_id=NETWORK,
    publisher_id=PUB, allowed_kinds=["RELEASE", "MODEL"], allowed_actions=["FUND_WITH_MANDATE", "NOTIFY"],
    per_action_principal_limit_atoms="50", total_principal_limit_atoms="100", total_fee_limit_atoms="20",
    outstanding_exposure_limit_atoms="200", max_actions=16, max_concurrent_reservations=8,
    expires_at_ms="4000000000000", refund_key_policy="OWNER_CONTROLLED_ONLY", minimum_confirmations=1,
    assurance_mode_restrictions=[], revocation_counter="0")


def reserve(call, event, principal, fee, *, reject=False):
    terms = dict(terms_id="d" * 96, publisher_id=PUB, network_id=NETWORK, principal_atoms=str(principal),
                 fee_atoms=str(fee), object_kind="RELEASE", confirmations=1)
    args = dict(**ID, event_id=event, publisher_id=PUB, object_kind="RELEASE",
                action="FUND_WITH_MANDATE", signed_terms=terms)
    reply = call("reservesubscriptionmandate", [args], reject=reject)
    if reject:
        return reply
    assert reply["event_id"] == event
    assert int(reply["automatic_spend_atoms"]) == 0 and reply["broadcast"] is False
    assert reply["wallet_signed"] is False
    return reply["reservation_id"]


def snapshot(call):
    result = call("getsubscriptionmandate", [ID])
    activity = call("getsubscriptionactivity", [ID])
    assert int(result["automatic_spend_atoms"]) == int(activity["automatic_spend_atoms"]) == 0
    fields = ("used_principal_atoms", "used_fee_atoms", "outstanding_exposure_atoms",
              "action_count", "concurrent_reservations")
    actions = {x["event_id"]: x["reservation_id"] for x in activity["actions"]}
    assert len(actions) == len(activity["actions"])
    return dict(totals=[int(result[k]) for k in fields], reservations=actions)


def run(mode, binary, scratch, evidence):
    state = {"variant": mode, "binary_sha256": hashlib.sha256(binary.read_bytes()).hexdigest()}
    with tempfile.TemporaryDirectory(prefix=mode + "-", dir=scratch) as name:
        work = Path(name)
        with helper(binary, work, evidence / f"{mode}-first.log") as (call, first_pid):
            call("createsubscriptionmandate", [MANDATE])
            existing = reserve(call, "already-saved", 20, 2)
            initial = snapshot(call)
            assert initial == dict(totals=[20, 2, 22, 1, 1], reservations={"already-saved": existing})
            files = list((work / "store").rglob("subscription-mandates.json"))
            assert len(files) == 1, files
            durable = files[0]
            original = durable.read_bytes()
            blocker = durable.with_name(durable.name + ".tmp")
            blocker.mkdir()
            error = reserve(call, "retry-event", 50, 5, reject=True)
            assert "write" in error["message"] and "subscription-mandates.json" in error["message"], error
            assert blocker.is_dir() and durable.read_bytes() == original
            fault = snapshot(call)
            assert fault["reservations"]["already-saved"] == existing
            # A failed save when replaying an already-durable event must preserve that event.
            reserve(call, "already-saved", 20, 2, reject=True)
            assert snapshot(call) == fault and durable.read_bytes() == original
            blocker.rmdir()
            retry = reserve(call, "retry-event", 50, 5)
            expected = dict(totals=[70, 7, 77, 2, 2],
                            reservations={"already-saved": existing, "retry-event": retry})
            assert retry != existing and snapshot(call) == expected
            assert reserve(call, "retry-event", 50, 5) == retry and snapshot(call) == expected
            assert durable.read_bytes() != original and not blocker.exists()
        with helper(binary, work, evidence / f"{mode}-restart.log") as (call, next_pid):
            assert next_pid != first_pid and snapshot(call) == expected
            assert reserve(call, "already-saved", 20, 2) == existing
            assert reserve(call, "retry-event", 50, 5) == retry
            assert snapshot(call) == expected
            fresh = reserve(call, "fresh-control", 10, 1)
            assert snapshot(call) == dict(totals=[80, 8, 88, 3, 3],
                reservations={**expected["reservations"], "fresh-control": fresh})
        state.update(initial=initial, after_failed_save=fault, disk_unchanged_on_failure=True,
            replay_during_failure_preserved_prior_reservation=True, after_retry=expected,
            after_restart_and_replay=expected, fresh_after_restart=[80, 8, 88, 3, 3],
            automatic_spend_atoms=0, clean_shutdowns=2, rollback=fault == initial)
    assert state["rollback"] or state["after_failed_save"] == state["after_retry"], state
    (evidence / f"{mode}-result.json").write_text(json.dumps(state, indent=2) + "\n")
    print(json.dumps(state))
    return 0 if state["rollback"] else 42


if __name__ == "__main__":
    raise SystemExit(run(sys.argv[1], *(Path(p) for p in sys.argv[2:])))
