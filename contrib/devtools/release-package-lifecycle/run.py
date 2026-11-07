"""Bounded ordinary startup/restart of the unchanged official Linux package."""
from pathlib import Path
import hashlib
import json
import os
import platform
import shutil
import signal
import socket
import subprocess
import tarfile
import time
import traceback
import urllib.request

W = Path(os.environ['GITHUB_WORKSPACE'])
SOURCE = W / 'product'
OUT = W / 'package-lifecycle-results'
OUT.mkdir(exist_ok=True)
RUNTIME = Path('/tmp') / ('btxpkg-' + os.environ['GITHUB_RUN_ID'] + '-' + os.environ['GITHUB_RUN_ATTEMPT'])
BASE = '0ac06fd23b4a62038963fb29f1c77ab26d7a1346'
EXPECTED = '58657765b5ac41252c44913f56c61247b781149fd21ed79374aedade67805ba1'
state = {'source_mapping': BASE, 'fixture': os.environ['GITHUB_SHA'],
         'platform': platform.platform(), 'checks': [], 'boots': [],
         'commands': [], 'cleanup_signals': [], 'passed': False,
         'test_scope': 'Packaged ordinary node-owned helper lifecycle; offline wallet-disabled regtest',
         'product_patch': False, 'source_build': False, 'manual_helper_launch': False}
package = None
node = None
node_log = None
runtime_owned = False
env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1')
# The launchers, not this test, must resolve their shipped dependencies.
for key in ['LD_LIBRARY_PATH', 'LD_PRELOAD', 'BTX_MODELD', 'BTX_MODELHELPER']:
    env.pop(key, None)


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def save():
    (OUT / 'result.json').write_text(json.dumps(state, indent=2) + '\n')


def check(name, condition):
    state['checks'].append({'name': name, 'pass': bool(condition)})
    save()
    assert condition, name


def proc_record(pid):
    p = Path('/proc') / str(pid)
    # parent/stat field parsing must tolerate spaces in comm.
    fields = (p / 'stat').read_text().rsplit(')', 1)[1].split()
    return {'pid': pid, 'ppid': int(fields[1]), 'start_ticks': fields[19],
            'exe': os.readlink(p / 'exe'),
            'argv': (p / 'cmdline').read_bytes().decode().rstrip('\0').split('\0')}


def processes():
    found = []
    if package is None:
        return found
    for p in Path('/proc').iterdir():
        if not p.name.isdigit():
            continue
        try:
            row = proc_record(int(p.name))
            if Path(row['exe']).is_relative_to(package):
                found.append(row)
        except (OSError, ValueError, ProcessLookupError):
            pass
    return found


def command(args, timeout=15):
    start = time.monotonic()
    r = subprocess.run([str(a) for a in args], cwd=RUNTIME, env=env,
                       capture_output=True, text=True, timeout=timeout)
    state['commands'].append({'args': [str(a) for a in args], 'exit': r.returncode,
                              'seconds': time.monotonic() - start,
                              'stderr': r.stderr[:3000]})
    save()
    return r


def rpc(method):
    r = command([package / 'bin/btx-cli', '-regtest', '-datadir=' + str(RUNTIME),
                 '-rpcport=' + str(port), '-rpcclienttimeout=5', method], timeout=8)
    if r.returncode:
        raise RuntimeError((method, r.returncode, r.stderr[:1500]))
    return json.loads(r.stdout)


def wait_for(fn, timeout, description):
    until = time.monotonic() + timeout
    errors = []
    while time.monotonic() < until:
        if node is not None and node.poll() is not None:
            raise RuntimeError(('node exited', node.returncode, description))
        try:
            value = fn()
            if value:
                state.setdefault('waits', []).append({'description': description,
                                                     'transient_errors': errors[-4:]})
                return value
        except (RuntimeError, OSError, subprocess.TimeoutExpired) as e:
            errors.append(repr(e))
        time.sleep(.25)
    raise TimeoutError((description, errors[-4:]))


def source_audit():
    assert subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=SOURCE, text=True).strip() == BASE
    assert not subprocess.check_output(['git', 'status', '--porcelain', '--untracked-files=no'], cwd=SOURCE)
    names = ['src/init.cpp', 'src/rpc/modelnet.cpp', 'src/modelnet/supervisor.cpp',
             'test/functional/feature_model_security_v2.py']
    return {name: sha(SOURCE / name) for name in names}


def live_info():
    info = rpc('getmodelnetworkinfo')
    if (info.get('helper_ready') is True and info.get('helper_state') == 'READY'
            and info.get('helper_managed_by_btxd') is True
            and info.get('owner_helper_pid', 0) > 0):
        return info
    return None


