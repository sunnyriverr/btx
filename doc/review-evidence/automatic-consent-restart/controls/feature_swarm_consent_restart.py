#!/usr/bin/env python3
# Copyright (c) 2026 The BTX developers
# Distributed under the MIT software license, see COPYING.
"""Default-owned helper: active automatic acquisition, withdrawal, restart, recovery.

Two fresh wallet-disabled regtest nodes on one host, with a configured local
model contact and strict PQ1. No model execution or monetary parameter changes.
This is not physical peer separation, LAN multicast or release qualification.
Stage beside feature_swarm_lan_discover.py in an exact-source functional tree.
"""

import hashlib
import json
import os
from pathlib import Path
import signal
import socket
import struct
import time

from feature_swarm_lan_discover import SwarmLanDiscoverTest
from test_framework.test_framework import BitcoinTestFramework, TestStatus
from test_framework.util import assert_equal

TARGET = "666673a3153225ba264c7870e0e82e354df86765"
PIECE_SIZE = 4 << 20
QUOTA = 1 << 30
ACTIVE = ("queued", "running")


class SwarmConsentRestartTest(SwarmLanDiscoverTest):
    def set_test_params(self):
        self.num_nodes = 2
        self.setup_clean_chain = True
        self.rpc_timeout = 15
        self.receipt = {"target": TARGET, "result": "NOT_COMPLETED", "snapshots": [],
                        "scope": "two same-host native default-owned helpers; configured model peer"}
        self.model_id = None
        self.artifact_id = None
        self.deadline = None

    def add_options(self, parser):
        parser.add_argument("--result-json", required=True, help="sanitized evidence output path")

    def setup_nodes(self):
        self.deadline = time.monotonic() + 400
        signal.signal(signal.SIGALRM, self._expired)
        signal.alarm(400)
        self.modeldirs = [Path(self.options.tmpdir) / f"models-{i}" for i in range(2)]
        # Same native setup as the maintained LAN case. A configured source
        # keeps the manual positive control intentional and survives restart.
        held = []
        try:
            for _ in range(2):
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.bind(("0.0.0.0", 0))
                held.append(sock)
            ports = [sock.getsockname()[1] for sock in held]
            self.source_endpoint = f"127.0.0.1:{ports[0]}"
            self.extra_args = []
            for i, modeldir in enumerate(self.modeldirs):
                modeldir.mkdir(parents=True)
                args = [f"-modeldir={modeldir}", f"-modelbind=0.0.0.0:{ports[i]}",
                        "-modellandiscovery=1", "-disablewallet=1"]
                args += ["-modeluploadlimit=1MiB"] if i == 0 else [f"-modelpeer={self.source_endpoint}"]
                self.extra_args.append(args)
        finally:
            for sock in held:
                sock.close()
        BitcoinTestFramework.setup_nodes(self)
        self.socket_paths = []
        for node in self.nodes:
            requested = node.datadir_path / self.chain / "modelnet" / "modeld.sock"
            encoded = os.fsencode(requested)
            if len(encoded) >= 108:
                # Match maintained profile test / UnixRpcListenPath. Never
                # supply -modelrpcsocket: btxd must own modeld.
                runtime = os.environ.get("XDG_RUNTIME_DIR")
                assert runtime, "long managed socket path requires XDG_RUNTIME_DIR"
                digest = hashlib.sha256(encoded).digest()[:8].hex()
                requested = Path(runtime) / "btx-modeld" / f"{digest}.sock"
            self.socket_paths.append(requested)

    @staticmethod
    def _expired(signum, frame):
        raise AssertionError("fixture exceeded 400 seconds")

    def shutdown(self):
        signal.alarm(0)
        # This framework deliberately leaves processes running on failure.
        # These two nodes belong solely to this fixture: stop them explicitly,
        # preserving their datadirs/logs for the parent's diagnosis.
        if self.success == TestStatus.FAILED:
            try:
                self.stop_nodes()
            except Exception as error:
                self.receipt["cleanup_error"] = str(error)
        self._save()
        return super().shutdown()

    def _save(self):
        path = Path(self.options.result_json)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.receipt, indent=2, default=str) + "\n")

    def helper(self, index, method, params=None):
        request = {"jsonrpc": "1.0", "id": "consent-native", "method": method, "params": params or []}
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
            client.settimeout(10)
            client.connect(str(self.socket_paths[index]))
            client.sendall((json.dumps(request) + "\n").encode())
            client.shutdown(socket.SHUT_WR)
            with client.makefile("rb") as stream:
                raw = stream.readline(1024 * 1024)
        reply = json.loads(raw)
        assert not reply.get("error"), (method, reply.get("error"))
        return reply["result"]

    def wait(self, check, timeout, label):
        end = min(self.deadline, time.monotonic() + timeout)
        while time.monotonic() < end:
            value = check()
            if value:
                return value
            time.sleep(0.25)
        raise AssertionError(f"timeout: {label}")

    def jobs(self, model_id=None):
        jobs = self.helper(1, "getmodeljob")["jobs"]
        return [job for job in jobs if job.get("model_id") == (model_id or self.model_id)]

    def row(self):
        return next((row for row in self.nodes[1].listmodels().get("models", [])
                     if row.get("model_id") == self.model_id), {})

    def pieces(self):
        root = self.modeldirs[1] / "store" / "artifacts" / self.artifact_id / "0"
        return {path.name: path.stat().st_size for path in sorted(root.glob("*.piece"))}

    def observation(self):
        peers = self.native(self.nodes[1]).get("peer_observations", [])
        return next((peer for peer in peers if peer.get("endpoint") == self.source_endpoint
                     and self.model_id in peer.get("advertised_models", [])
                     and len(peer.get("transport_pin", "")) == 96
                     and peer.get("compute_authorized") is False), {})

    def health(self, index):
        info = self.nodes[index].getmodelnetworkinfo()
        assert info.get("helper_ready") is True, info
        assert info.get("pq1_ready") is True, info
        assert_equal(info["automatic_spend_atoms"], 0)
        assert_equal(self.nodes[index].getblockcount(), 0)
        assert_equal(self.nodes[index].getpeerinfo(), [])
        assert self.guard_ready(index), "owned guard not ready"
        return info

    def policy(self, allowed):
        info = self.health(1)
        pol = info.get("propagation", {})
        return (pol.get("storage_quota_bytes") == QUOTA
                and pol.get("follow_configured_peers") is allowed
                and pol.get("preserve_rare") is False
                and pol.get("seed") == ("auto" if allowed else "off"))

    def set_policy(self, allowed):
        result = self.helper(1, "setmodelprofile", ["custom", {
            "storage_bytes": QUOTA, "follow_peers": allowed,
            "preserve_rare": False, "seed": "auto" if allowed else "off"}])
        assert result.get("applied") is True, result
        assert_equal(result["runtime_apply"], "QUEUED")
        self.wait(lambda: self.policy(allowed), 20, "live policy application")

    def snapshot(self, stage):
        # RPCs below contain public model state only: never read cookie/key/TLS
        # files or dump process environment / private helper directories.
        info = self.health(1)
        source = self.health(0)
        snap = {"stage": stage, "elapsed_s": round(400 - (self.deadline - time.monotonic()), 3),
                "policy": info.get("propagation"), "helper_ready": info.get("helper_ready"),
                "pq1_ready": info.get("pq1_ready"), "automatic_spend_atoms": info.get("automatic_spend_atoms"),
                "jobs": self.jobs(), "model": self.row(), "observation": self.observation(),
                "pieces": self.pieces(), "source_health": {
                    key: source.get(key) for key in ("helper_ready", "pq1_ready", "automatic_spend_atoms")}}
        self.receipt["snapshots"].append(snap)
        self._save()
        return snap

    def quiet(self, stage, baseline, seconds=16):
        start = time.monotonic()
        initial = self.observation().get("observed_at_ms", 0)
        observed = set()
        def check():
            assert self.policy(False), "disabled live policy changed"
            self.health(0)
            assert not self.verified(self.nodes[1], self.model_id), "journey model completed under disabled policy"
            assert self.row().get("incomplete") is True, "incomplete catalog entry lost"
            assert_equal(self.pieces(), baseline)
            assert not any(job.get("status") in ACTIVE for job in self.jobs()), "new active journey job under disabled policy"
            peer = self.observation()
            when = peer.get("observed_at_ms", 0)
            if when > initial:
                observed.add(when)
            return time.monotonic() - start >= seconds and len(observed) >= 2
        self.wait(check, 45, "quiet incomplete bytes across two fresh discovery observations")
        snap = self.snapshot(stage)
        snap["distinct_new_discovery_observations"] = sorted(observed)
        self._save()

    def write_model(self, tag, size):
        # Same SafeTensors shape/import path as retrieve-regressions; streaming
        # output bounds fixture RAM. Payload is never executed.
        path = Path(self.options.tmpdir) / f"{tag}.safetensors"
        header = json.dumps({"t": {"dtype": "U8", "shape": [size], "data_offsets": [0, size]}},
                            separators=(",", ":")).encode()
        digest = hashlib.sha384()
        with path.open("wb") as stream:
            first = struct.pack("<Q", len(header)) + header
            stream.write(first)
            digest.update(first)
            for offset in range(0, size, 1 << 20):
                data = hashlib.shake_256(f"{tag}:{offset}".encode()).digest(min(1 << 20, size - offset))
                stream.write(data)
                digest.update(data)
        return path, digest.hexdigest()

    def assert_digest(self, uri, expected):
        manifest = self.helper(1, "getmodelmanifest", [uri])
        assert manifest.get("complete") is True, manifest
        entry, = manifest["files"]
        root = self.modeldirs[1] / "store" / "artifacts" / manifest["artifact_id"] / "0"
        digest = hashlib.sha384()
        total = 0
        for index in range((int(entry["size"]) + PIECE_SIZE - 1) // PIECE_SIZE):
            data = (root / f"{index}.piece").read_bytes()
            digest.update(data)
            total += len(data)
        assert_equal(total, int(entry["size"]))
        assert_equal(digest.hexdigest(), entry["sha384"])
        assert_equal(digest.hexdigest(), expected)
        return {"bytes": total, "sha384": expected, "manifest_sha384": entry["sha384"]}

    def run_test(self):
        try:
            self.journey()
            self.receipt["result"] = "PASS"
        except BaseException as error:
            self.receipt["result"] = "FAIL_OR_PREREQUISITE"
            self.receipt["error"] = f"{type(error).__name__}: {error}"
            if self.artifact_id and time.monotonic() < self.deadline - 10:
                try:
                    self.snapshot("failure")
                except Exception as diagnostic:
                    self.receipt["diagnostic_error"] = str(diagnostic)
            raise
        finally:
            self._save()

    def journey(self):
        for index, node in enumerate(self.nodes):
            self.wait(lambda node=node: node.getmodelnetworkinfo().get("helper_ready") is True, 60, "owned helper ready")
            self.wait(lambda index=index: self.guard_ready(index), 30, "owned guard ready")
            info = self.health(index)
            assert_equal(info["quota_bytes"], QUOTA)
        assert_equal(self.nodes[1].listmodels().get("models", []), [])
        assert_equal(self.helper(1, "getmodeljob")["jobs"], [])
        # No follower import/copy/watch/getmodel before recovery. Automatic
        # origin is additionally checked in the enqueue-time durable record.
        src, expected = self.write_model("journey", 68 << 20)
        hosted = self.nodes[0].hostmodel(str(src))
        self.model_id = hosted["model_id"]
        uri = hosted["uri"]
        manifest = self.helper(0, "getmodelmanifest", [uri])
        self.artifact_id = manifest["artifact_id"]
        self.receipt["journey"] = {"model_id": self.model_id, "artifact_id": self.artifact_id,
                                   "source_bytes": src.stat().st_size, "source_sha384": expected}
        self.wait(lambda: self.observation(), 60, "authenticated same-chain source model observation")
        def active():
            assert not self.verified(self.nodes[1], self.model_id), "completed before revocation precondition"
            return next((job for job in self.jobs() if job.get("status") == "running"
                         and 0 < job.get("bytes_committed", 0) < src.stat().st_size
                         and self.row().get("incomplete") is True), None)
        job = self.wait(active, 65, "positive incomplete automatic piece progress")
        durable = json.loads((self.modeldirs[1] / "retrieve_jobs.json").read_text())
        marker = next((item for item in durable.get("jobs", []) if item.get("job_id") == job["job_id"]), {})
        assert marker.get("automatic") is True, marker
        self.receipt["automatic_enqueue_record"] = marker
        self.snapshot("active_before_withdrawal")
        self.set_policy(False)
        self.snapshot("disabled_live_before_worker_settlement")
        def stopped():
            matching = self.jobs()
            old = next((item for item in matching if item["job_id"] == job["job_id"]), {})
            if old.get("status") not in ("failed", "cancelled"):
                return False
            text = json.dumps(old).lower()
            assert any(token in text for token in ("cancelled", "canceled", "stopped", "disabled by local policy")), old
            return not any(item.get("status") in ACTIVE for item in matching)
        self.wait(stopped, 30, "policy-related terminal automatic job")
        baseline = self.pieces()
        assert baseline and sum(baseline.values()) < src.stat().st_size, baseline
        self.quiet("disabled_settled", baseline)
        stored = self.helper(1, "getmodelprofile")
        assert stored.get("follow_peers") is False and stored.get("seed") == "off", stored
        self.receipt["saved_disabled_profile"] = stored
        self.restart_node(1)
        self.wait(lambda: self.nodes[1].getmodelnetworkinfo().get("helper_ready") is True, 60, "restarted helper ready")
        self.wait(lambda: self.guard_ready(1), 30, "restarted owned guard ready")
        assert self.policy(False), "saved disabled policy did not survive restart"
        assert_equal(self.helper(1, "getmodelprofile"), stored)
        # Fresh native observations are empty at startup. Quiet requires new
        # authenticated advertisements, not the old ID or startup counters.
        self.quiet("disabled_after_restart", baseline)
        control_src, control_digest = self.write_model("manual-control", 3 << 20)
        control = self.nodes[0].hostmodel(str(control_src))
        assert control["model_id"] != self.model_id
        assert not self.verified(self.nodes[1], control["model_id"])
        requested = self.helper(1, "getmodel", [control["uri"], "FREE_ONLY"])
        assert requested.get("job_id"), requested
        def manual_done():
            assert self.policy(False)
            assert_equal(self.pieces(), baseline)
            assert not self.verified(self.nodes[1], self.model_id)
            return self.verified(self.nodes[1], control["model_id"])
        self.wait(manual_done, 35, "valid manual control with automatic policy off")
        self.receipt["manual_control"] = {"model_id": control["model_id"], "request": requested,
            "jobs": self.jobs(control["model_id"]), "digest": self.assert_digest(control["uri"], control_digest)}
        self.quiet("disabled_after_manual_control", baseline, seconds=11)
        self.set_policy(True)
        self.snapshot("consent_restored")
        # A loaded/new job can fail before fresh discovery and retry after
        # 30 s. Neither successful completion nor recovery requires the old ID.
        self.wait(lambda: self.policy(True) and self.verified(self.nodes[1], self.model_id),
                  155, "automatic recovery and completion after restored consent")
        self.receipt["journey"]["verified_digest"] = self.assert_digest(uri, expected)
        self.snapshot("automatic_recovery_complete")
        self.health(0)
        self.health(1)
        self.log.info("PASS: active automatic pieces, applied withdrawal, settled refusal across restart, "
                      "manual free control and digest-verified automatic recovery; same host only")


if __name__ == "__main__":
    SwarmConsentRestartTest(__file__).main()
