#!/usr/bin/env python3
"""Same native fail-before/pass-after cancellation and compatibility test.

Only --btxd and --label differ between baseline and candidate invocations.
Private AI-assisted fixture. No live peers, model execution or wallet spending.
"""
from pathlib import Path
import argparse, base64, errno, hashlib, json, os, resource, shutil, socket
import subprocess, sys, tempfile, threading, time, traceback, urllib.error, urllib.request

ROOT = Path(__file__).resolve().parent
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--btxd', type=Path, required=True)
parser.add_argument('--label', required=True)
parser.add_argument('--long-seconds', type=float, default=123)
opts = parser.parse_args()
BIN = opts.btxd.resolve(strict=True)
RUN = ROOT / opts.label
RUN.mkdir(exist_ok=False)
resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
env = {k: v for k, v in os.environ.items() if not k.startswith('BTX_')}
env.update(BTX_MATMUL_BACKEND='metal', BTX_MATMUL_V4_BACKEND='metal', BTX_MATMUL_REQUIRE_BACKEND='metal')
fixture = json.loads((ROOT / 'synthetic-blocks.json').read_text())
common = json.loads((ROOT / 'common-args.json').read_text())
wrapper = RUN / 'control-helper'
wrapper.write_text('#!' + sys.executable + '\nimport runpy\nrunpy.run_path(' + repr(str(ROOT / 'fixture_helper.py')) + ',run_name="__main__")\n')
wrapper.chmod(0o700)
report = {'status': 'running', 'ai_assisted': True, 'events': [], 'cases': {},
          'harness_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
          'helper_sha256': hashlib.sha256((ROOT / 'fixture_helper.py').read_bytes()).hexdigest(),
          'binary_sha256': hashlib.sha256(BIN.read_bytes()).hexdigest(),
          'long_seconds': opts.long_seconds, 'shutdown_deadline_seconds': 8,
          'scope': 'M4 strict-Metal toy regtest; synthetic owned/external private Unix helpers, no real remote Modelnet workload'}
nodes = []
event_lock = threading.Lock()

def event(phase, **data):
    with event_lock:
        report['events'].append({'phase': phase, 'time': time.time(), **data})
        (RUN / 'result.json').write_text(json.dumps(report, indent=2) + '\n')
        print(phase, json.dumps(data)[:500], flush=True)

def until(predicate, timeout, reason):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            if predicate():
                return
        except Exception:
            pass
        time.sleep(.05)
    raise AssertionError(reason)

