"""Preserve the clean pinned source and its successful or partial build."""
from pathlib import Path
import json
import os
from checkpoint import create

root = Path(os.environ["GITHUB_WORKSPACE"])
records = root / "records"
result = records / "build-exit.txt"
identity = {
    "source": "7d65025bb3bff27e4f6c2fdc95f33e4b859a2df5",
    "seed_checkpoint": 14734210789,
    "targets": ["btxd"],
    "candidate": "wallet-relock-v1",
    "ninja_exit": int(result.read_text()) if result.is_file() else None,
    "target_build_complete": (records / "built-binaries.sha256").is_file(),
    "tests_included": False,
}
manifest = create(root, root / "retained-presync-build", identity)
summary = dict(identity, inner_sha256=manifest["archive_sha256"],
               members=len(manifest["rows"]),
               objects=sum(n.endswith(".o") and v["kind"] == "file"
                           for n, v in manifest["rows"].items()))
(records / "checkpoint-created.json").write_text(json.dumps(summary, indent=2) + "\n")
