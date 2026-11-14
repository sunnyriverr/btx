"""Strict real-MinIO acceptance using the upstream fixture."""
import hashlib
import os
from pathlib import Path

from feature_modelnet_minio import ModelNetMinioLayoutsTest


class StrictMinioRecovery(ModelNetMinioLayoutsTest):
    proved = False

    def _start_container(self):
        endpoint = super()._start_container()
        assert endpoint, self.not_run
        return endpoint

    def _run_matrix(self, fake):
        assert not fake and self.container and self.endpoint, "Real MinIO required"
        super()._run_matrix(fake)
        assert self.proved, "PIECE_OBJECTS restore did not execute"

    def _assert_piece_objects_hydrate_incomplete(self, mode, fake, uri, artifact_id, want_sha):
        source = Path(self.options.tmpdir) / "import-minio-piece_objects" / "model.safetensors"
        original = source.read_bytes()
        assert hashlib.sha384(original).hexdigest() == want_sha
        # Remove the original input as an alternate local recovery source.
        source.unlink()
        old_pid = self.modeld_proc.pid
        super()._assert_piece_objects_hydrate_incomplete(mode, fake, uri, artifact_id, want_sha)
        assert self.modeld_proc.pid != old_pid
        root = Path(self.modeldir) / "store" / "artifacts" / artifact_id
        paths = sorted(root.rglob("*.piece"), key=lambda p: (int(p.parent.name), int(p.stem)))
        assert paths and all(p.parent.name == "0" for p in paths), paths
        assert [int(p.stem) for p in paths] == list(range(len(paths)))
        recovered = b"".join(p.read_bytes() for p in paths)
        assert recovered == original, (len(original), len(recovered))
        assert not source.exists()
        assert not (Path(self.modeldir) / "fakes3-objects.bin").exists()
        print(f"MINIO_RECOVERY_BYTE_IDENTICAL bytes={len(recovered)} pieces={len(paths)} "
              f"sha384={hashlib.sha384(recovered).hexdigest()} helper={old_pid}->{self.modeld_proc.pid}", flush=True)
        self.proved = True


if __name__ == "__main__":
    StrictMinioRecovery(__file__).main()
