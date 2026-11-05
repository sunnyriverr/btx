from pathlib import Path
import base64
import hashlib
import http.client
import http.server
import json
import os
import shutil
import socket
import subprocess
import threading
import time
import uuid
import sys

R = Path('/tmp/btx-session2-index-cli')
B = Path('/tmp/btx-session2-helper-restart-current/build')
CLI = Path(sys.argv[1])
RESULT = Path(sys.argv[2])
EXPECTED_CLI_SHA = sys.argv[3]
HELPER = B / 'bin/btx-modeld'
ROOT = R / 'paired-runtime'
ROOT.mkdir(mode=0o700)
MODEL = ROOT / 'models'
MODEL.mkdir()
CLI_DIR = ROOT / 'cli'
CLI_DIR.mkdir()
SOCKET = ROOT / 'rpc.sock'
COOKIE = ROOT / 'fixture.cookie'
credential = 'fixture:' + uuid.uuid4().hex
COOKIE.write_text(credential)
COOKIE.chmod(0o600)
authorization = 'Basic ' + base64.b64encode(credential.encode()).decode()
build = json.loads((R / 'build-result.json').read_text())
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
assert sha(CLI) == EXPECTED_CLI_SHA
assert sha(HELPER) == build['helper_sha256']
record = {'checks': [], 'cli_calls': [], 'adapter_requests': [], 'cleanup': {},
          'cli_sha256_before': sha(CLI), 'helper_sha256_before': sha(HELPER),
          'requirements': [], 'functional_failures': [],
          'scope': 'Actual CLI -> loopback test HTTP adapter -> real helper Unix RPC; no btxd'}
helper = None
server = None
thread = None
lock = threading.Lock()
log = RESULT.with_suffix('.helper.log').open('wb')


def save():
    RESULT.write_text(json.dumps(record, indent=2) + '\n')


def check(label, actual, expected):
    record['checks'].append({'label': label, 'actual': actual, 'expected': expected,
                             'passed': actual == expected})
    save()
    if actual != expected:
        raise AssertionError(label + ': ' + repr(actual) + ' != ' + repr(expected))


def helper_network_sockets():
    inodes = set()
    for fd in Path('/proc', str(helper.pid), 'fd').iterdir():
        try:
            name = os.readlink(fd)
        except FileNotFoundError:
            continue
        if name.startswith('socket:['):
            inodes.add(name[8:-1])
    sockets = []
    for kind in ['tcp', 'tcp6', 'udp', 'udp6']:
        for line in Path('/proc/net', kind).read_text().splitlines()[1:]:
            fields = line.split()
            if fields[9] in inodes:
                sockets.append({'kind': kind, 'local': fields[1], 'remote': fields[2], 'state': fields[3]})
    return sockets


def unix_rpc(method, params=None):
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as connection:
        connection.settimeout(10)
        connection.connect(str(SOCKET))
        connection.sendall((json.dumps({'id': 1, 'method': method, 'params': params or []}) + '\n').encode())
        connection.shutdown(socket.SHUT_WR)
        data = bytearray()
        while b'\n' not in data:
            part = connection.recv(65536)
            if not part:
                break
            data.extend(part)
            if len(data) > 1024 * 1024:
                raise RuntimeError('Unexpected helper response size')
    response = json.loads(data)
    if response.get('error'):
        raise RuntimeError(str(response['error']))
    return response['result']


