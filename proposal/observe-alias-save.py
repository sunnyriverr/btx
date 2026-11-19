"""Observe alias save and restart behavior in a disposable local Linux helper."""
import argparse
import errno
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import struct
import sys
import tempfile

# A staged copy can place the existing modules beside this file.
support = (Path(__file__).resolve().parent.parent /
           "modelnet-contact-save-confirmation/repair/retry/recipe")
if support.is_dir():
    sys.path.insert(0, str(support))
from observe import ContactHelper

OLD, NEW, STABLE = "fixture-old-alias", "fixture-new-alias", "fixture-control-alias"
OPERATIONS = (
    ("add", "setmodelalias", NEW, "alias"),
    ("remove", "removemodelalias", OLD, "removed"),
)


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def hosted_model(helper, root, label):
    model_dir = root / label
    model_dir.mkdir()
    # #644's tiny SafeTensors layout with a header label to keep the IDs distinct.
    header = json.dumps({"__metadata__": {"fixture": label}},
                        separators=(",", ":")).encode()
    (model_dir / "toy.safetensors").write_bytes(struct.pack("<Q", len(header)) + header)
    result = helper.rpc("hostmodel", [str(model_dir)])
    require(re.fullmatch("[0-9a-f]{96}", result["model_id"]), "invalid hosted model ID")
    require(isinstance(result["uri"], str) and result["uri"], "missing hosted model URI")
    return result["model_id"], result["uri"]


def accepted(reply, field, alias, model_id):
    value = reply["result"] or {}
    return (reply["error"] is None and value.get(field) == alias
            and value.get("model_id") == model_id
            and value.get("signed_metadata") is True
            and value.get("automatic_spend_atoms") == 0)


def save_error(reply):
    error = reply["error"]
    message = error.get("message") if isinstance(error, dict) else error
    return isinstance(message, str) and "search-index write" in message


def disk_snapshot(index, model_ids):
    data = index.read_bytes()
    relevant = {row["model_id"]: row for row in json.loads(data)["records"]
                if row["model_id"] in model_ids}
    require(set(relevant) == model_ids, "target or control missing from saved index")
    return {"sha256": digest(data), "models": relevant}


def live_aliases(helper, model_id):
    rows = helper.rpc("getmodelaliases", [model_id])["aliases"]
    names = [row["alias"] for row in rows]
    require(len(names) == len(set(names)), "duplicate alias in live index")
    require(all(row["model_id"] == model_id and row["provenance"] == "publisher_metadata"
                for row in rows), "live alias missing signed model provenance")
    return sorted(names)


