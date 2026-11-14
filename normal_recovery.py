"""Prepared only: real MinIO, normal catalog, missing-piece recovery journey."""
import hashlib
import json
from pathlib import Path
from feature_modelnet_minio import ModelNetMinioLayoutsTest, write_safetensors

class NormalRecovery(ModelNetMinioLayoutsTest):
    def set_test_params(self):
        super().set_test_params()

    def run_test(self):
        super().run_test()

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
        # Same disposable state: measure the supported remove/retrieve path.
        outcome["remove"] = self._zero_spend(node.removemodel(uri), "remove damaged local replica")
        assert outcome["remove"].get("removed") is True
        remote = self._reconstruct_object(self._bucket_keys(), artifact)
        assert remote == original
        outcome["remote_bytes_survive_remove"] = True
        outcome["retry_getmodel"] = self._zero_spend(node.getmodel(uri), "retrieve after remove")
        outcome["retry_pieces_match"] = stored() == original
        try:
            exported = self._zero_spend(node.exportmodelpath(uri), "materialize after retry")
            outcome["retry_materialized_match"] = (Path(exported["path"]) / source.name).read_bytes() == original
        except Exception as e:
            outcome["retry_materialize_error"] = str(e)
        self._restart_helper()
        outcome["restart_getmodel"] = self._zero_spend(node.getmodel(uri), "retrieve after second restart")
        outcome["restart_pieces_match"] = stored() == original
        try:
            exported = self._zero_spend(node.exportmodelpath(uri), "materialize after second restart")
            outcome["restart_materialized_match"] = (Path(exported["path"]) / source.name).read_bytes() == original
        except Exception as e:
            outcome["restart_materialize_error"] = str(e)
        assert self._reconstruct_object(self._bucket_keys(), artifact) == original
        assert not source.exists()
        assert not Path(self.modeldir, "fakes3-objects.bin").exists()
        recovered = all(outcome.get(k) is True for k in ["retry_pieces_match", "retry_materialized_match", "restart_pieces_match", "restart_materialized_match"])
        outcome["phase"] = "OPERATOR_RECOVERY_PASSED" if recovered else "OPERATOR_PATH_MEASURED_NO_RECOVERY"
        Path(self.options.tmpdir, "normal-recovery-result.json").write_text(json.dumps(outcome, indent=2))
        print("OPERATOR_RECOVERY_MEASUREMENT_COMPLETE", flush=True)

if __name__ == "__main__":
    NormalRecovery(__file__).main()
