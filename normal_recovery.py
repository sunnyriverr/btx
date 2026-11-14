"""Prepared only: real MinIO, normal catalog, missing-piece recovery journey."""
import hashlib
import json
from pathlib import Path
from feature_modelnet_minio import ModelNetMinioLayoutsTest, write_safetensors

class NormalRecovery(ModelNetMinioLayoutsTest):
    def _start_container(self):
        endpoint = super()._start_container()
        assert endpoint, self.not_run  # Never silently fall back to FakeS3.
        return endpoint

    def _run_matrix(self, fake):
        assert not fake and self.container and self.endpoint
        node = self.nodes[0]
        self._zero_spend(node.setcloudstorage(self._cloud_cfg("PIECE_OBJECTS", False)), "configure")
        source = Path(self.options.tmpdir) / "normal-recovery" / "model.safetensors"
        digest = write_safetensors(source, "normal-cloud-recovery\n")
        original = source.read_bytes()
        imported = self._zero_spend(node.importmodel(str(source)), "import")
        assert imported.get("cloud_uploaded") is True
        uri, artifact = imported["uri"], imported["artifact_id"]
        assert hashlib.sha384(self._reconstruct_object(self._bucket_keys(), artifact)).hexdigest() == digest
        root = Path(self.modeldir) / "store" / "artifacts" / artifact
        def stored():
            paths = sorted(root.rglob("*.piece"), key=lambda p: (int(p.parent.name), int(p.stem)))
            return b"".join(p.read_bytes() for p in paths)
        assert stored() == original
        healthy = self._zero_spend(node.getmodel(uri), "healthy getmodel")
        assert healthy.get("status") == "local"
        self._stop_helper()
        catalog_path = Path(self.modeldir) / "catalog.json"
        prior_catalog = catalog_path.read_bytes()
        row = next(e for e in json.loads(prior_catalog)["models"] if e["artifact_id"] == artifact)
        assert not row.get("incomplete", False)
        pieces = list(root.rglob("*.piece")); assert pieces
        for piece in pieces:
            piece.unlink()
        source.unlink()
        assert catalog_path.read_bytes() == prior_catalog  # No fixture flag write.
        self._start_helper(); self._wait_helper_ready()
        outcome = {"phase": "observed", "cloud_sha384": digest, "catalog_unchanged_at_fault": True}
        try:
            outcome["getmodel"] = self._zero_spend(node.getmodel(uri), "ordinary recovery")
        except Exception as e:
            outcome["getmodel_error"] = str(e)
        outcome["pieces_restored"] = stored() == original
        try:
            exported = self._zero_spend(node.exportmodelpath(uri), "materialize")
            checkout = Path(exported["path"]) / source.name
            outcome["materialized_bytes_match"] = checkout.read_bytes() == original
        except Exception as e:
            outcome["materialize_error"] = str(e)
        Path(self.options.tmpdir, "normal-recovery-result.json").write_text(json.dumps(outcome, indent=2))
        # Honest classification: a local label alone never passes recovery.
        assert outcome["pieces_restored"], outcome
        assert outcome.get("materialized_bytes_match"), outcome
        self._restart_helper()
        assert stored() == original
        assert self._zero_spend(node.getmodel(uri), "second restart").get("status") == "local"
        assert not source.exists()
        assert not Path(self.modeldir, "fakes3-objects.bin").exists()
        outcome["phase"] = "PASS_BYTES_AND_RESTART"
        Path(self.options.tmpdir, "normal-recovery-result.json").write_text(json.dumps(outcome, indent=2))
        print("NORMAL_CLOUD_RECOVERY_PASS", flush=True)

if __name__ == "__main__":
    NormalRecovery(__file__).main()
