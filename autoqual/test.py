"""Real helper automatic-search check; initial observation is external file IO only."""
from pathlib import Path
import hashlib
import json
import os
import socket
import subprocess
import sys
import time
import traceback

BINARY = Path(sys.argv[1]).resolve()
ROOT = Path(sys.argv[2]).resolve()
OUT = Path(sys.argv[3]).resolve()
assert os.getuid() != 0, 'Run with the isolated unprivileged test identity'
assert not ROOT.exists(), 'Refuse a reused runtime root'
ROOT.mkdir(mode=0o700)
OUT.mkdir(parents=True, exist_ok=True)
processes = {}
handles = []
calls = []
observations = []
checks = []
starts = []
expected = {}
stage = 'setup'
started = time.monotonic()
result = {'status': 'INCOMPLETE'}


def save(name, value):
    (OUT / name).write_text(json.dumps(value, indent=2) + '\n')


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_json(path):
    try:
        return json.loads(path.read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def index(name):
    obj = read_json(ROOT / name / 'search-index.json')
    return {} if obj is None else {r['model_id']: r for r in obj.get('records', [])}


def alive(name):
    assert name in processes and processes[name].poll() is None, (name, 'helper stopped')


def launch(name, port=None, peer=None):
    directory = ROOT / name
    fresh = not directory.exists()
    if fresh:
        directory.mkdir(mode=0o700)
        assert not (directory / 'search-index.json').exists()
    sock = ROOT / (name + '.sock')
    assert not sock.exists()
    argv = [str(BINARY), '-modeldir=' + str(directory), '-modelrpcsocket=' + str(sock),
            '-modelstorage=8MiB', '-pwcchain=regtest', '-modellandiscovery=0', '-modelnatpmp=0']
    if port is not None:
        argv.append('-modelbind=127.0.0.1:' + str(port))
    if peer is not None:
        argv.append('-modelpeer=127.0.0.1:' + str(peer))
    log = OUT / ('helper-' + str(len(starts) + 1) + '-' + name + '.log')
    handle = log.open('wb')
    handles.append(handle)
    processes[name] = subprocess.Popen(argv, stdout=handle, stderr=subprocess.STDOUT)
    starts.append({'name': name, 'argv': argv, 'pid': processes[name].pid, 'stage': stage, 'fresh_state': fresh})
    deadline = time.monotonic() + 25
    while time.monotonic() < deadline:
        alive(name)
        if sock.exists() and 'btx-modeld: PQ1 ready;' in log.read_text(errors='replace'):
            return
        time.sleep(.1)
    raise AssertionError(('startup timeout', name))


def stop(name):
    proc = processes.get(name)
    if proc is None:
        return
    proc.terminate()
    try:
        proc.wait(10)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait(5)
        raise AssertionError(('unclean stop', name))
    assert proc.returncode == 0, (name, proc.returncode)
    del processes[name]
    sock = ROOT / (name + '.sock')
    if sock.exists():
        sock.unlink()


def rpc(name, method, params):
    # No arbitrary receiver method, implicit scope, or readiness RPC can poll for success.
    if name != 'publisher':
        assert name == 'receiver' and stage == 'offline_restart_local', (stage, method)
        assert method in ('searchmodels', 'listmodelsearchrecords')
        if method == 'searchmodels':
            assert params == [{'scope': 'LOCAL', 'limit': 100}]
    else:
        assert method in ('publishmodelsearchrecord', 'listmodelsearchrecords')
    with socket.socket(socket.AF_UNIX) as client:
        client.settimeout(8)
        client.connect(str(ROOT / (name + '.sock')))
        client.sendall((json.dumps({'id': len(calls) + 1, 'method': method, 'params': params}) + '\n').encode())
        client.shutdown(socket.SHUT_WR)
        with client.makefile('rb') as stream:
            reply = json.loads(stream.readline(2 ** 20))
    calls.append({'role': name, 'stage': stage, 'method': method, 'params': params, 'reply': reply})
    assert reply.get('error') is None, reply
    return reply['result']


def publish(number):
    model_id = f'{number:096x}'
    reply = rpc('publisher', 'publishmodelsearchrecord', [model_id, {
        'type': 'btx-model-search-v1', 'canonical_name': 'automatic-search-fixture-' + str(number),
        'display_name': 'automatic-search-fixture-' + str(number), 'expires_at': 0,
        'short_description': 'disposable signed metadata; no model payload',
    }])
    assert reply['signed_metadata'] and reply['model_id'] == model_id, reply
    return model_id


def publisher_records():
    records = rpc('publisher', 'listmodelsearchrecords', [{'limit': 100}])['records']
    assert records and all(r['signed_metadata'] and r['signature'] and r['pubkey'] for r in records)
    assert len({r['signer_id'] for r in records}) == 1
    return {r['model_id']: r for r in records}


def observe_until(name, wanted, seconds=60):
    deadline = time.monotonic() + seconds
    last_hash = None
    while time.monotonic() < deadline:
        alive(name)
        path = ROOT / name / 'search-index.json'
        raw = path.read_bytes() if path.exists() else b''
        h = hashlib.sha256(raw).hexdigest()
        if h != last_hash:
            try:
                snapshot = json.loads(raw) if raw else None
            except json.JSONDecodeError:
                snapshot = None
            rows = [] if snapshot is None else snapshot.get('records', [])
            observations.append({'stage': stage, 'seconds': time.monotonic() - started,
                                 'file_sha256': h, 'records': len(rows),
                                 'ids': [r['model_id'] for r in rows]})
            if snapshot is not None:
                (OUT / ('snapshot-' + str(len(observations)) + '.json')).write_bytes(raw)
            last_hash = h
        actual = index(name)
        if actual == wanted:
            return actual
        time.sleep(.2)
    raise AssertionError(('passive propagation unresolved', stage, sorted(index(name)), sorted(wanted)))


def participation(name, expected_pin=None):
    deadline = time.monotonic() + 3
    while time.monotonic() < deadline:
        obj = read_json(ROOT / name / 'swarm/native-participation.json')
        if obj and obj.get('authenticated_peers', 0) >= 1:
            assert obj['network'] == 'regtest' and obj['acquired_models'] == 0
            assert obj['automatic_spend_atoms'] == '0' and not obj['lan_enabled']
            pins = {x['transport_pin'] for x in obj['peer_observations']}
            assert len(pins) == 1 and len(next(iter(pins))) == 96
            if expected_pin is not None:
                assert pins == {expected_pin}
            save('participation-' + stage + '.json', obj)
            return next(iter(pins))
        time.sleep(.1)
    raise AssertionError(('no authenticated peer evidence', stage, obj))


try:
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        port = sock.getsockname()[1]
    launch('publisher', port=port)
    for i in range(1, 18):
        publish(i)
    expected = publisher_records()
    assert len(expected) == 17
    save('publisher-original-records.json', expected)

    stage = 'no_contact_control'
    launch('control')
    deadline = time.monotonic() + 11
    while time.monotonic() < deadline:
        alive('control')
        assert not (set(index('control')) & set(expected))
        time.sleep(.2)
    stop('control')
    checks.append({'stage': stage, 'pass': True, 'receiver_rpc_calls': 0})

    stage = 'initial_passive_propagation'
    launch('receiver', peer=port)
    assert starts[-1]['fresh_state']
    assert not any(c['role'] == 'receiver' for c in calls)
    observe_until('receiver', expected)
    pin = participation('receiver')
    assert not any(c['role'] == 'receiver' for c in calls)
    checks.append({'stage': stage, 'pass': True, 'exact_signed_records': 17, 'receiver_rpc_calls': 0})

    # Persisted records must stand alone; restart with the publisher unavailable.
    stage = 'stop_sources'
    stop('publisher')
    stop('receiver')
    saved_hash = digest(ROOT / 'receiver/search-index.json')
    stage = 'offline_restart_local'
    launch('receiver', peer=port)
    assert 'publisher' not in processes and index('receiver') == expected
    local = rpc('receiver', 'searchmodels', [{'scope': 'LOCAL', 'limit': 100}])
    assert local['scope'] == 'LOCAL'
    assert {x['model_id'] for x in local['results']} == set(expected)
    for key in ['connected_peers_queried', 'index_peers_queried', 'routing_peers_queried', 'responses_received']:
        assert local['coverage'][key] == 0, (key, local['coverage'])
    restored = rpc('receiver', 'listmodelsearchrecords', [{'limit': 100}])
    assert {x['model_id']: x for x in restored['records']} == expected
    assert digest(ROOT / 'receiver/search-index.json') == saved_hash
    checks.append({'stage': stage, 'pass': True, 'exact_signed_records': 17,
                   'publisher_offline': True, 'saved_bytes_unchanged': True, 'remote_queries_and_responses': 0})

    stage = 'reconnect_new_record'
    launch('publisher', port=port)
    publish(18)
    expected = publisher_records()
    assert len(expected) == 18
    observe_until('receiver', expected)
    participation('receiver', pin)
    checks.append({'stage': stage, 'pass': True, 'exact_signed_records': 18, 'same_transport_pin': True})

    stage = 'passive_health'
    deadline = time.monotonic() + 6
    while time.monotonic() < deadline:
        alive('publisher')
        alive('receiver')
        assert index('receiver') == expected
        time.sleep(.25)
    stop('receiver')
    stop('publisher')
    checks.append({'stage': stage, 'pass': True, 'clean_stops': True})
    result['status'] = 'PASS'
except Exception as error:
    result.update(status='UNRESOLVED_FAILURE', error=repr(error), traceback=traceback.format_exc())
    # Read-only diagnostics only. No network-search rescue and no promotion to PASS.
    for name in ['publisher', 'receiver', 'control']:
        for rel in ['search-index.json', 'swarm/native-participation.json']:
            obj = read_json(ROOT / name / rel)
            if obj is not None:
                save('diagnostic-' + name + '-' + rel.replace('/', '-'), obj)
finally:
    cleanup_errors = []
    for name in list(processes):
        try:
            stop(name)
        except Exception as error:
            cleanup_errors.append(repr(error))
    for handle in handles:
        handle.close()
    if cleanup_errors:
        result.update(status='UNRESOLVED_FAILURE', cleanup_errors=cleanup_errors)
    result.update(final_stage=stage, checks=checks, calls=calls, starts=starts,
                  observations=observations, seconds=time.monotonic() - started,
                  uid=os.getuid(), gid=os.getgid(), binary_sha256=digest(BINARY),
                  script_sha256=digest(Path(__file__)), live_owned_helpers=len(processes))
    save('result.json', result)
    print(result['status'], 'checks', len(checks), 'RPCs', len(calls), 'starts', len(starts), flush=True)
    if result.get('traceback'):
        print(result['traceback'], flush=True)
raise SystemExit(0 if result['status'] == 'PASS' else 1)
