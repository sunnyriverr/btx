"""Observe model identity CLI labels on the unchanged official archive."""
from pathlib import Path
import configparser
import hashlib
import json
import os
import re
import shutil
import signal
import subprocess
import tarfile
import time
import urllib.request

W = Path(os.environ['GITHUB_WORKSPACE'])
P = W / 'product'
H = Path(__file__).parent
O = W / 'identity-label-results'
R = W / 'identity-label-runtime'
O.mkdir(exist_ok=True)
BASE = '0ac06fd23b4a62038963fb29f1c77ab26d7a1346'
EXPECTED = '58657765b5ac41252c44913f56c61247b781149fd21ed79374aedade67805ba1'
state = {'source': BASE, 'fixture': os.environ['GITHUB_SHA'], 'commands': [],
         'observation_complete': False, 'test_pass': False, 'cache_saved': False}
env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1')
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def save(): (O / 'result.json').write_text(json.dumps(state, indent=2) + '\n')
def command(args, label, allowed=(0,), timeout=120):
    print('START', label, flush=True)
    with (O / (label + '.log')).open('wb') as log:
        proc = subprocess.Popen([str(a) for a in args], stdout=log, stderr=subprocess.STDOUT,
                                env=env, start_new_session=True)
        try:
            rc = proc.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            os.killpg(proc.pid, signal.SIGTERM)
            try: proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                os.killpg(proc.pid, signal.SIGKILL)
                proc.wait()
            raise
    state['commands'].append({'label': label, 'args': [str(a) for a in args], 'exit': rc})
    save()
    assert rc in allowed, (label, rc)
    print('END', label, rc, flush=True)
    return (O / (label + '.log')).read_text(errors='replace')
def audit():
    assert subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=P, text=True).strip() == BASE
    assert not subprocess.check_output(['git', 'status', '--porcelain', '--untracked-files=no'], cwd=P)
    return {n: sha(P / n) for n in ['src/rpc/client.cpp', 'src/rpc/modelnet.cpp', 'src/modelnet/helper.cpp',
                                  'src/modeld.cpp', 'test/functional/test_framework/test_framework.py']}
package = None
def processes():
    found = []
    if package is None: return found
    for pid in Path('/proc').iterdir():
        if not pid.name.isdigit(): continue
        try:
            exe = Path(os.readlink(pid / 'exe'))
            if exe.is_relative_to(package): found.append({'pid': int(pid.name), 'exe': str(exe)})
        except (OSError, PermissionError): pass
    return found
