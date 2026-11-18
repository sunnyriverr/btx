"""Bounded ordinary upload/status liveness observation; no product changes.

Independent origin release; first-run spare-worker precondition failed.
Reuses the #818 controlled HTTP origin and disposable Unix helper fixture.
Not AWS/MinIO authentication, node liveness, or native platform qualification.
"""
import argparse
import hashlib
import json
from pathlib import Path
import socket
import struct
import tempfile
import threading
import time
import traceback
from fixture import Fixture
from origin import Origin

HELPER_SHA = '28d7ecb6c611e5676d85de7a64038bc7d07cd0b6b2fb2606390d5e6405838ad2'
RPC_SECONDS = 12
HOLD_SECONDS = 2
GATE_SECONDS = 8


def payload():
    size = 256 * 1024
    header = json.dumps({'w': {'dtype': 'U8', 'shape': [size-128],
                              'data_offsets': [0, size-128]}}, separators=(',', ':')).encode()
    assert len(header) <= 120
    return struct.pack('<Q', 120) + header.ljust(120, b' ') + b'A' * (size-128)


class PausedOrigin(Origin):
    def __init__(self):
        super().__init__(deadline_seconds=90)
        self.entered = threading.Event()
        self.release = threading.Event()
        self.gate = {}

    def _handler(self):
        parent = super()._handler()
        owner = self
        class Handler(parent):
            def _dispatch(self, path, query, body):
                if self.command == 'PUT' and '/files/' in path and not owner.entered.is_set():
                    owner.gate.update(path=path, bytes=len(body), entered=time.monotonic())
                    owner.entered.set()
                    if not owner.release.wait(GATE_SECONDS):
                        owner.gate['watchdog_fired'] = True
                        return 503, b'<Error><Code>FixtureDeadline</Code></Error>', None, 'gate-timeout'
                    owner.gate['resumed'] = time.monotonic()
                return super()._dispatch(path, query, body)
        return Handler

    def unblock(self):
        self.gate.setdefault('released', time.monotonic())
        self.release.set()

    def __exit__(self, *args):
        self.unblock()
        return super().__exit__(*args)


class Calls:
    """Separate sockets, bounded reads and unique response-checked request IDs."""
    def __init__(self, endpoint):
        self.endpoint = endpoint
        self.rows = {}
        self.threads = []
        self.lock = threading.Lock()

    def call(self, name, method, *params, sent=None):
        row = {'id': name, 'method': method, 'started': time.monotonic()}
        with self.lock:
            assert name not in self.rows
            self.rows[name] = row
        try:
            with socket.socket(socket.AF_UNIX) as conn:
                conn.settimeout(RPC_SECONDS)
                conn.connect(str(self.endpoint))
                conn.sendall(json.dumps({'id': name, 'method': method, 'params': list(params)}).encode()+b'\n')
                conn.shutdown(socket.SHUT_WR)
                row['sent'] = time.monotonic()
                if sent: sent.set()
                with conn.makefile('rb') as wire:
                    raw = wire.readline(2 * 1024 * 1024)
                row['received'] = time.monotonic()
                row['raw_reply'] = raw.decode('utf-8', errors='replace')
                assert raw.endswith(b'\n'), 'missing/oversized reply'
                reply = json.loads(raw)
                assert reply.get('id') == name, 'wrong response ID'
                assert reply.get('error') is None, reply
                row['result'] = reply['result']
                row['finished'] = time.monotonic()
                return row['result']
        except Exception:
            row['error'] = traceback.format_exc()
            if sent: sent.set()
            raise

    def start(self, name, method, *params):
        sent = threading.Event()
        def run():
            try: self.call(name, method, *params, sent=sent)
            except Exception: pass  # retained in row; strict validator rejects it
        t = threading.Thread(target=run, name=name, daemon=True)
        self.threads.append(t)
        t.start()
        assert sent.wait(2), 'request was not sent'
        assert 'error' not in self.rows[name], self.rows[name]
        return t

    def join(self):
        for t in self.threads:
            t.join(RPC_SECONDS + 1)
            assert not t.is_alive(), 'RPC thread exceeded bound'


