"""Exercise getmodelrelease through real helper RPC with an identical cap of two."""
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import signal
import socket
import struct
import subprocess
import sys
import tempfile
import time


@contextmanager
def helper(binary, parent, label, log):
    with tempfile.TemporaryDirectory(prefix=label, dir=parent) as name:
        tmp = Path(name)
        home = tmp / "home"
        home.mkdir()
        store = tmp / "store"
        store.mkdir()
        endpoint = tmp / "rpc.sock"
        args = [str(binary), f"-modeldir={store}", f"-modelrpcsocket={endpoint}",
                "-modelstorage=8MiB", "-modellandiscovery=0", "-modelfollowpeers=0",
                "-modelnatpmp=0", "-modelhost=0", "-modelseed=off", "-pwcchain=regtest"]
        env = dict(os.environ, HOME=str(home), XDG_DATA_HOME=str(home / "data"),
                   XDG_RUNTIME_DIR=str(tmp))
        with log.open("wb") as stream:
            with subprocess.Popen(args, env=env, stdout=stream, stderr=subprocess.STDOUT) as proc:
                request_id = 0

                def call(method, params=(), *, allow_error=False):
                    nonlocal request_id
                    assert proc.poll() is None
                    request_id += 1
                    request = dict(jsonrpc="1.0", id=request_id, method=method, params=params)
                    with socket.socket(socket.AF_UNIX) as conn:
                        conn.settimeout(20)
                        conn.connect(str(endpoint))
                        conn.sendall(json.dumps(request).encode() + b"\n")
                        conn.shutdown(socket.SHUT_WR)
                        with conn.makefile("rb") as reply:
                            raw = reply.read(1024 * 1024 + 1)
                    assert 0 < len(raw) <= 1024 * 1024
                    result = json.loads(raw)
                    assert result["id"] == request_id
                    if allow_error:
                        return result
                    assert result["error"] is None, (method, result["error"])
                    return result["result"]

                try:
                    deadline = time.monotonic() + 25
                    while not endpoint.exists():
                        assert time.monotonic() < deadline and proc.poll() is None, label
                        time.sleep(0.05)
                    assert isinstance(call("getmodelnetworkinfo"), dict)
                    yield call, tmp
                    assert proc.poll() is None
                finally:
                    if proc.poll() is None:
                        proc.send_signal(signal.SIGTERM)
                        try:
                            proc.wait(20)
                        except subprocess.TimeoutExpired:
                            proc.kill()
                            proc.wait(10)
                            raise
                    assert proc.returncode == 0 and not endpoint.exists(), (label, proc.returncode)


def campaign(call, tmp, model, publish):
    path = tmp / f"model-{model}.safetensors"
    header = json.dumps({"__metadata__": {"format": "pt"},
                         "w": {"dtype": "F32", "shape": [1], "data_offsets": [0, 4]}}).encode()
    path.write_bytes(struct.pack("<Q", len(header)) + header + struct.pack("<f", model))
    hosted = call("hostmodel", [str(path), {"publish": publish}])
    options = dict(uri=hosted["uri"], secret32_hex="de" * 32, refund_height=50,
                   target_atoms=100000000, publish_search_record=publish,
                   display_name=f"Disposable model {model}")
    result = call("createmodelrelease", [options])
    assert result["automatic_spend_atoms"] == 0
    assert result["publish_state"] == ("published" if publish else "local_campaign_only"), result
    return result


def lookup(call, key):
    result = call("getmodelrelease", [key], allow_error=True)
    if result["error"] is not None:
        assert "unknown release" in json.dumps(result["error"]).lower(), result
        return None
    payload = result["result"]
    assert payload["automatic_spend_atoms"] == 0 and len(payload["campaigns"]) == 1
    return payload["campaigns"][0]["release_id"]


def ingest(call, record):
    result = call("importmodelindex", [{"records": [record]}])
    assert result["imported"] == 1 and result["rejected"] == 0 and result["reverified"], result


def main(mode, binary, scratch, evidence):
    fixture = scratch / "signed-fixture.json"
    if mode == "before":
        with helper(binary, scratch, "publisher", evidence / "publisher.log") as (call, tmp):
            remote = [campaign(call, tmp, model, True) for model in (1, 2)]
            records = call("exportmodelindex", [{"limit": 100}])["records"]
            records = [next(row for row in records if row.get("release_id") == c["release_id"])
                       for c in remote]
        fixture.write_text(json.dumps(records))
    records = json.loads(fixture.read_text())
    first, second = records
    assert first["model_id"] != second["model_id"]
    with helper(binary, scratch, mode, evidence / f"{mode}-helper.log") as (call, tmp):
        local = campaign(call, tmp, 1, False)
        local_id, model_id = local["release_id"], local["model_id"]
        assert model_id == first["model_id"] and local_id != first["release_id"]
        assert lookup(call, model_id) == local_id
        ingest(call, first)
        assert lookup(call, model_id) == first["release_id"]
        assert lookup(call, local_id) == local_id
        assert len(call("getmodelrelease")["campaigns"]) == 2
        ingest(call, second)
        rows = call("getmodelrelease")
        assert rows["automatic_spend_atoms"] == 0
        assert {c["release_id"] for c in rows["campaigns"]} == {local_id, second["release_id"]}
        assert lookup(call, first["release_id"]) is None
        assert lookup(call, local_id) == local_id
        assert lookup(call, second["model_id"]) == second["release_id"]
        observed = lookup(call, model_id)
        assert isinstance(call("getmodelnetworkinfo"), dict)
    assert observed in (None, local_id)
    result = dict(variant=mode, model_lookup="NOT_FOUND" if observed is None else "retained_local",
                  verified_imports=2, cap=2, protected_release_by_id=True, evicted_remote=True,
                  other_model_lookup=True, automatic_spend_atoms=0, helper_healthy=True,
                  clean_shutdown=True, fixture_sha256=hashlib.sha256(fixture.read_bytes()).hexdigest(),
                  binary_sha256=hashlib.sha256(binary.read_bytes()).hexdigest())
    (evidence / f"{mode}-result.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result), flush=True)
    return 0 if observed == local_id else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1], *(Path(arg) for arg in sys.argv[2:])))
