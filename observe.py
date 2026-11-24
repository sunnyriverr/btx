"""Test an automatic download across a normal restart of the packaged regtest node."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import socket
import struct
import subprocess
import tempfile
import time

from helpers import Helper, completion, digest, require


CAP = 64 << 20
MODEL_BYTES = 8_388_681
MODEL_SHA384 = "abac2e23268fc4cb7f34f1f1a5c30a4b39229f4aec2f5bcf51b3cf7c04290dc936f2f476bca1bc8116d8dd61e9a1ecd2"


def unused_port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def process_record(pid):
    proc = Path("/proc") / str(pid)
    fields = (proc / "stat").read_text().rsplit(")", 1)[1].split()
    return {"pid": pid, "ppid": int(fields[1]), "started": fields[19],
            "exe": str((proc / "exe").resolve(strict=True))}


def is_same_process(record):
    try:
        return process_record(record["pid"])["started"] == record["started"]
    except (FileNotFoundError, ProcessLookupError):
        return False


def preserves(before, after, fields=("bytes", "sha256")):
    return bool(before) and all(
        all(after.get(name, {}).get(key) == piece[key] for key in fields)
        for name, piece in before.items()
    )


class PackagedNode(Helper):
    def __init__(self, package, root, out, endpoint):
        super().__init__(package / "bin/btxd", root, out, "receiver", CAP, peer=endpoint)
        self.package = package
        self.datadir = root / "node"
        self.datadir.mkdir()
        home = root / "home"
        home.mkdir()
        self.port = unused_port()
        self.env = dict(os.environ, HOME=str(home), XDG_DATA_HOME=str(home / "data"),
                        XDG_RUNTIME_DIR=str(root))
        for key in ("LD_LIBRARY_PATH", "LD_PRELOAD", "BTX_MODELD", "BTX_MODELHELPER", "BTX_OPENSSL"):
            self.env.pop(key, None)
        self.launch_args = [
            str(self.binary), "-regtest", f"-datadir={self.datadir}", f"-rpcport={self.port}",
            "-rpcbind=127.0.0.1", "-listen=0", "-connect=0", "-dnsseed=0",
            "-discover=0", "-disablewallet=1", "-swapnet=0", f"-modeldir={self.store}",
            "-modelstorage=64MiB", "-modelseed=auto", "-modelfollowpeers=1",
            "-modellandiscovery=0", "-modelbind=off", "-modelhost=0",
            f"-modelpeer={endpoint}", "-printtoconsole=1",
        ]
        self.boots = []
        self.exits = []

    def ok(self, method, params=None):
        args = [str(self.package / "bin/btx-cli"), "-regtest", f"-datadir={self.datadir}",
                f"-rpcport={self.port}", "-rpcclienttimeout=4", method]
        args.extend(v if isinstance(v, str) else json.dumps(v) for v in (params or []))
        call = subprocess.run(args, env=self.env, capture_output=True, text=True, timeout=8)
        self.calls.append({"method": method, "exit": call.returncode,
                           "error": call.stderr.strip()[:300] if call.returncode else None})
        require(call.returncode == 0, f"{method}: {call.stderr.strip()[:500]}")
        if method == "stop":
            return call.stdout.strip()
        return json.loads(call.stdout)

    def start(self):
        require(self.proc is None, "node already started")
        self.starts += 1
        self.log = (self.out / f"receiver-{self.starts}.log").open("wb")
        self.proc = subprocess.Popen(self.launch_args, env=self.env, cwd=self.root,
                                     stdout=self.log, stderr=subprocess.STDOUT, start_new_session=True)
        deadline = time.monotonic() + 55
        last = None
        while time.monotonic() < deadline:
            require(self.proc.poll() is None, f"packaged node exited: {self.proc.returncode}")
            try:
                chain = self.ok("getblockchaininfo")
                info = self.info()
                if (info.get("helper_ready") is True and info.get("pq1_ready") is True
                        and info.get("helper_managed_by_btxd") is True
                        and info.get("helper_state") == "READY" and info.get("owner_helper_pid", 0) > 0):
                    break
            except (RuntimeError, OSError, subprocess.TimeoutExpired) as exc:
                last = str(exc)
            time.sleep(0.2)
        else:
            raise RuntimeError(f"node-owned helper did not become ready: {last}, {locals().get('info')}")
        node = process_record(self.proc.pid)
        child = process_record(info["owner_helper_pid"])
        require(chain["chain"] == "regtest" and chain["blocks"] == 0, "not empty regtest")
        require(node["exe"] == str(self.package / "libexec/btxd.real"), "node executable mismatch")
        require(child["exe"] == str(self.package / "libexec/btx-modeld.real"), "helper executable mismatch")
        require(child["ppid"] == node["pid"], "helper is not a child of the node")
        require(info["helper_restart_count"] == 0, "helper restarted unexpectedly during boot")
        self.boots.append({"node": node, "child": child,
                           "tree": info["native_participation"]["network"]})
        self.start_info.append(info)

    def stop(self):
        if self.proc is None:
            return
        require(self.proc.poll() is None, "node exited before normal stop")
        self.ok("stop")
        status = self.proc.wait(timeout=30)
        child = self.boots[-1]["child"] if len(self.boots) == self.starts else None
        require(status == 0, f"node stop exit {status}")
        require(child is not None and not is_same_process(child), "managed child survived normal stop")
        self.exits.append(status)
        self.proc = None
        self.log.close()
        self.log = None


class BudgetExceeded(BaseException):
    pass


def verify_result(r):
    for flag in ("complete", "initial_empty", "automatic_job", "active_partial_before_stop",
                 "retained_partial_after_stop", "restart_preserved_pieces", "peer_authenticated_same_chain",
                 "clean_cleanup", "runtime_removed"):
        require(r.get(flag) is True, f"missing result: {flag}")
    require(len(r["boots"]) == 2 and r["node_exits"] == [0, 0] and r["provider_exit"] == 0,
            "two clean managed boots and one provider exit required")
    require(all(c["method"] != "getmodel" for c in r["receiver_calls"]), "manual retrieval used")
    require(r["integrity"]["bytes"] == r["source_bytes"] == MODEL_BYTES
            and r["integrity"]["sha384"] == r["source_sha384"] == MODEL_SHA384, "model bytes differ")
    require(r["integrity"]["manifest"]["model_id"] == r["model_id"]
            and r["integrity"]["manifest"]["artifact_id"] == r["artifact_id"], "model or artifact ID differs")
    checkout = r["public_checkout"]
    require(checkout == {"model_id": r["model_id"], "artifact_id": r["artifact_id"],
                         "bytes": MODEL_BYTES, "sha384": MODEL_SHA384}, "public checkout not verified")
    require(r["health_polls"] == 3, "post-recovery health controls incomplete")
    before, retained, final = (r[key] for key in ("before_stop_pieces", "after_stop_pieces", "final_pieces"))
    require(0 < sum(piece["bytes"] for piece in before.values()) <= MODEL_BYTES // 2,
            "invalid partial boundary")
    require(sum(piece["bytes"] for piece in retained.values()) < MODEL_BYTES
            and preserves(before, retained) and preserves(retained, final), "verified pieces not retained")


def observe(package, out):
    root = Path(tempfile.mkdtemp(prefix="btxpr-"))
    root.chmod(0o700)
    r = {"complete": False, "stage": "fixture", "timeline": []}
    start = time.monotonic()
    provider = receiver = None

    def save():
        (out / "result.json").write_text(json.dumps(r, indent=2) + "\n")

    def step(name):
        r["stage"] = name
        r["timeline"].append({"stage": name, "elapsed_seconds": time.monotonic() - start})
        save()
        print(name, flush=True)

    def deadline(*_):
        raise BudgetExceeded("600-second case bound exceeded")

    signal.signal(signal.SIGALRM, deadline)
    signal.alarm(600)
    try:
        port = unused_port()
        endpoint = f"127.0.0.1:{port}"
        provider = Helper(package / "bin/btx-modeld", root / "provider", out, "provider",
                          CAP, hostport=port, expected_exe=package / "libexec/btx-modeld.real")
        provider.start()
        src = root / "model.safetensors"
        n = 8 << 20
        header = json.dumps({"t": {"dtype": "U8", "shape": [n], "data_offsets": [0, n]}},
                            separators=(",", ":")).encode()
        src.write_bytes(struct.pack("<Q", len(header)) + header
                        + hashlib.shake_256(b"configured-first").digest(n))
        require(src.stat().st_size == MODEL_BYTES, "fixture payload size changed")
        require(digest(src, "sha384") == MODEL_SHA384, "fixture payload digest changed")
        imported = provider.ok("importmodel", [str(src), {"pin": True}])
        model_id, uri = imported["model_id"], imported["uri"]
        manifest = provider.ok("getmodelmanifest", [uri])
        require(manifest["complete"] is True, "provider source incomplete")
        aid = manifest["artifact_id"]
        r.update(source_bytes=src.stat().st_size, source_sha384=digest(src, "sha384"),
                 model_id=model_id, artifact_id=aid, endpoint=endpoint,
                 sender_executable_sha256=digest(package / "libexec/btx-modeld.real"))
        receiver = PackagedNode(package, root / "receiver", out, endpoint)
        r["initial_empty"] = (not (receiver.store / "catalog.json").exists()
                              and not list(receiver.store.rglob("*.piece")))
        require(r["initial_empty"], "receiver not empty")
        step("managed boot before transfer")
        receiver.start()
        r["boots"] = receiver.boots

        def jobs_on_disk():
            path = receiver.store / "retrieve_jobs.json"
            return json.loads(path.read_text()).get("jobs", []) if path.exists() else []

        def sample():
            require(receiver.ok("getmodelpeers")["peers"] == [endpoint], "other configured contact")
            info = receiver.info()
            np = info["native_participation"]
            require(np["network"] == "regtest" and np["lan_enabled"] is False
                    and np["hint_count"] == 0, "chain/LAN/contact guard")
            require(int(info["automatic_spend_atoms"]) == 0, "automatic spending enabled")
            require(np.get("peer_observations") is not None, "peer observation missing")
            if any(p["endpoint"] == endpoint and len(p.get("transport_pin", "")) == 96
                   and model_id in p.get("advertised_models", []) for p in np["peer_observations"]):
                r["peer_authenticated_same_chain"] = True
            if any(j.get("model_id") == model_id and j.get("automatic") is True
                   for j in jobs_on_disk()):
                r["automatic_job"] = True
            r["acquired_models"] = np["acquired_models"]
            r["whole_file_stage_seen"] = (r.get("whole_file_stage_seen", False)
                                           or (receiver.store / "peer-hydrate-q").is_dir())
            return receiver.row(model_id)

        step("wait for verified partial automatic download")
        end = time.monotonic() + 120
        while time.monotonic() < end:
            row = sample()
            pieces = receiver.pieces(aid)
            active = [j for j in receiver.ok("getmodeljob").get("jobs", [])
                      if j.get("model_id") == model_id and j.get("status") == "running"]
            if r.get("automatic_job") and active and 0 < sum(p["bytes"] for p in pieces.values()) <= MODEL_BYTES // 2:
                r.update(active_partial_before_stop=True, before_stop_pieces=pieces, active_jobs=active)
                break
            require(not (row.get("bytes_verified") is True and row.get("incomplete") is False),
                    "fixture missed the active partial boundary")
            time.sleep(0.2)
        else:
            raise RuntimeError("fixture did not reach an active automatic partial download")
        step("normal node stop with partial work")
        receiver.stop()
        retained = receiver.pieces(aid)
        r["after_stop_pieces"] = retained
        r["saved_automatic_after_stop"] = any(
            j.get("model_id") == model_id and j.get("automatic") is True for j in jobs_on_disk()
        )
        r["retained_partial_after_stop"] = 0 < sum(p["bytes"] for p in retained.values()) < MODEL_BYTES
        require(r["retained_partial_after_stop"] and preserves(pieces, retained),
                "sampled partial state did not survive or completed before stop")
        require(provider.proc.poll() is None, "provider did not stay alive")

        step("managed restart using the same state")
        receiver.start()
        for kind in ("node", "child"):
            first, second = (b[kind] for b in receiver.boots)
            require((first["pid"], first["started"]) != (second["pid"], second["started"]),
                    f"{kind} did not restart")
        step("wait for autonomous completion")
        end = time.monotonic() + 180
        while time.monotonic() < end:
            row = sample()
            if row.get("bytes_verified") is True and row.get("incomplete") is False:
                break
            time.sleep(0.5)
        else:
            raise RuntimeError("no automatic completion within 180 seconds after managed restart")
        final = receiver.pieces(aid)
        r["final_pieces"] = final
        r["restart_preserved_pieces"] = preserves(retained, final)
        r["piece_file_identity_preserved"] = preserves(retained, final, ("bytes", "sha256", "inode", "mtime_ns"))
        r["integrity"] = completion(receiver, uri, r["source_sha384"])
        step("public exportmodelpath checkout")
        checkout = receiver.ok("exportmodelpath", [uri])
        checkout_path = Path(checkout["path"]).resolve(strict=True)
        require(checkout_path.is_relative_to(receiver.store.resolve()), "checkout outside disposable store")
        payload = checkout_path / "model.safetensors"
        require(checkout["model_id"] == model_id and checkout["artifact_id"] == aid and checkout["materialized"],
                "checkout identity or materialization mismatch")
        require(payload.stat().st_size == MODEL_BYTES and digest(payload, "sha384") == MODEL_SHA384,
                "public checkout bytes differ")
        r["public_checkout"] = {"model_id": checkout["model_id"], "artifact_id": checkout["artifact_id"],
                                "bytes": payload.stat().st_size, "sha384": digest(payload, "sha384")}
        r["health_polls"] = 0
        for _ in range(3):
            require(sample().get("incomplete") is False, "completed model became incomplete")
            r["health_polls"] += 1
            time.sleep(0.5)
        step("clean teardown")
        receiver.stop()
        r["complete"] = True
    except (Exception, BudgetExceeded) as exc:
        r["error"] = repr(exc)
    finally:
        signal.alarm(0)
        r["cleanup_errors"] = []
        for helper in (receiver, provider):
            if helper is None:
                continue
            proc = helper.proc
            helper.cleanup()
            if helper.cleanup_error or helper.forced:
                r["cleanup_errors"].append({"role": helper.label, "error": helper.cleanup_error,
                                            "forced": helper.forced})
            if helper is provider:
                r["provider_exit"] = proc.poll() if proc else None
        if receiver:
            r["receiver_calls"] = receiver.calls
            r["node_exits"] = receiver.exits
        r["clean_cleanup"] = not r["cleanup_errors"]
        if all(h is None or h.proc is None or h.proc.poll() is not None for h in (receiver, provider)):
            shutil.rmtree(root)
            r["runtime_removed"] = True
        r["seconds"] = time.monotonic() - start
        save()
    verify_result(r)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("package", type=Path)
    parser.add_argument("out", type=Path)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    observe(args.package.resolve(), args.out.resolve())
