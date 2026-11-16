"""One original/draft comparison with verified unchanged retained executables."""
from pathlib import Path
import hashlib
import configparser
import json
import os
import shutil
import signal
import subprocess
import time

root = Path.cwd()
records = root / 'records'
proposal = root / 'proposal'
manifest = json.loads((proposal / 'manifest.json').read_text())
producer = json.loads((root / 'saved/producer.json').read_text())
def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()
assert producer['source_identity'] == manifest['source']
config = configparser.ConfigParser()
config.read(root / 'build/test/config.ini')
assert config['components'].getboolean('ENABLE_WALLET')
assert config['components'].getboolean('USE_SQLITE')
assert not config['components'].getboolean('ENABLE_MODELNET', fallback=False)
assert shutil.disk_usage(root).free >= 2 * 2**30
results = {'source': manifest['source'], 'cases': [], 'compiled': False,
           'shared_args': manifest['shared_args'],
           'scope': 'Direct normal functional framework with common startup profile and method observers; no product substitutions'}
for label in ['original', 'draft']:
    for name, digest in producer['binary_sha256'].items():
        assert sha(root / 'build/bin' / name) == digest
    script = proposal / (label + '-wallet_create_tx.py')
    assert sha(script) == manifest['scripts'][label]
    scratch = root / ('create-tx-private-' + label)
    assert not scratch.exists()
    scratch.mkdir()
    env = dict(os.environ, CASE_LABEL=label)
    for key, name in [('BTXD','btxd'), ('BITCOIND','btxd'), ('BTXCLI','btx-cli'), ('BITCOINCLI','btx-cli')]:
        env[key] = str(root / 'build/bin' / name)
    row = {'label': label, 'fixture_sha256': sha(script), 'binaries': producer['binary_sha256'],
           'timeout': False, 'resource_stop': False, 'group_absent': False}
    command = ['python3', str(proposal / 'run_case.py'), '--descriptors',
               '--configfile=' + str(root / 'build/test/config.ini'),
               '--tmpdir=' + str(scratch / 'regtest'),
               '--cachedir=' + str(scratch / 'cache'), '--nocleanup']
    try:
        with (records / (label + '-functional.log')).open('w') as log:
            proc = subprocess.Popen(command, cwd=root, env=env, stdout=log,
                                    stderr=subprocess.STDOUT, start_new_session=True)
            try:
                deadline = time.monotonic() + 600
                while True:
                    try:
                        row['exit_code'] = proc.wait(timeout=2)
                        break
                    except subprocess.TimeoutExpired:
                        size = 0
                        for path in scratch.rglob('*'):
                            try:
                                if path.is_file():
                                    size += path.stat().st_size
                            except FileNotFoundError:
                                pass
                        row['peak_sampled_scratch'] = max(size, row.get('peak_sampled_scratch', 0))
                        row['timeout'] = time.monotonic() >= deadline
                        row['resource_stop'] = size > 512 * 2**20 or shutil.disk_usage(root).free < 2 * 2**30
                        if row['timeout'] or row['resource_stop']:
                            os.killpg(proc.pid, signal.SIGKILL)
                            row['exit_code'] = proc.wait()
                            break
            finally:
                try:
                    os.killpg(proc.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
        stop_deadline = time.monotonic() + 5
        while time.monotonic() < stop_deadline:
            try:
                os.killpg(proc.pid, 0)
            except ProcessLookupError:
                row['group_absent'] = True
                break
            time.sleep(0.1)
        progress = records / (label + '-methods.json')
        if progress.exists():
            row['methods'] = json.loads(progress.read_text())
    finally:
        if row['group_absent']:
            shutil.rmtree(scratch)
        row['scratch_removed'] = not scratch.exists()
        results['cases'].append(row)
        (records / 'comparison.json').write_text(json.dumps(results, indent=2))
    if not row['group_absent'] or row['timeout'] or row['resource_stop']:
        raise SystemExit('Cleanup/resource stop: inspect evidence; no automatic retry')
    # An original setup/earlier failure remains useful diagnostic evidence.
    # Run the one draft case on a fresh datadir, without claiming the expected
    # unsupported-address failure unless the actual progress/error proves it.
    assert label != 'draft' or (row['exit_code'] == 0 and
        [x['method'] for x in row.get('methods', []) if x['status'] == 'passed'] == manifest['methods'])