class Node:
    def __init__(self, name, external=False):
        self.name, self.external = name, external
        self.data = Path(tempfile.mkdtemp(prefix='btx-cancel-'))
        self.model = self.data / 'regtest/modelnet'
        self.model.mkdir(parents=True)
        self.sock = self.model / 'modeld.sock'
        self.log = (RUN / (name + '-console.log')).open('wb')
        self.external_log = (RUN / (name + '-external-console.log')).open('wb')
        self.proc = self.helper_proc = None
        self.fillers = []
        with socket.socket() as s:
            s.bind(('127.0.0.1', 0))
            self.port = s.getsockname()[1]
        nodes.append(self)

    def rpc(self, method, *params, timeout=30):
        auth = base64.b64encode((self.data / 'regtest/.cookie').read_bytes().strip()).decode()
        req = urllib.request.Request('http://127.0.0.1:' + str(self.port) + '/',
            data=json.dumps({'jsonrpc': '2.0', 'id': 1, 'method': method, 'params': list(params)}).encode(),
            headers={'Authorization': 'Basic ' + auth, 'Content-Type': 'application/json'})
        try:
            with urllib.request.urlopen(req, timeout=timeout) as f:
                r = json.load(f)
        except urllib.error.HTTPError as e:
            r = json.load(e)
        if r.get('error'):
            raise RuntimeError(json.dumps(r['error']))
        return r['result']

    def start(self):
        assert shutil.disk_usage(ROOT).free > 100 * 1024**2
        extra = ['-modelhelper=' + str(wrapper)]
        if self.external:
            extra = ['-modelrpcsocket=' + str(self.sock), '-modeldir=' + str(self.model)]
            if self.helper_proc is None:
                self.helper_proc = subprocess.Popen([str(wrapper), '-modeldir=' + str(self.model),
                    '-modelrpcsocket=' + str(self.sock)], env=env, stdout=self.external_log, stderr=self.external_log)
                until(self.sock.exists, 5, 'External socket missing')
        cmd = [str(BIN), '-datadir=' + str(self.data), '-rpcport=' + str(self.port),
               '-rpcbind=127.0.0.1', '-rpcallowip=127.0.0.1', '-modelnet=1',
               '-modelbind=0', '-modellandiscovery=0', '-modelfollowpeers=0',
               '-modelseed=none', '-modelpeer=127.0.0.1:1'] + extra + common
        self.proc = subprocess.Popen(cmd, env=env, stdin=subprocess.DEVNULL, stdout=self.log, stderr=self.log)
        event('start', case=self.name, pid=self.proc.pid, external=self.external)
        until(lambda: self.rpc('getblockchaininfo')['chain'] == 'regtest', 25, 'RPC not ready')
        until(lambda: self.rpc('getmodelnetworkinfo').get('helper_ready'), 15, 'Helper not ready')
        event('helper-ready', case=self.name, pid=int((self.model / 'fixture-pid').read_text()))

    def progress(self, blocks, phase):
        for b in blocks:
            assert self.rpc('submitblock', b['raw']) in [None, 'duplicate', 'inconclusive']
        c = self.rpc('getblockchaininfo')
        f = self.rpc('getfinalityinfo')
        a = f['active_tip']
        assert c['bestblockhash'] == blocks[-1]['hash'] == a['hash']
        assert not c['is_stale'] and a['chainwork'] == a['authenticated_chainwork']
        assert f['matmul_validation_mode'] == 'consensus' and not f['trusted_mirror']
        v = self.rpc('getmininginfo')['backend_runtime']['rc_exact_replay']['last_validation']
        assert v['available'] and v['outcome'] == 'valid' and v['execution_policy'] == 'strict-device'
        assert v['require_device'] and v['full_metal_pipeline'] and v['fully_accelerated']
        assert all(v[k] == 0 for k in ['cpu_gemm_calls', 'cpu_gemm_fallbacks', 'host_xof_calls', 'device_xof_fallbacks'])
        d = {'chain': c, 'finality': f, 'runtime': v}
        (RUN / (self.name + '-' + phase + '.json')).write_text(json.dumps(d, indent=2) + '\n')
        return d

    def direct_ping(self):
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
            s.settimeout(3)
            s.connect(str(self.sock))
            s.sendall(b'{"method":"fixture_ping","params":[]}\n')
            s.shutdown(socket.SHUT_WR)
            raw = b''
            while b'\n' not in raw:
                part = s.recv(4096)
                if not part:
                    raise RuntimeError('Fixture ping closed without a reply')
                raw += part
            return json.loads(raw)['result']

    def release(self):
        if self.model.exists():
            (self.model / 'fixture-release').touch()
            (self.model / 'fixture-pause-accept').unlink(missing_ok=True)
        for s in self.fillers:
            s.close()
        self.fillers.clear()

    def pause_and_fill(self):
        (self.model / 'fixture-pause-accept').touch()
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
            s.connect(str(self.sock))  # Wake the fixture's currently blocking accept.
        until(lambda: (self.model / 'fixture-accept-paused').exists(), 3, 'Accept not paused')
        refused = None
        for _ in range(64):
            s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            s.setblocking(False)
            error = s.connect_ex(str(self.sock))
            self.fillers.append(s)
            if error not in [0, errno.EINPROGRESS, errno.EALREADY]:
                refused = error
                break
        assert refused in [errno.EAGAIN, errno.EWOULDBLOCK, errno.ECONNREFUSED], (len(self.fillers), refused)
        event('accept-queue-full', case=self.name, connections=len(self.fillers), errno=refused)
        time.sleep(2.5)  # External supervisor polls every2s; leave one genuine attempt blocked.

    def archive(self):
        for p, n in [(self.data / 'regtest/debug.log', self.name + '-debug.log'),
                     (self.model / 'fixture-events.jsonl', self.name + '-helper-events.jsonl')]:
            if p.exists():
                shutil.copyfile(p, RUN / n)

    def cleanup(self):
        self.release()
        if self.proc and self.proc.poll() is None:
            try:
                self.rpc('stop', timeout=2)
            except Exception:
                self.proc.terminate()
            try:
                self.proc.wait(timeout=12)
            except subprocess.TimeoutExpired:
                self.proc.kill()
                self.proc.wait(timeout=5)
        self.archive()
        if self.helper_proc and self.helper_proc.poll() is None:
            self.helper_proc.terminate()  # Harness cleanup AFTER external-ownership assertions.
            self.helper_proc.wait(timeout=5)
        if self.data.exists():
            shutil.rmtree(self.data)
        self.log.close()
        self.external_log.close()

