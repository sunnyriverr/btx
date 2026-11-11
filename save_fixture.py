"""Matched observations for the failed-save boundary of the real importlabels RPC."""
import argparse
import json
import signal
import sqlite3
import sys
import traceback
from pathlib import Path

from daemon_fixture import BASE_SHA256, Observation, sha256, work_deadline


def record(address, label):
    return json.dumps({"type": "addr", "ref": address, "label": label}).encode()


class Labels(Observation):
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

    def save_case(self, mode):
        assert mode in ("ABORT", "ROLLBACK")
        name = "save-probe-" + mode.lower()
        self.rpc.createwallet(name, False, False, "", False, True, False, False)
        wallet = self.rpc_for_wallet(name)
        address = wallet.getnewaddress("old-save-label", "p2mr")
        assert self.label(wallet, address) == "old-save-label"
        source = self.runtime / "save.jsonl"
        source.write_bytes(record(address, "new-save-label") + b"\n")
        original = sha256(source)
        self.rpc.unloadwallet(name, False)
        db = self.runtime / "wallets" / name / "wallet.dat"
        assert db.is_file()
        key = b"\x04name" + bytes([len(address)]) + address.encode()
        old = b"\x0eold-save-label"
        purpose_key = b"\x07purpose" + bytes([len(address)]) + address.encode()
        with sqlite3.connect(str(db)) as conn:
            assert conn.execute("SELECT value FROM main WHERE key=?", (key,)).fetchone() == (old,)
            # Seed a distinct prior purpose so rollback has an observable second write.
            conn.execute("UPDATE main SET value=? WHERE key=?", (b"\x04send", purpose_key))
            assert conn.execute("SELECT value FROM main WHERE key=?", (purpose_key,)).fetchone() == (b"\x04send",)
            conn.execute(f"""CREATE TRIGGER reject_probe_label BEFORE INSERT ON main
                         WHEN NEW.key = X'{key.hex()}'
                         BEGIN SELECT RAISE({mode}, 'BTX_LABEL_PROBE_SAVE_{mode}'); END""")
        self.rpc.loadwallet(name, False)
        wallet = self.rpc_for_wallet(name)
        assert self.label(wallet, address) == "old-save-label"
        reply = self.attempt("save_fault_" + mode, wallet.importlabels, str(source))
        live = self.label(wallet, address)
        wallet = self.reopen(name)
        reopened = self.label(wallet, address)
        self.rpc.unloadwallet(name, False)
        with sqlite3.connect(str(db)) as conn:
            stored = conn.execute("SELECT value FROM main WHERE key=?", (key,)).fetchone()
            stored_purpose = conn.execute("SELECT value FROM main WHERE key=?", (purpose_key,)).fetchone()
            conn.execute("DROP TRIGGER reject_probe_label")
        self.rpc.loadwallet(name, False)
        retry = self.attempt("save_retry_" + mode, self.rpc_for_wallet(name).importlabels, str(source))
        wallet = self.reopen(name)
        after = self.label(wallet, address)
        self.rpc.unloadwallet(name, False)
        assert retry["success"] and retry["result"]["imported"] == 1 and after == "new-save-label"
        assert sha256(source) == original
        with sqlite3.connect(str(db)) as conn:
            assert conn.execute("SELECT value FROM main WHERE key=?", (purpose_key,)).fetchone() == (b"\x07receive",)
        self.result.setdefault("save_probes", {})[mode] = {
            "fault": "SQLite trigger rejects only INSERT/REPLACE of the existing address name key",
            "live_label": live, "reopened_label": reopened, "stored_old_value": stored == (old,),
            "healthy_retry_reopened_label": after, "source_unchanged": True,
            "stored_purpose": stored_purpose[0].hex(),
            "oracle_pass": not reply["success"] and reply["error"]["code"] == -4
                           and live == reopened == "old-save-label" and stored == (old,)
                           and stored_purpose == (b"\x04send",),
            "false_success": reply["success"] and reply["result"]["imported"] == 1
                             and reopened == "old-save-label" and stored == (old,),
        }
        self.save()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--binary", type=Path, required=True)
    parser.add_argument("--records", type=Path, required=True)
    parser.add_argument("--functional-root", type=Path, default=Path("accepted-source/test/functional"))
    parser.add_argument("--expected-sha256", default=BASE_SHA256)
    args = parser.parse_args()
    assert sys.platform == "linux"
    args.records = args.records.resolve()
    args.functional_root = args.functional_root.resolve(strict=True)
    sys.path.insert(0, str(args.functional_root))
    from test_framework.authproxy import AuthServiceProxy, JSONRPCException

    obs = Labels(args, AuthServiceProxy, JSONRPCException)
    obs.result["scope"] = "Linux synthetic wallet importlabels, SQLite ABORT and automatic ROLLBACK"
    obs.result["fixture_sha256"] = sha256(Path(__file__))
    obs.result["launcher_sha256"] = sha256(Path(__file__).with_name("daemon_fixture.py"))
    signal.signal(signal.SIGALRM, work_deadline)
    signal.setitimer(signal.ITIMER_REAL, 165)
    try:
        obs.start()
        for mode in ("ABORT", "ROLLBACK"):
            obs.save_case(mode)
        obs.result["status"] = "observation_complete"
    except Exception:
        obs.result["error"] = traceback.format_exc()
        obs.result["status"] = "inconclusive"
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        obs.cleanup()
    log = (args.records / "daemon.log").read_text(errors="replace")
    obs.result["fault_hits"] = {m: log.count("BTX_LABEL_PROBE_SAVE_" + m)
                                for m in ("ABORT", "ROLLBACK")}
    if not all(obs.result["fault_hits"].values()) or len(obs.result.get("save_probes", {})) != 2:
        obs.result["status"] = "inconclusive"
    obs.save()
    print(json.dumps(obs.result, indent=2, default=str))
    if obs.result["status"] != "observation_complete":
        return 2
    return 0 if all(p["oracle_pass"] for p in obs.result["save_probes"].values()) else 1


if __name__ == "__main__":
    sys.exit(main())
