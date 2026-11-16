"""Correctness verdict over the identical bounded transport probe, before and after."""
import argparse
import json
from pathlib import Path
import subprocess
import sys

p = argparse.ArgumentParser()
p.add_argument('--client', required=True)
p.add_argument('--probe-dir', type=Path, required=True)
p.add_argument('--out', type=Path, required=True)
a = p.parse_args()
a.out.mkdir(parents=True, exist_ok=True)
ret = subprocess.run([sys.executable, str(a.probe_dir/'run.py'), '--client', a.client, '--out', str(a.out)], timeout=120)
if ret.returncode:
    raise SystemExit(ret.returncode)
r = json.loads((a.out/'result.json').read_text())
assert r['complete'] and len(r['cases']) == 6
failures = [name for name, row in r['cases'].items() if row['observation']['classification'] == 'false_success_reproduced']
verdict = {'complete': True, 'correctness_pass': not failures, 'failed_cases': failures,
           'passed_cases': [name for name in r['cases'] if name not in failures],
           'scope': r['scope'], 'same_observer': True}
(a.out/'qualification.json').write_text(json.dumps(verdict, indent=2)+'\n')
print(json.dumps(verdict, indent=2))
raise SystemExit(1 if failures else 0)