def exercise(helper, root, result):
    index = helper.store / "search-index.json"
    obstacle = index.with_suffix(".json.tmp")
    sentinel = obstacle / "fixture-sentinel"
    phases = result["phases"]
    helper.start()
    target, uri = hosted_model(helper, root, "alias-target")
    control, control_uri = hosted_model(helper, root, "alias-control")
    require(target != control, "the model fixtures must have different IDs")
    result["model_ids"] = {"target": target, "control": control}
    for model_id, model_uri, alias in [(target, uri, OLD), (control, control_uri, STABLE)]:
        require(accepted(helper.call("setmodelalias", [model_uri, alias]), "alias", alias, model_id),
                "healthy seed alias did not succeed")

    def capture(name, reply=None, live=True):
        row = {"disk": disk_snapshot(index, {target, control})}
        if live:
            row["live"] = {"target": live_aliases(helper, target),
                           "control": live_aliases(helper, control)}
        if reply is not None:
            row["rpc"] = reply
        phases[name] = row
        return row

    def expect_aliases(row, names):
        require(row["live"] == {"target": sorted(names), "control": [STABLE]},
                "unexpected alias state in the live index")
        require(sorted(row["disk"]["models"][target]["aliases"]) == sorted(names),
                "unexpected alias state on disk")

    initial = capture("healthy")
    expect_aliases(initial, [OLD])
    original_digest = initial["disk"]["sha256"]
    original_control = initial["disk"]["models"][control]
    signer = initial["disk"]["models"][target]["signer_id"]
    require(bool(initial["disk"]["models"][target]["signature"]), "missing saved target signature")
    require(bool(original_control["signature"]), "missing saved control signature")

    obstacle.mkdir()
    sentinel.write_text("owned alias fixture\n")
    try:
        fd = os.open(obstacle, os.O_WRONLY)
    except OSError as error:
        require(error.errno == errno.EISDIR, "temporary write path did not fail as a directory")
        result["write_obstacle_errno"] = error.errno
    else:
        os.close(fd)
        raise ValueError("temporary write path remained writable")

    def still_blocked(row):
        require(sentinel.read_text() == "owned alias fixture\n", "write obstacle changed")
        require(row["disk"]["sha256"] == original_digest, "a blocked operation changed the saved index")
        if "live" in row:
            require(row["live"]["control"] == [STABLE], "unrelated live alias changed")

    for label, method, alias, field in OPERATIONS:
        row = capture(f"failed_{label}", helper.call(method, [uri, alias]))
        still_blocked(row)
        require(accepted(row["rpc"], field, alias, target) or save_error(row["rpc"]),
                f"{method} did not reach a signed alias update or report the write error")
    helper.stop()
    still_blocked(capture("after_stop", live=False))

    helper.start()
    helper.rpc("getmodelfeedstatus", [])  # The alias getter does not trigger the lazy load.
    reopened = capture("first_reopen")
    still_blocked(reopened)
    expect_aliases(reopened, [OLD])
    sentinel.unlink()
    obstacle.rmdir()

    previous_sequence = reopened["disk"]["models"][target]["metadata_sequence"]
    for (label, method, alias, field), expected in zip(OPERATIONS, ([OLD, NEW], [NEW])):
        row = capture(f"retry_{label}", helper.call(method, [uri, alias]))
        require(accepted(row["rpc"], field, alias, target), "retry did not return signed success")
        expect_aliases(row, expected)
        record = row["disk"]["models"][target]
        require(record["signer_id"] == signer and bool(record["signature"])
                and record["metadata_sequence"] > previous_sequence,
                "retry did not persist a newer record from the original signer")
        previous_sequence = record["metadata_sequence"]
        require(row["disk"]["models"][control] == original_control, "retry changed the control record")
    helper.stop()

    helper.start()
    helper.rpc("getmodelfeedstatus", [])
    final = capture("final_reopen")
    expect_aliases(final, [NEW])
    require(final["disk"]["models"] == phases["retry_remove"]["disk"]["models"],
            "signed records changed across the final reopen")
    helper.stop()
    require(helper.starts == 3, "unexpected number of helper starts")

    result["failed_write_acknowledgements"] = [
        label for label, _, alias, field in OPERATIONS
        if accepted(phases[f"failed_{label}"]["rpc"], field, alias, target)]
    result["rejected_writes_changed_live_state"] = []
    live_before = initial["live"]["target"]
    for label, *_ in OPERATIONS:
        phase = phases[f"failed_{label}"]
        live_after = phase["live"]["target"]
        if save_error(phase["rpc"]) and live_after != live_before:
            result["rejected_writes_changed_live_state"].append(label)
        live_before = live_after
    result["helper_starts"] = helper.starts


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--helper", required=True, type=Path)
    parser.add_argument("--expected-helper-sha256", required=True)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    require(platform.system() == "Linux" and platform.machine() == "x86_64",
            "the recorded scope is Linux x86-64")
    binary = args.helper.resolve(strict=True)
    helper_sha = digest(binary.read_bytes())
    require(helper_sha == args.expected_helper_sha256, "helper digest mismatch")
    args.out.mkdir(parents=True, exist_ok=False)
    result = {"helper_sha256": helper_sha, "complete": False, "phases": {}}
    root = Path(tempfile.mkdtemp(prefix="s2-alias-save-", dir="/tmp"))
    helper = ContactHelper(binary, root, args.out, "alias-helper")
    try:
        try:
            exercise(helper, root, result)
        finally:
            helper.cleanup()
        require(not root.exists() and not helper.cleanup_signals, "fixture cleanup was not clean")
        result["complete"] = True
        found = result["failed_write_acknowledgements"] or result["rejected_writes_changed_live_state"]
        result["verdict"] = "ALIAS_WRITE_CONTRACT_FAILED" if found else "ALIAS_WRITE_CONTRACT_PASSED"
        return 2 if found else 0
    except Exception as exc:
        result["verdict"] = "INCOMPLETE"
        result["error"] = repr(exc)
        return 1
    finally:
        result["runtime_removed"] = not root.exists()
        result["forced_cleanup_signals"] = helper.cleanup_signals
        (args.out / "result.json").write_text(json.dumps(result, indent=2) + "\n")


if __name__ == "__main__":
    sys.exit(main())
