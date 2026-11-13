"""Require the two expected handoff files and verify the inner archive identity."""
import hashlib
import json
from pathlib import Path
import sys

SOURCE = "88c9b49cb16360fc8fbf3f84003b8b54c29e6db5"
NAME = "btx-linux-gui-candidate.tar.gz"


def main():
    directory = Path(sys.argv[1])
    record = json.loads((directory / "provenance.json").read_text())
    archive = directory / NAME
    if record["source"] != SOURCE or record["archive_name"] != NAME:
        raise ValueError("unexpected source or archive name")
    if not archive.is_file() or archive.is_symlink():
        raise ValueError("archive is missing or not a regular file")
    checksum = hashlib.sha256()
    size = 0
    with archive.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            checksum.update(block)
            size += len(block)
    if size <= 0 or size != record["archive_size_bytes"]:
        raise ValueError("archive size mismatch")
    if checksum.hexdigest() != record["candidate_archive_sha256"]:
        raise ValueError("archive checksum mismatch")
    print(f"Verified {NAME}: {size} bytes, SHA-256 {checksum.hexdigest()}")


if __name__ == "__main__":
    main()