def observe_boot(number):
    global node, node_log
    check('no packaged processes before boot' + str(number), not processes())
    node_log = (OUT / ('boot' + str(number) + '-console.log')).open('wb')
    start = time.monotonic()
    node = subprocess.Popen([str(package / 'bin/btxd')] + node_args,
                            cwd=RUNTIME, env=env, stdout=node_log, stderr=subprocess.STDOUT,
                            start_new_session=True)
    wait_for(lambda: rpc('getblockchaininfo'), 45, 'node RPC boot' + str(number))
    info = wait_for(live_info, 60, 'managed helper ready boot' + str(number))
    parent = proc_record(node.pid)
    helper = proc_record(info['owner_helper_pid'])
    check('actual node executable is shipped daemon boot' + str(number),
          Path(parent['exe']) == package / 'libexec/btxd.real')
    check('helper is direct child of actual node boot' + str(number), helper['ppid'] == node.pid)
    check('actual helper executable is shipped helper boot' + str(number),
          Path(helper['exe']) == package / 'libexec/btx-modeld.real')
    check('no external helper or Modelnet enable override boot' + str(number),
          not any(a.split('=', 1)[0] in ['-modelrpcsocket', '-modelhelper', '-modeld', '-modelnet']
                  for a in parent['argv']))
    check('offline helper command propagated boot' + str(number),
          all(a in helper['argv'] for a in ['-modelseed=off', '-modelfollowpeers=0',
                                            '-modellandiscovery=0', '-modelstorage=16MiB']))
    check('helper has no peer or network listener arguments boot' + str(number),
          not any(a.split('=', 1)[0] in ['-modelbind', '-modelpeer', '-modelseednode']
                  for a in helper['argv']))
    check('no helper restart fallback boot' + str(number), info['helper_restart_count'] == 0)
    check('no automatic spending boot' + str(number), info['automatic_spend_atoms'] == 0)
    check('helper reports isolated storage/seed/follow policy boot' + str(number),
          info.get('quota_bytes') == 16 * 1024**2 and info.get('seed_mode') == 'off'
          and info.get('follow_configured_peers') is False)
    ids = rpc('listmodelidentities')['identities']
    check('persisted default identity exists boot' + str(number), bool(ids))
    identity_files = list(RUNTIME.rglob('identities.json'))
    check('one private public-identity catalog boot' + str(number), len(identity_files) == 1)
    boot = {'number': number, 'ready_seconds': time.monotonic() - start,
            'node': parent, 'helper': helper, 'network_info': info,
            'identity_ids': sorted(x['id'] for x in ids),
            'public_identities': ids,
            'identity_public_store_sha256': sha(identity_files[0]), 'health': []}
    state['boots'].append(boot)
    save()
    for i in range(10):
        now = rpc('getmodelnetworkinfo')
        chain = rpc('getblockchaininfo')
        peers = rpc('getconnectioncount')
        current = proc_record(helper['pid'])
        healthy = (now.get('helper_ready') is True and now.get('helper_managed_by_btxd') is True
                   and now.get('owner_helper_pid') == helper['pid']
                   and now.get('helper_state') == 'READY' and now.get('helper_restart_count') == 0
                   and current['ppid'] == node.pid and current['start_ticks'] == helper['start_ticks']
                   and chain['chain'] == 'regtest' and chain['blocks'] == 0 and peers == 0
                   and now.get('peers_connected') == 0
                   and now['automatic_spend_atoms'] == 0 and now.get('advertised_host') is not True
                   and now.get('public_host_reachable') is False)
        boot['health'].append({'poll': i, 'pass': healthy, 'height': chain['blocks'],
                               'peers': peers, 'model_peers': now.get('peers_connected'),
                               'helper_pid': current['pid']})
        check('ordinary node/helper health boot' + str(number) + ' poll' + str(i), healthy)
        time.sleep(.5)
    return boot


def stop_node(number):
    global node_log
    start = time.monotonic()
    stopped = command([package / 'bin/btx-cli', '-regtest', '-datadir=' + str(RUNTIME),
                       '-rpcport=' + str(port), '-rpcclienttimeout=5', 'stop'])
    check('RPC stop accepted boot' + str(number), stopped.returncode == 0)
    node.wait(timeout=30)
    node_log.close()
    node_log = None
    check('normal node exit boot' + str(number), node.returncode == 0)
    until = time.monotonic() + 5
    while processes() and time.monotonic() < until:
        time.sleep(.1)
    check('owned helpers gone after normal shutdown boot' + str(number), not processes())
    state['boots'][-1]['stop_seconds'] = time.monotonic() - start
    logfile = RUNTIME / 'regtest/debug.log'
    if logfile.exists():
        shutil.copyfile(logfile, OUT / ('through-boot' + str(number) + '-debug.log'))