class Adapter(http.server.BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_POST(self):
        if self.client_address[0] != '127.0.0.1' or self.headers.get('Authorization') != authorization:
            self.send_error(401)
            return
        size = int(self.headers['Content-Length'])
        if not 0 < size < 65536:
            self.send_error(400)
            return
        request = json.loads(self.rfile.read(size))
        method = request['method']
        params = request.get('params', [])
        if method not in ['addmodelindex', 'removemodelindex', 'getsearchpeers']:
            self.send_error(400)
            return
        original = params
        if isinstance(params, dict):
            if method == 'getsearchpeers' and params == {}:
                params = []
            elif method != 'getsearchpeers' and set(params) == {'endpoint'}:
                params = [params['endpoint']]
            else:
                self.send_error(400)
                return
        if not isinstance(params, list) or len(params) != (0 if method == 'getsearchpeers' else 1):
            self.send_error(400)
            return
        with lock:
            record['adapter_requests'].append({'method': method, 'received_params': original,
                                                'forwarded_params': params})
        # This fixture does not supply a canned success or alter endpoint bytes.
        result = unix_rpc(method, params)
        body = json.dumps({'result': result, 'error': None, 'id': request['id']}).encode()
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def direct(method, params):
    connection = http.client.HTTPConnection('127.0.0.1', server.server_port, timeout=10)
    try:
        connection.request('POST', '/', json.dumps({'id': 2, 'method': method, 'params': params}),
                           {'Authorization': authorization, 'Content-Type': 'application/json'})
        response = connection.getresponse()
        body = response.read()
        if response.status != 200:
            raise RuntimeError('Adapter HTTP status ' + str(response.status))
        value = json.loads(body)
        if value.get('error'):
            raise RuntimeError(str(value['error']))
        return value['result']
    finally:
        connection.close()


def cli(method, value=None, named=False, quoted=False):
    args = [str(CLI), '-regtest', '-datadir=' + str(CLI_DIR), '-rpcconnect=127.0.0.1',
            '-rpcport=' + str(server.server_port), '-rpccookiefile=' + str(COOKIE),
            '-rpcclienttimeout=5']
    if named:
        args.append('-named')
    args.append(method)
    if value is not None:
        value = json.dumps(value) if quoted else value
        args.append('endpoint=' + value if named else value)
    before = len(record['adapter_requests'])
    result = subprocess.run(args, capture_output=True, text=True, timeout=15)
    delta = len(record['adapter_requests']) - before
    row = {'method': method, 'argv': args, 'named': named, 'quoted_json_string': quoted,
           'exit': result.returncode, 'stdout': result.stdout, 'stderr': result.stderr,
           'adapter_request_delta': delta}
    record['cli_calls'].append(row)
    save()
    return row


def state(label, expected):
    row = cli('getsearchpeers')
    check(label + ' readback CLI success', row['exit'], 0)
    peers = json.loads(row['stdout'])['peers']
    check(label + ' exact helper endpoints', sorted(p['endpoint'] for p in peers), sorted(expected))


def endpoints(label):
    row = cli('getsearchpeers')
    check(label + ' readback succeeds', row['exit'], 0)
    return sorted(p['endpoint'] for p in json.loads(row['stdout'])['peers'])


def required(label, actual, expected):
    passed = actual == expected
    record['requirements'].append({'label': label, 'actual': actual, 'expected': expected, 'passed': passed})
    if not passed:
        record['functional_failures'].append(label)
    save()


def success_response(label, row):
    value = json.loads(row['stdout'])
    check(label + ' addrman response flag', value['addrman'], False)
    check(label + ' automatic spend response flag', value['automatic_spend_atoms'], 0)


try:
    helper_args = [str(HELPER), '-modeldir=' + str(MODEL), '-modelrpcsocket=' + str(SOCKET),
                   '-modelstorage=16MiB', '-modelhost=0', '-modelseed=off', '-modelfollowpeers=0',
                   '-modellandiscovery=0', '-modelnatpmp=0', '-pwcchain=regtest']
    record['helper_args'] = helper_args
    helper = subprocess.Popen(helper_args, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT)
    record['helper_pid'] = helper.pid
    deadline = time.monotonic() + 20
    while True:
        if helper.poll() is not None:
            raise RuntimeError('Helper startup exited')
        try:
            info = unix_rpc('getmodelnetworkinfo')
            if info.get('pq1_ready'):
                record['helper_info'] = info
                break
        except (OSError, ValueError):
            pass
        if time.monotonic() >= deadline:
            raise RuntimeError('Helper readiness deadline')
        time.sleep(.1)
    server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), Adapter)
    record['adapter_bind'] = list(server.server_address)
    record['helper_network_sockets_before'] = helper_network_sockets()
    check('helper has no observed TCP/UDP socket at start', record['helper_network_sockets_before'], [])
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    sentinel, target = '127.0.0.1:37492', '127.0.0.1:37491'
    state('initial', [])
    direct('addmodelindex', [sentinel])
    state('sentinel established by direct HTTP', [sentinel])
    for named in [False, True]:
        row = cli('addmodelindex', target, named=named)
        after = endpoints('ordinary add ' + str(named))
        required('ordinary add workflow ' + str(named),
                 {'exit': row['exit'], 'ingress': row['adapter_request_delta'], 'peers': after},
                 {'exit': 0, 'ingress': 1, 'peers': sorted([sentinel, target])})
        if row['exit'] != 0:
            check('add failure is original JSON conversion ' + str(named),
                  'Error parsing JSON: ' + target in row['stderr'], True)
            check('add failure never entered adapter ' + str(named), row['adapter_request_delta'], 0)
            check('failed add preserves exact state ' + str(named), after, [sentinel])
            # Restore only fixture prerequisites, after recording the failed
            # required property, so baseline removal starts with target present.
            direct('addmodelindex', [target])
        else:
            success_response('ordinary add ' + str(named), row)
        state('removal precondition ' + str(named), [sentinel, target])
        row = cli('removemodelindex', target, named=named)
        after = endpoints('ordinary remove ' + str(named))
        required('ordinary remove workflow ' + str(named),
                 {'exit': row['exit'], 'ingress': row['adapter_request_delta'], 'peers': after},
                 {'exit': 0, 'ingress': 1, 'peers': [sentinel]})
        if row['exit'] != 0:
            check('remove failure is original JSON conversion ' + str(named),
                  'Error parsing JSON: ' + target in row['stderr'], True)
            check('remove failure never entered adapter ' + str(named), row['adapter_request_delta'], 0)
            check('failed remove preserves exact state ' + str(named), after, sorted([sentinel, target]))
            direct('removemodelindex', [target])
        else:
            success_response('ordinary remove ' + str(named), row)
        state('iteration cleaned ' + str(named), [sentinel])
    direct('addmodelindex', [target])
    state('direct add control', [sentinel, target])
    direct('removemodelindex', [target])
    state('direct remove control', [sentinel])
    direct('removemodelindex', [sentinel])
    state('preferences cleaned', [])
    record['helper_network_sockets_after'] = helper_network_sockets()
    check('helper has no observed TCP/UDP socket at finish', record['helper_network_sockets_after'], [])
    record['cli_sha256_after'] = sha(CLI)
    record['helper_sha256_after'] = sha(HELPER)
    check('CLI unchanged', record['cli_sha256_after'], record['cli_sha256_before'])
    check('helper unchanged', record['helper_sha256_after'], record['helper_sha256_before'])
    record['suite_complete'] = True
    record['required_properties_pass'] = not record['functional_failures']
