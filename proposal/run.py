"""Bounded disposable regtest proposal; not executed during preparation."""
from pathlib import Path
import hashlib
import json
import os
import signal
import subprocess

root = Path.cwd()
records = root / 'records'
records.mkdir(exist_ok=True)
fixture = root / 'proposal/wallet_bcp1_concurrent_reservations.py'
manifest = json.loads((root / 'proposal/inputs.json').read_text())
assert hashlib.sha256(fixture.read_bytes()).hexdigest() == manifest[fixture.name]
producer = json.loads((root / 'saved/producer.json').read_text())
assert producer['source_identity'] == '1e2f8b5f12295002334d3390c12cac0bb4ae2aff'
for name, expected in producer['binary_sha256'].items():
    assert hashlib.sha256((root / 'build/bin' / name).read_bytes()).hexdigest() == expected
scratch = root / 'concurrent-private'
assert not scratch.exists()
scratch.mkdir()
destination = root / 'source/test/functional' / fixture.name
assert not destination.exists()
destination.write_bytes(fixture.read_bytes())
env = dict(os.environ)
for key, name in [('BTXD', 'btxd'), ('BITCOIND', 'btxd'), ('BTXCLI', 'btx-cli'), ('BITCOINCLI', 'btx-cli')]:
    env[key] = str(root / 'build/bin' / name)
command = ['python3', str(destination), '--descriptors',
           '--configfile=' + str(root / 'build/test/config.ini'),
           '--tmpdir=' + str(scratch / 'regtest'), '--nocleanup']
result = {'source': producer['source_identity'], 'fixture': manifest,
          'binary_sha256': producer['binary_sha256'], 'timeout': False,
          'scope': 'Direct maintained functional framework; no whole-suite or deterministic-schedule claim'}
with (records / 'fixture.log').open('w') as output:
    process = subprocess.Popen(command, cwd=root, env=env, stdout=output,
                               stderr=subprocess.STDOUT, start_new_session=True)
    try:
        result['exit_code'] = process.wait(timeout=300)
    except subprocess.TimeoutExpired:
        result['timeout'] = True
        os.killpg(process.pid, signal.SIGKILL)
        result['exit_code'] = process.wait()
    finally:
        # Include any node left behind by framework failure, only in our group.
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
observations = scratch / 'regtest/concurrent-package-observations.json'
if observations.exists():
    (records / observations.name).write_bytes(observations.read_bytes())
# Never upload disposable wallet directories, cookie, config or debug logs.
import shutil
shutil.rmtree(scratch)
result['scratch_removed'] = not scratch.exists()
(records / 'fixture-result.json').write_text(json.dumps(result, indent=2))
raise SystemExit(0 if result['exit_code'] == 0 and not result['timeout'] else 1)