try:
    assert shutil.disk_usage(W).free > 3 * 1024**3
    state['source_before'] = audit()
    archive = W / 'release.tar.gz'
    url = 'https://github.com/btxchain/btx/releases/download/v0.34.16/btx-0.34.16-x86_64-linux-gnu.tar.gz'
    with urllib.request.urlopen(url, timeout=60) as source, archive.open('wb') as target:
        shutil.copyfileobj(source, target)
    assert sha(archive) == EXPECTED
    state['archive'] = {'url': url, 'sha256': EXPECTED, 'bytes': archive.stat().st_size, 'asset_id': 720210208, 'source_mapping': 'Published replacement for release-0.34.16/0ac06fd2 perNumair; not independently reproduced build'}
    assert archive.stat().st_size == 158893635
    dest = W / 'release-package'
    dest.mkdir()
    with tarfile.open(archive) as tar:
        members = tar.getmembers()
        assert sum(m.size for m in members) < 2 * 1024**3
        tar.extractall(dest, filter='data')
    archive.unlink()
    candidates = list(dest.rglob('bin/btxd'))
    assert len(candidates) == 1
    package = candidates[0].parent.parent
    assert not processes()
    before = {str(f.relative_to(package)): sha(f) for f in package.rglob('*') if f.is_file()}
    state['package_files_before'] = before
    assert 'v0.34.16' in command([package / 'bin/btxd', '-version'], 'daemon-version')
    assert 'v0.34.16' in command([package / 'bin/btx-cli', '-version'], 'cli-version')
    help_text = command([package / 'bin/btxd', '-help-debug'], 'daemon-options')
    features = {'ENABLE_WALLET': '-wallet=<path>' in help_text,
                'ENABLE_MODELNET': bool(re.search(r'(?m)^\s+-modelnet(?:[=\s]|$)', help_text)),
                'ENABLE_ZMQ': '-zmqpubhashblock=' in help_text,
                'ENABLE_EXTERNAL_SIGNER': '-signer=<cmd>' in help_text}
    assert features['ENABLE_WALLET'] and features['ENABLE_MODELNET'], features
    dynamic = command(['readelf', '-d', package / 'libexec/btxd.real'], 'daemon-dynamic-dependencies')
    assert 'libsqlite3.so' in dynamic, 'Cannot establish descriptor-wallet SQLite profile from package dependencies'
    state['features'] = features
    state['profile_basis'] = 'Conditional daemon options and SQLite ELF dependency; descriptor-wallet test profile, optional legacy backend not qualified. Not the producer CMakeCache.'
    config = configparser.ConfigParser()
    config['environment'] = {'CLIENT_NAME': 'BTX', 'CLIENT_BUGREPORT': 'https://github.com/btxchain/btx/issues',
                             'SRCDIR': str(P), 'BUILDDIR': str(package), 'EXEEXT': '',
                             'RPCAUTH': str(P / 'share/rpcauth/rpcauth.py')}
    config['components'] = {k: str(v).lower() for k, v in features.items()}
    config['components'].update({'USE_SQLITE': 'true', 'USE_BDB': 'false', 'ENABLE_CLI': 'true',
                                 'ENABLE_BITCOIND': 'true', 'ENABLE_WALLET_TOOL': str((package / 'bin/btx-wallet').exists()).lower(),
                                 'ENABLE_BITCOIN_UTIL': str((package / 'bin/btx-util').exists()).lower(), 'ENABLE_USDT_TRACEPOINTS': 'false'})
    configfile = O / 'functional-config.ini'
    with configfile.open('w') as f: config.write(f)
    R.mkdir(mode=0o700)
    env.update(PYTHONPATH=str(P / 'test/functional'), IDENTITY_RUNTIME=str(R), IDENTITY_RESULTS=str(O))
    command(['python3', H / 'case.py', '--configfile=' + str(configfile),
             '--tmpdir=' + str(R / 'case'), '--cachedir=' + str(R / 'cache'),
             '--portseed=43417', '--nocleanup'], 'identity-label-workflow', timeout=180)
    observed = json.loads((O / 'observations.json').read_text())
    assert observed['observation_complete'] and observed['controls_complete']
    assert len(observed['bad_cli']) == 4 and len(observed['quoted_controls']) == 4
    assert all(r['returncode'] != 0 and r['state_unchanged'] for r in observed['bad_cli'])
    assert all(r['returncode'] == 0 and r['persisted_exactly'] for r in observed['quoted_controls'])
    state['workflow'] = observed
    state['framework_exit'] = state['commands'][-1]['exit']
    state['test_pass'] = False  # The unchanged CLI has four observed failures, not a repaired product.
    state['source_after'] = audit()
    assert state['source_before'] == state['source_after']
    after = {str(f.relative_to(package)): sha(f) for f in package.rglob('*') if f.is_file()}
    assert before == after
    state['package_files_unchanged'] = True
    state['observation_complete'] = observed['observation_complete']
except Exception as error:
    state['error'] = repr(error)
    raise
finally:
    state['cleanup_before'] = processes()
    state['cleanup_signals'] = []
    for row in state['cleanup_before']:
        os.kill(row['pid'], signal.SIGTERM)
        state['cleanup_signals'].append(row)
    for _ in range(50):
        if not processes(): break
        time.sleep(.1)
    state['cleanup_remaining'] = processes()
    if R.exists():
        for f in R.rglob('*'):
            if f.is_file() and f.name in ['test_framework.log', 'debug.log']:
                out = O / 'logs' / f.relative_to(R)
                out.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(f, out)
        if not state['cleanup_remaining']: shutil.rmtree(R)
    state['runtime_removed'] = not R.exists()
    state['observation_complete'] &= not state['cleanup_before'] and not state['cleanup_remaining']
    save()
assert state['observation_complete']
