"""Preserve the clean pinned source and its successful or partial build."""
from pathlib import Path
import json
import os
from checkpoint import create

root = Path(os.environ["GITHUB_WORKSPACE"])
records = root / "records"
result = records / "build-exit.txt"
identity = {
    "source": "f9ba112822c0089ae2fc3bb5f71e1a28c7cf0302",
    "seed_checkpoint": 14707154639,
    "targets": ["btxd", "btx-cli"],
    "ninja_exit": int(result.read_text()) if result.is_file() else None,
    "target_build_complete": (records / "built-binaries.sha256").is_file(),
    "tests_included": False,
}
manifest = create(root, root / "retained-eth-build", identity)
summary = dict(identity, inner_sha256=manifest["archive_sha256"],
               members=len(manifest["rows"]),
               objects=sum(n.endswith(".o") and v["kind"] == "file"
                           for n, v in manifest["rows"].items()))
(records / "checkpoint-created.json").write_text(json.dumps(summary, indent=2) + "\n")
