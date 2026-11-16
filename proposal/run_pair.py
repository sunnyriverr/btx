"""One paired direct-framework attempt. Preserve errors; do not retry."""
from pathlib import Path
import hashlib
import json
import os
import shutil
import signal
import subprocess
import time

root = Path.cwd()
records = root / 'records'
manifest = json.loads((root / 'proposal/manifest.json').read_text())
producer = json.loads((root / 'saved/producer.json').read_text())
def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()
for name, expected in producer['binary_sha256'].items():
    assert sha(root / 'baseline/bin' / name) == expected
assert sha(root / 'build/bin/btx-cli') == producer['binary_sha256']['btx-cli']
assert sha(root / 'source/test/functional/wallet_p2mr_aps_payment.py') == manifest['fixture_sha256']
for entry in manifest['changes']:
    assert sha(root / 'source' / entry['path']) == entry['sha256']
# Re-check host closure after compilation, including candidate NEEDED names.
verification = json.loads((records / 'verification-result.json').read_text())
import re
for name in ['btxd', 'btx-cli']:
    dynamic = subprocess.check_output(['readelf', '-d', str(root / 'build/bin' / name)], text=True)
    assert sorted(re.findall(r'\(NEEDED\).*\[(.*?)\]', dynamic)) == sorted(verification['root_dependencies'][name]['needed'])
for provider, entry in verification['ELF_dependencies'].items():
    host = Path(provider)
    if str(host).startswith(('/usr/lib/', '/lib/')):
        assert sha(host) == entry['sha256']
assert shutil.disk_usage(root).free >= 2 * 2**30
results = {'base': manifest['base'], 'candidate': manifest['candidate'],
           'fixture_sha256': manifest['fixture_sha256'], 'cases': [],
           'scope': 'Direct functional framework, same fixture, no full suite'}
for label, directory in [('baseline', root / 'baseline/bin'), ('candidate', root / 'build/bin')]:
    scratch = root / ('aps-private-' + label)
    assert not scratch.exists()
    scratch.mkdir()
    env = dict(os.environ)
    for variable, name in [('BTXD','btxd'), ('BITCOIND','btxd'), ('BTXCLI','btx-cli'), ('BITCOINCLI','btx-cli')]:
        env[variable] = str(directory / name)
    record = {'label': label, 'binaries': {name: sha(directory / name) for name in ['btxd','btx-cli']},
              'timeout': False}
    command = ['python3', str(root / 'source/test/functional/wallet_p2mr_aps_payment.py'),
               '--descriptors', '--configfile=' + str(root / 'build/test/config.ini'),
               '--tmpdir=' + str(scratch / 'regtest'), '--nocleanup']
    try:
        with (records / (label + '-functional.log')).open('w') as log:
            process = subprocess.Popen(command, cwd=root, env=env, stdout=log,
                                       stderr=subprocess.STDOUT, start_new_session=True)
            try:
                deadline = time.monotonic() + 300
                while True:
                    try:
                        record['exit_code'] = process.wait(timeout=2)
                        break
                    except subprocess.TimeoutExpired:
                        size = 0
                        for path in scratch.rglob('*'):
                            try:
                                if path.is_file():
                                    size += path.stat().st_size
                            except FileNotFoundError:
                                pass
                        record['peak_sampled_scratch'] = max(size, record.get('peak_sampled_scratch', 0))
                        if time.monotonic() >= deadline or size > 512 * 2**20 or shutil.disk_usage(root).free < 2 * 2**30:
                            record['timeout'] = time.monotonic() >= deadline
                            record['resource_stop'] = size > 512 * 2**20 or shutil.disk_usage(root).free < 2 * 2**30
                            os.killpg(process.pid, signal.SIGKILL)
                            record['exit_code'] = process.wait()
                            break
            finally:
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
        # The group belongs only to this fixture. Verify disappearance before
        # deleting data; killing/waiting for the parent is not sufficient.
        group_deadline = time.monotonic() + 5
        record['group_absent'] = False
        while time.monotonic() < group_deadline:
            try:
                os.killpg(process.pid, 0)
            except ProcessLookupError:
                record['group_absent'] = True
                break
            time.sleep(0.1)
        if not record['group_absent']:
            raise RuntimeError('Owned process group persists after stop; scratch retained')
        observation = scratch / 'regtest/p2mr-aps-payment.json'
        if observation.exists():
            record['observation'] = json.loads(observation.read_text())
    finally:
        if record.get('group_absent'):
            shutil.rmtree(scratch)
        record['scratch_removed'] = not scratch.exists()
        results['cases'].append(record)
        (records / 'paired-results.json').write_text(json.dumps(results, indent=2))
    # A baseline error is useful only after all setup preconditions passed.
    if label == 'baseline' and (record.get('resource_stop') or record['timeout'] or record.get('observation', {}).get('stage') != 'payment'):
        # A baseline pass also changes the regression decision; do not scale up.
        raise SystemExit('Baseline did not expose the intended payment failure; inspect evidence, no automatic retry')
    if label == 'baseline':
        error = record['observation'].get('rpc_error', {})
        if record['exit_code'] == 0 or error.get('code') != -6 or 'Unconfirmed UTXOs are available' not in error.get('message', ''):
            raise SystemExit('Baseline failure not the expected insufficient-funds classification; inspect exact error')
# No automatic semantic pass from workflow badge alone; inspect both receipts.
assert len(results['cases']) == 2
assert results['cases'][1]['exit_code'] == 0 and not results['cases'][1]['timeout']
assert results['cases'][1].get('observation', {}).get('stage') == 'passed'
