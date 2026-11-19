"""Verify the exact base and single product change before configuring."""
import hashlib
import json
from pathlib import Path
import subprocess

root = Path.cwd()
recipe = root / "proposal"
records = root / "records"
identity = json.loads((recipe / "source-hashes.json").read_text())
base = json.loads((records / "source-sync.json").read_text())
assert base["complete"] and base["exact_source"] == identity["pinned_linux_base"]
patch = recipe / "fix.patch"
assert hashlib.sha256(patch.read_bytes()).hexdigest() == identity["patch"]
assert [x for x in patch.read_text().splitlines() if x.startswith("+++ ")] == ["+++ b/src/modelnet/helper.cpp"]
subprocess.run(["git","apply","--directory=product","--check",str(patch)],check=True)
subprocess.run(["git","apply","--directory=product",str(patch)],check=True)
candidate = root / "product/src/modelnet/helper.cpp"
assert hashlib.sha256(candidate.read_bytes()).hexdigest() == identity["pinned_linux_candidate_helper_source_sha256"]
assert hashlib.sha256((recipe / "observe-alias-save.py").read_bytes()).hexdigest() == identity["fixture"]
(records / "alias-candidate-source.json").write_text(json.dumps(identity,indent=2)+"\n")