def shutdown_case(name, external=False, mode=None, ignore_term=False, backlog=False):
    n = Node(name, external)
    n.start()
    n.progress(fixture['old'], 'seed20')
    if ignore_term:
        (n.model / 'fixture-ignore-term').touch()
    if backlog:
        n.pause_and_fill()
    elif mode:
        (n.model / 'fixture-fault').write_text(mode)
        until(lambda: (n.model / 'fixture-stalled-getmodelnetworkinfo').exists(), 12, 'No stalled supervisor poll')
    state = n.progress(fixture['fork'][:3], 'fault21')
    start = time.monotonic()
    n.rpc('stop')
    passed = True
    try:
        n.proc.wait(timeout=8)
    except subprocess.TimeoutExpired:
        passed = False
        event('shutdown-regression-failure', case=name, seconds=time.monotonic()-start)
        n.release()
        (n.model / 'fixture-ignore-term').unlink(missing_ok=True)
        n.proc.wait(timeout=10)
    elapsed = time.monotonic()-start
    assert n.proc.returncode == 0, n.proc.returncode
    d = {'passed': passed, 'stop_to_exit_seconds': elapsed, 'exit_code': n.proc.returncode,
         'external': external, 'mode': mode, 'backlog': backlog, 'ignore_term': ignore_term,
         'tip_before_stop': state['chain']['bestblockhash']}
    if external:
        assert n.helper_proc.poll() is None, 'Node killed external helper'
        n.release()
        # A deliberately full accept queue needs a moment to drain after
        # unpausing it; process survival alone is not the serving oracle.
        until(lambda: n.direct_ping().get('alive'), 5, 'External helper did not resume serving')
        ping = n.direct_ping()
        assert ping == {'pid': n.helper_proc.pid, 'alive': True}, ping
        d['external_alive_and_serving_after_node_exit'] = ping
    n.release()
    for p in n.model.glob('fixture-stalled-*'):
        p.unlink()
    (n.model / 'fixture-fault').unlink(missing_ok=True)
    (n.model / 'fixture-ignore-term').unlink(missing_ok=True)
    n.start()
    assert n.rpc('getbestblockhash') == fixture['fork'][2]['hash']
    fresh = n.progress(fixture['fork'][3:], 'restart23')
    d['restart_fresh_height'] = fresh['chain']['blocks']
    n.rpc('stop')
    n.proc.wait(timeout=8)
    assert n.proc.returncode == 0
    if external:
        assert n.helper_proc.poll() is None
    report['cases'][name] = d
    n.cleanup()
    event('case-completed', case=name, **d)

def main():
    long_node = Node('long-call')
    long_node.start()
    long_node.progress(fixture['old'], 'seed20')
    (long_node.model / 'fixture-long-delay').write_text(str(opts.long_seconds))
    reply = {}
    def get_long():
        start = time.monotonic()
        try:
            reply['result'] = long_node.rpc('getmodel', 'f'*96, timeout=opts.long_seconds+20)
        except Exception as e:
            reply['error'] = repr(e)
        reply['elapsed_s'] = time.monotonic()-start
    worker = threading.Thread(target=get_long)
    worker.start()
    until(lambda: (long_node.model / 'fixture-long-started').exists(), 5, 'Long call did not start')
    long_node.progress(fixture['fork'][:3], 'during-long21')
    event('long-call-waiting', seconds=opts.long_seconds)
    shutdown_case('healthy-owned')
    shutdown_case('partial-owned', mode='partial')
    shutdown_case('silent-owned', mode='silent')
    shutdown_case('stubborn-owned', mode='partial', ignore_term=True)
    shutdown_case('partial-external', external=True, mode='partial')
    shutdown_case('backlog-external', external=True, backlog=True)
    worker.join(timeout=opts.long_seconds+20)
    assert not worker.is_alive() and 'error' not in reply, reply
    assert reply['result'].get('fixture_long_reply') is True, reply
    assert reply['elapsed_s'] >= opts.long_seconds-.1, reply
    try:
        long_node.rpc('getmodel', 'fixture-refusal')
        raise AssertionError('Fixture error not propagated')
    except RuntimeError as e:
        assert 'fixture refusal' in str(e), str(e)
    long_node.progress(fixture['fork'][3:], 'after-long23')
    long_node.rpc('stop')
    long_node.proc.wait(timeout=8)
    assert long_node.proc.returncode == 0
    long_node.cleanup()
    report['long_call'] = reply
    report['status'] = 'pass' if all(c['passed'] for c in report['cases'].values()) else 'fail'
    event('completed', status=report['status'], long_call=reply)

try:
    main()
except BaseException as e:
    report['status'] = 'harness_or_control_failure'
    event('failure', error=repr(e), traceback=traceback.format_exc())
    raise
finally:
    for n in nodes:
        if n.data.exists():
            n.cleanup()
    (RUN / 'result.json').write_text(json.dumps(report, indent=2) + '\n')
raise SystemExit(0 if report['status'] == 'pass' else 1)
