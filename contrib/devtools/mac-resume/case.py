"""Bounded ordinary startup/restart of the combined Mac package."""
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
import sys
import ctypes, shlex
import urllib.request

W = Path(os.environ['GITHUB_WORKSPACE'])
SOURCE = W / 'product'
OUT = Path(sys.argv[2])
OUT.mkdir(exist_ok=True)
RUNTIME = Path('/tmp').resolve() / ('btxpkg-' + os.environ['GITHUB_RUN_ID'] + '-' + os.environ['GITHUB_RUN_ATTEMPT'] + '-' + sys.argv[3])
BASE = '36ab43008cac48aa5c8410e4b70d90a249196a33'
EXPECTED = '58657765b5ac41252c44913f56c61247b781149fd21ed79374aedade67805ba1'
state = {'source_mapping': BASE, 'fixture': os.environ['GITHUB_SHA'],
         'platform': platform.platform(), 'checks': [], 'boots': [],
         'commands': [], 'cleanup_signals': [], 'passed': False,
         'test_scope': 'Packaged ordinary node-owned helper lifecycle; offline wallet-disabled regtest',
         'binary_bytes_changed': False, 'package_layout_variant': sys.argv[3],
         'source_build': False, 'manual_helper_launch': False}
package = Path(sys.argv[1]).resolve()
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


libproc = ctypes.CDLL('/usr/lib/libproc.dylib')
libproc.proc_pidpath.argtypes = [ctypes.c_int, ctypes.c_void_p, ctypes.c_uint32]
libproc.proc_pidpath.restype = ctypes.c_int

def proc_record(pid):
    buf = ctypes.create_string_buffer(4096)
    if libproc.proc_pidpath(pid, buf, len(buf)) <= 0:
        raise ProcessLookupError(pid)
    parent = subprocess.check_output(['ps','-p',str(pid),'-o','ppid='],text=True).strip()
    start = subprocess.check_output(['ps','-p',str(pid),'-o','lstart='],text=True).strip()
    argv = subprocess.check_output(['ps','-ww','-p',str(pid),'-o','command='],text=True).strip()
    return {'pid':pid,'ppid':int(parent),'start_ticks':start,'exe':buf.value.decode(),'argv':shlex.split(argv)}

def processes():
    found=[]
    for value in subprocess.check_output(['ps','-axo','pid='],text=True).split():
        try:
            pid=int(value);buf=ctypes.create_string_buffer(4096)
            if libproc.proc_pidpath(pid,buf,len(buf))<=0:continue
            if Path(buf.value.decode()).is_relative_to(package):found.append(proc_record(pid))
        except (OSError, ValueError, subprocess.CalledProcessError): pass
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


def rpc(method, *args):
    r = command([package / 'bin/btx-cli', '-regtest', '-datadir=' + str(RUNTIME),
                 '-rpcport=' + str(port), '-rpcclienttimeout=5', method, *args], timeout=8)
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



def guard_observation():
    try:
        value = rpc('modelsecurity', '{"op":"status"}')
        matching = [x for x in processes() if (package / 'libexec/btx-guardd').exists() and Path(x['exe']).is_file() and Path(x['exe']).samefile(package / 'libexec/btx-guardd')]
        ok = (value.get('ok') is True and value.get('automatic_spend_atoms') == '0'
              and value.get('policy_installed') is False and value.get('journal_valid') is True
              and len(matching) == 1 and matching[0]['ppid'] == node.pid)
        return {'ready': ok, 'reply': value, 'processes': matching}
    except RuntimeError as e:
        return {'ready': False, 'error': str(e), 'processes': []}


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
    deadline = time.monotonic() + 3
    while True:
        boot['guard'] = guard_observation()
        if boot['guard']['ready'] or time.monotonic() >= deadline:
            break
        time.sleep(.1)
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
        guard = guard_observation()
        boot.setdefault('guard_health', []).append(guard)
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
    check('fresh owned runtime', not RUNTIME.exists())
    RUNTIME.mkdir(mode=0o700)
    runtime_owned = True
    state['runtime'] = str(RUNTIME)
    state['variant'] = sys.argv[3]
    state['source_before'] = source_audit()
    before = {str(f.relative_to(package)): sha(f) for f in package.rglob('*') if f.is_file()}
    state['package_files_before'] = before
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
    check('default identity survives restart', first['public_identities'] == second['public_identities'])
    stop_node(2)
    state['source_after'] = source_audit()
    check('selected daemon/source files unchanged', state['source_before'] == state['source_after'])
    after = {str(f.relative_to(package)): sha(f) for f in package.rglob('*') if f.is_file()}
    state['package_files_after'] = after
    check('package bytes unchanged within this phase', before == after)
    # Same acceptance requirement on every variant, including negative controls.
    ready = all(b['guard']['ready'] and len(b.get('guard_health', [])) == 10
                and all(x['ready'] for x in b['guard_health']) for b in state['boots'])
    state['guard_contract_pass'] = ready
    check('packaged guard actually answers on both boots and throughout health polls', ready)
    check('fresh guard process after restart', first['guard']['processes'][0]['pid'] != second['guard']['processes'][0]['pid'])
    check('fresh guard boot after restart', first['guard']['reply']['guard_boot'] != second['guard']['reply']['guard_boot'])
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
