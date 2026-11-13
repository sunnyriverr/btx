"""Create provenance for the exact admitted archive used by all runtime checks."""
import hashlib
import json
from pathlib import Path, PurePosixPath
import subprocess
import tarfile

source = subprocess.check_output(["git", "-C", "product", "rev-parse", "HEAD"], text=True).strip()
assert source == "88c9b49cb16360fc8fbf3f84003b8b54c29e6db5"
root = Path("candidate-input")
archive = root / "btx-linux-gui-candidate.tar.gz"
with archive.open("rb") as stream:
    checksum = hashlib.sha256()
    for block in iter(lambda: stream.read(1 << 20), b""):
        checksum.update(block)
rows = {}
with tarfile.open(archive) as tar:
    for member in tar:
        parts = PurePosixPath(member.name).parts
        assert parts and parts[0] == "btx-0.34.16" and ".." not in parts
        if member.isfile():
            stream = tar.extractfile(member)
            assert stream is not None
            content = hashlib.sha256()
            for block in iter(lambda: stream.read(1 << 20), b""):
                content.update(block)
            name = str(PurePosixPath(*parts[1:]))
            assert name not in rows
            rows[name] = {"sha256": content.hexdigest()}
        elif member.issym() or member.islnk():
            # The reused desktop observer hashes resolved file contents.
            name = str(PurePosixPath(*parts[1:]))
            target = tar.extractfile(member)
            assert target is not None and name not in rows
            rows[name] = {"sha256": hashlib.sha256(target.read()).hexdigest()}
for binary in ("btxd", "btx-qt", "btx-atlas", "btx-guardd", "btx-modeld"):
    assert f"bin/{binary}" in rows
record = {
    "source": source,
    "archive_name": archive.name,
    "archive_size_bytes": archive.stat().st_size,
    "candidate_archive_sha256": checksum.hexdigest(),
    "candidate_files": rows,
    "gui_observation_allowed": True,
}
(root / "provenance.json").write_text(json.dumps(record, indent=2) + "\n")
print("Archive gate PASS:", checksum.hexdigest(), flush=True)