def validate(r):
    """Classify valid observations; reject missing paths, errors and leaked cleanup."""
    assert r['complete'] is True
    assert r['helper_sha256'] == HELPER_SHA
    assert r['unix_workers'] == 2
    assert r['clean_shutdown'] is True and r['remaining_threads'] == 0
    assert r['origin_errors'] == []
    assert r['uploaded_bytes'] == len(payload())
    assert r['uploaded_sha256'] == hashlib.sha256(payload()).hexdigest()
    g = r['gate']
    assert not g.get('watchdog_fired')
    assert g['bytes'] == len(payload()) and '/files/' in g['path']
    assert r['uploaded_path'] == g['path']
    calls = r['calls']
    expected = {'initial', 'upload', 'upload-only', 'post-release', 'post-status'}
    assert set(calls) == expected
    for name, c in calls.items():
        assert c['id'] == name and 'error' not in c
        assert c['started'] <= c['sent'] <= c['finished']
        assert isinstance(c['result'], dict)
        expected_method = 'importmodel' if name == 'upload' else ('getmodelnetworkinfo' if name == 'post-status' else 'hello')
        assert c['method'] == expected_method
    assert calls['upload']['result']['cloud_uploaded'] is True
    assert calls['post-status']['result']['unix_workers'] == 2
    for n in ('initial', 'upload-only', 'post-release'):
        assert calls[n]['result']['suite'] == 'pq1'
    assert g['entered'] < calls['upload-only']['sent'] < g['released'] <= g['resumed'] <= calls['upload']['finished']
    assert HOLD_SECONDS <= g['released'] - calls['upload-only']['sent'] < GATE_SECONDS
    assert calls['post-release']['sent'] > max(calls['upload']['finished'], calls['upload-only']['finished'])
    assert calls['post-status']['sent'] > calls['post-release']['finished']
    if calls['upload-only']['finished'] < g['released']:
        return 'SHORT_CALL_COMPLETES_DURING_PAUSED_UPLOAD'
    return 'SHORT_CALL_WAITED_FOR_UPLOAD_RELEASE'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--helper', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True)
    a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=False)
    r = {'complete': False, 'scope': __doc__, 'helper_sha256': None}
    f = calls = origin = None
    start = time.monotonic()
    try:
        r['helper_sha256'] = hashlib.sha256(a.helper.read_bytes()).hexdigest()
        assert r['helper_sha256'] == HELPER_SHA
        with tempfile.TemporaryDirectory(prefix='s2-live-') as td:
            root = Path(td)
            source = root / 'model.safetensors'
            source.write_bytes(payload())
            f = Fixture(a.helper.resolve(), root, a.out)
            with PausedOrigin() as origin:
                with f.running():
                    creds = root / 'credentials'
                    creds.write_text('aws_access_key_id=TEST_KEY_NOT_REAL\naws_secret_access_key=TEST_SECRET_NOT_REAL\n')
                    creds.chmod(0o600)
                    cfg = {'endpoint': origin.endpoint, 'bucket': 'fixture', 'prefix': 'liveness',
                           'provider': 'GENERIC_S3', 'region': 'us-east-1', 'layout': 'SOURCE_FILES',
                           'credential_ref': str(creds), 'credential_ref_kind': 'path', 'use_fake': False,
                           'allow_http_loopback': True, 'automatic_spend_atoms': 0, 'idempotency_key': 'liveness'}
                    configured = f.ok('setcloudstorage', cfg)
                    assert configured['applied'] and configured['automatic_spend_atoms'] == 0
                    r['startup_info'] = f.ok('getmodelnetworkinfo')
                    assert r['startup_info']['helper_ready'] and r['startup_info']['pq1_ready']
                    r['unix_workers'] = r['startup_info']['unix_workers']
                    assert r['unix_workers'] == 2
                    calls = Calls(f.endpoint)
                    calls.call('initial', 'hello')
                    timer = None
                    try:
                        calls.start('upload', 'importmodel', str(source), {'pin': True, 'publish': False})
                        assert origin.entered.wait(5), 'origin never reached source PUT'
                        calls.start('upload-only', 'hello')
                        # Release independently of any helper reply. The first
                        # run proved waiting for this reply can outlast HTTP I/O.
                        timer = threading.Timer(HOLD_SECONDS + .05, origin.unblock)
                        timer.start()
                        calls.join()
                    finally:
                        origin.unblock()
                        if timer:
                            timer.cancel()
                            timer.join(1)
                            assert not timer.is_alive(), 'release timer did not stop'
                        calls.join()
                    calls.call('post-release', 'hello')
                    calls.call('post-status', 'getmodelnetworkinfo')
                    up = calls.rows['upload']['result']
                    files = up['cloud_files']
                    assert len(files) == 1 and files[0]['ok'] is True
                    key = '/fixture/' + files[0]['object_key'].lstrip('/')
                    assert up['artifact_id'] in key and key == origin.gate['path']
                    data = origin.object_bytes(key)
                    r.update(uploaded_path=key, uploaded_bytes=len(data), uploaded_sha256=hashlib.sha256(data).hexdigest())
                r['clean_shutdown'] = True
                r['origin'] = origin.snapshot()
                r['origin_errors'] = [q for q in r['origin']['requests'] if q.get('fixture_error') or q.get('response_status', 500) >= 400]
            r['complete'] = True
        r['calls'] = calls.rows
        r['gate'] = origin.gate
        r['remaining_threads'] = sum(t.is_alive() for t in calls.threads)
        r['verdict'] = validate(r)
    except Exception:
        r['complete'] = False
        r['error'] = traceback.format_exc()
        r['verdict'] = 'SETUP_OR_INCOMPLETE_OBSERVATION'
    finally:
        if calls: r['calls'] = calls.rows
        if origin:
            r['gate'] = origin.gate
            r['origin'] = origin.snapshot()
        if f:
            try: f.finish()
            except Exception:
                r['cleanup_error'] = traceback.format_exc()
                r['complete'] = False
                r['verdict'] = 'SETUP_OR_INCOMPLETE_OBSERVATION'
        r['seconds'] = time.monotonic() - start
        (a.out / 'result.json').write_text(json.dumps(r, indent=2)+'\n')
    print(json.dumps({'verdict': r['verdict'], 'seconds': r['seconds']}))
    return 1 if r['verdict'].startswith(('SETUP', 'INCONCLUSIVE')) else 0

if __name__ == '__main__':
    raise SystemExit(main())
