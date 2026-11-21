"""Bring the disposable restored source tree to the exact upstream Git tree."""
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess
import tarfile
import time

from checkpoint import sha

workspace = Path(os.environ["GITHUB_WORKSPACE"])
root = workspace / "product"
records = workspace / "records"
head = "f9ba112822c0089ae2fc3bb5f71e1a28c7cf0302"
assert workspace == Path("/home/runner/work/btx/btx")
assert json.loads((records / "staging.json").read_text())["complete"]
git = ["git", "-C", str(workspace / "current-reference")]
assert subprocess.check_output([*git, "rev-parse", "HEAD"], text=True).strip() == head
def blob_id(data):
    return hashlib.sha1(f"blob {len(data)}\0".encode() + data).hexdigest()

tree = {}
for row in subprocess.check_output([*git, "ls-tree", "-rz", head]).split(b"\0"):
    if row:
        meta, name = row.decode().split("\t", 1)
        mode, kind, digest = meta.split()
        if kind == "blob":
            tree[name] = (mode, digest)

candidate_files = {str(p.relative_to(root)) for p in root.rglob("*") if p.is_file() or p.is_symlink()}
changes = {name: {"target_blob": None} for name in candidate_files - set(tree)}
for name, (mode, expected) in tree.items():
    path = root / name
    if mode == "120000" and path.is_symlink():
        data = os.readlink(path).encode()
    elif mode != "120000" and path.is_file() and not path.is_symlink() and bool(path.stat().st_mode & stat.S_IXUSR) == (mode == "100755"):
        data = path.read_bytes()
    else:
        data = None
    if data is None or blob_id(data) != expected:
        changes[name] = {"target_blob": expected}
assert len(changes) == 24, sorted(changes)
(records / "source-delta.json").write_text(json.dumps(changes, sort_keys=True, indent=2) + "\n")
for name, row in changes.items():
    target = root / name
    assert target.parent.resolve().is_relative_to(root.resolve())
    if row["target_blob"] is None:
        assert target.is_symlink() or target.is_file()
        target.unlink()

updated = set()
with subprocess.Popen([*git, "archive", head], stdout=subprocess.PIPE) as proc:
    with tarfile.open(fileobj=proc.stdout, mode="r|") as archive:
        for member in archive:
            name = member.name
            if name not in changes:
                continue
            target = root / name
            assert target.parent.resolve().is_relative_to(root.resolve())
            mode, expected = tree[name]
            assert expected == changes[name]["target_blob"]
            data = member.linkname.encode() if member.issym() else archive.extractfile(member).read()
            assert blob_id(data) == expected
            target.parent.mkdir(parents=True, exist_ok=True)
            if target.is_symlink() or target.is_file():
                target.unlink()
            if mode == "120000":
                target.symlink_to(data.decode())
            else:
                target.write_bytes(data)
                target.chmod(0o755 if mode == "100755" else 0o644)
            updated.add(name)
    assert proc.wait() == 0
assert updated == {n for n, row in changes.items() if row["target_blob"] is not None}

actual = {str(p.relative_to(root)) for p in root.rglob("*") if p.is_file() or p.is_symlink()}
assert actual == set(tree)
for name, (mode, expected) in tree.items():
    path = root / name
    if mode == "120000":
        assert path.is_symlink()
        data = os.readlink(path).encode()
    else:
        assert path.is_file() and not path.is_symlink()
        assert bool(path.stat().st_mode & stat.S_IXUSR) == (mode == "100755")
        data = path.read_bytes()
    assert blob_id(data) == expected, name
receipt = {
    "complete": True, "exact_source": head, "verified_source_blobs": len(tree),
    "replaced_or_added": len(updated), "removed_overlay_paths": len(changes) - len(updated),
    "preserved_file_timestamps_for_unchanged_inputs": True,
    "retained_helper_sha256": sha(workspace / "gui-pilot-runtime/qtbuild/bin/btx-modeld"),
}
(records / "source-sync.json").write_text(json.dumps(receipt, indent=2) + "\n")