finally:
    if server:
        port = server.server_port
        server.shutdown()
        server.server_close()
        if thread:
            thread.join(timeout=3)
        with socket.socket() as probe:
            probe.settimeout(1)
            record['cleanup']['adapter_listener_closed'] = probe.connect_ex(('127.0.0.1', port)) != 0
    if helper and helper.poll() is None:
        helper.terminate()
        try:
            helper.wait(timeout=15)
            record['cleanup']['helper_stop'] = 'SIGTERM, no kill fallback'
        except subprocess.TimeoutExpired:
            helper.kill()
            helper.wait(timeout=5)
            record['cleanup']['helper_stop'] = 'kill fallback after timeout'
    record['cleanup']['helper_exit'] = helper.returncode if helper else None
    record['cleanup']['adapter_thread_stopped'] = not thread.is_alive() if thread else True
    log.close()
    shutil.rmtree(ROOT)
    record['cleanup']['owned_runtime_and_cookie_removed'] = not ROOT.exists()
    save()

assert record.get('suite_complete'), 'Workflow did not finish its safety/valid controls'
assert record['cleanup']['helper_stop'] == 'SIGTERM, no kill fallback'
assert record['cleanup']['adapter_listener_closed'] and record['cleanup']['adapter_thread_stopped']
print(json.dumps({'suite_complete': True, 'required_pass': record['required_properties_pass'], 'failures': len(record['functional_failures']), 'checks': len(record['checks']), 'cli_calls': len(record['cli_calls'])}))
sys.exit(0 if record['required_properties_pass'] else 1)
