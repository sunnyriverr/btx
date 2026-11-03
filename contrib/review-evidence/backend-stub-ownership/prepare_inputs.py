#!/usr/bin/env python3
"""Reconstruct reviewed inputs from a repository containing both commits."""
import hashlib, json, pathlib, subprocess, sys
root = pathlib.Path(__file__).resolve().parent
repo = pathlib.Path(sys.argv[1]).resolve()
ids = json.loads((root / 'identities.json').read_text())
for folder, revision in [('source', ids['base']), ('candidate', 'd1ee21e828df480d6a3b9605a0d08a21fce8c6ef')]:
    for name, expected in ids[folder + '_tree_files'].items():
        data = subprocess.check_output(['git', '-C', str(repo), 'show', revision + ':' + name])
        if hashlib.sha256(data).hexdigest() != expected:
            raise RuntimeError('Input identity mismatch: ' + name)
        dest = root / folder / name
        if dest.exists() and dest.read_bytes() != data:
            raise RuntimeError('Refusing to overwrite different input: ' + str(dest))
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)
print('All exact baseline/candidate inputs verified; run python3 run_checks.py on macOS.')