try:
    check('remote disk headroom before extraction', shutil.disk_usage(W).free > 3 * 1024**3)
    state['source_before'] = source_audit()
    check('fresh owned runtime', not RUNTIME.exists())
    RUNTIME.mkdir(mode=0o700)
    runtime_owned = True
    state['runtime'] = str(RUNTIME)
    archive = W / 'package-lifecycle.tar.gz'
    url = 'https://github.com/btxchain/btx/releases/download/v0.34.16/btx-0.34.16-x86_64-linux-gnu.tar.gz'
    with urllib.request.urlopen(url, timeout=60) as response, archive.open('wb') as target:
        shutil.copyfileobj(response, target)
    state['archive'] = {'asset_id': 720210208, 'url': url, 'sha256': sha(archive),
                        'bytes': archive.stat().st_size,
                        'mapping_basis': 'Numair published0ac mapping; producer build not reproduced'}
    check('exact current archive digest and size', sha(archive) == EXPECTED and archive.stat().st_size == 158893635)
    dest = W / 'package-lifecycle-installation'
    dest.mkdir()
    with tarfile.open(archive) as tar:
        check('bounded unpacked package', sum(m.size for m in tar.getmembers()) < 2 * 1024**3)
        tar.extractall(dest, filter='data')
    archive.unlink()
    candidates = list(dest.rglob('bin/btxd'))
    check('one packaged node entrypoint', len(candidates) == 1)
    package = candidates[0].parent.parent.resolve()
    before = {str(f.relative_to(package)): sha(f) for f in package.rglob('*') if f.is_file()}
    state['package_files_before'] = before
    for name in ['btxd', 'btx-cli', 'btx-modeld', 'btx-guardd']:
        for sub, suffix in [('bin', ''), ('libexec', '.real')]:
            path = package / sub / (name + suffix)
            check('executable package file ' + str(path.relative_to(package)), os.access(path, os.X_OK))
            if sub == 'bin':
                shutil.copyfile(path, OUT / (name + '-launcher.sh'))
            else:
                r = command(['ldd', path])
                (OUT / (name + '-ldd.log')).write_text(r.stdout + r.stderr)
                # ldd without launcher LD_LIBRARY_PATH is diagnostic only: bundled resolution is exercised live.
    for name in ['btxd', 'btx-cli']:
        r = command([package / 'bin' / name, '-version'])
        check(name + ' shipped version', r.returncode == 0 and 'v0.34.16' in r.stdout)
        (OUT / (name + '-version.log')).write_text(r.stdout + r.stderr)
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        port = sock.getsockname()[1]
    node_args = ['-regtest', '-datadir=' + str(RUNTIME), '-server=1', '-disablewallet',
                 '-listen=0', '-networkactive=0', '-connect=0', '-dnsseed=0', '-discover=0',
                 '-natpmp=0', '-rpcbind=127.0.0.1', '-rpcallowip=127.0.0.1', '-rpcport=' + str(port),
                 '-modelbind=off', '-modelhost=0', '-modelseed=off', '-modelfollowpeers=0',
                 '-modellandiscovery=0', '-modelstorage=16MiB', '-printtoconsole=1']
    state['node_arguments'] = node_args
    first = observe_boot(1)
    stop_node(1)
    second = observe_boot(2)
    check('new node process on restart', first['node']['pid'] != second['node']['pid'])
    check('new helper process on restart', first['helper']['pid'] != second['helper']['pid'])
    check('default identity survives restart', first['identity_ids'] == second['identity_ids'])
    check('public identity fields survive restart', first['public_identities'] == second['public_identities'])
    check('public identity store bytes preserved', first['identity_public_store_sha256'] == second['identity_public_store_sha256'])
    stop_node(2)
    state['source_after'] = source_audit()
    check('source review files unchanged', state['source_before'] == state['source_after'])
    after = {str(f.relative_to(package)): sha(f) for f in package.rglob('*') if f.is_file()}
    check('all distributed package files unchanged', before == after)
    state['package_files_after'] = after
    state['passed'] = True
except Exception as error:
    state['error'] = repr(error)
    state['traceback'] = traceback.format_exc()
    raise
finally:
    state['cleanup_before'] = processes()
    # Only exact-executable records from this unique extraction are eligible for cleanup.
    for row in state['cleanup_before']:
        try:
            current = proc_record(row['pid'])
            if current['exe'] == row['exe'] and current['start_ticks'] == row['start_ticks']:
                os.kill(row['pid'], signal.SIGTERM)
                state['cleanup_signals'].append({'pid': row['pid'], 'signal': 'SIGTERM'})
        except OSError:
            pass
    if node is not None:
        try:
            node.wait(timeout=10)
        except subprocess.TimeoutExpired:
            pass
    until = time.monotonic() + 10
    while processes() and time.monotonic() < until:
        time.sleep(.1)
    state['cleanup_remaining'] = processes()
    if node_log is not None:
        node_log.close()
    if runtime_owned and RUNTIME.exists() and not state['cleanup_remaining']:
        log = RUNTIME / 'regtest/debug.log'
        if log.exists():
            shutil.copyfile(log, OUT / 'final-debug.log')
        shutil.rmtree(RUNTIME)
    state['runtime_removed'] = not RUNTIME.exists()
    state['passed'] &= not state['cleanup_before'] and not state['cleanup_remaining'] and state['runtime_removed']
    save()
assert state['passed']
