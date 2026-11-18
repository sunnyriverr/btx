"""Offline driver/collector tests only: synthetic records and local Python doubles."""
import copy
import io
import json
import threading
import time
import unittest
from unittest.mock import patch
import observe as o


def record(responsive=False):
    calls = {}
    times = {'initial': (0, .1, .2), 'upload': (.3, .4, 8),
             'upload-only': (2, 2.1, 2.2), 'status': (3, 3.1, 7.5),
             'probe': (3.2, 3.3, 3.4 if responsive else 7.6),
             'post-release': (9, 9.1, 9.2), 'post-status': (10, 10.1, 10.2)}
    for n, (start, sent, end) in times.items():
        method = 'importmodel' if n == 'upload' else ('getmodelnetworkinfo' if n in ('status', 'post-status') else 'hello')
        result = {'cloud_uploaded': True} if n == 'upload' else ({'unix_workers': 2} if method == 'getmodelnetworkinfo' else {'suite': 'pq1'})
        calls[n] = {'id': n, 'method': method, 'started': start, 'sent': sent, 'finished': end, 'result': result}
    return {'complete': True, 'helper_sha256': o.HELPER_SHA, 'unix_workers': 2,
            'clean_shutdown': True, 'remaining_threads': 0, 'origin_errors': [],
            'uploaded_path': '/fixture/a/files/model', 'uploaded_bytes': len(o.payload()), 'uploaded_sha256': o.hashlib.sha256(o.payload()).hexdigest(),
            'gate': {'path': '/fixture/a/files/model', 'bytes': len(o.payload()), 'entered': 1,
                     'released': 7, 'resumed': 7.1}, 'calls': calls}


class Offline(unittest.TestCase):
    def test_coupled(self):
        self.assertEqual(o.validate(record()), 'SHORT_CALLS_COMPLETE_AFTER_ORIGIN_RELEASE')

    def test_responsive(self):
        self.assertEqual(o.validate(record(True)), 'SHORT_CALL_COMPLETES_BEFORE_ORIGIN_RELEASE')

    def test_status_completed_early_is_inconclusive(self):
        r = record(); r['calls']['status']['finished'] = 3.2
        self.assertTrue(o.validate(r).startswith('INCONCLUSIVE'))

    def test_status_returned_before_probe_does_not_overclaim_overlap(self):
        r = record(True); r['calls']['status']['finished'] = 3.2
        self.assertEqual(o.validate(r), 'SHORT_CALL_COMPLETES_BEFORE_ORIGIN_RELEASE')

    def test_negative_records_rejected(self):
        mutations = [lambda r: r.update(complete=False),
                     lambda r: r.update(helper_sha256='wrong'),
                     lambda r: r.update(unix_workers=3),
                     lambda r: r.update(clean_shutdown=False),
                     lambda r: r.update(remaining_threads=1),
                     lambda r: r.update(origin_errors=['error']),
                     lambda r: r.update(uploaded_sha256='wrong'),
                     lambda r: r['calls'].pop('probe'),
                     lambda r: r['calls']['probe'].update(error='timeout'),
                     lambda r: r['calls']['probe'].pop('finished'),
                     lambda r: r['calls']['upload']['result'].update(cloud_uploaded=False),
                     lambda r: r['gate'].update(watchdog_fired=True),
                     lambda r: r['gate'].update(bytes=0),
                     lambda r: r['gate'].update(released=3.4),
                     lambda r: r['calls']['upload-only'].update(finished=7.5),
                     lambda r: r['calls']['probe'].update(id='wrong'),
                     lambda r: r['calls']['post-status']['result'].update(unix_workers=3)]
        for mutation in mutations:
            with self.subTest(mutation=mutations.index(mutation)):
                r = record(); mutation(r)
                with self.assertRaises((AssertionError, KeyError)): o.validate(r)

    def test_payload_is_valid_header(self):
        b = o.payload(); n = o.struct.unpack('<Q', b[:8])[0]
        h = json.loads(b[8:8+n]); self.assertEqual(h['w']['data_offsets'], [0, len(b)-8-n])

    def test_reused_fixture_constructs_without_helper(self):
        from pathlib import Path
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            f = o.Fixture(Path('/not-executed'), Path(td), Path(td))
            self.assertEqual(f.starts, 0)
            self.assertTrue(f.model.is_dir())

    def test_gate_blocks_then_releases_and_preserves_bytes(self):
        origin = o.PausedOrigin()
        handler = object.__new__(origin._handler()); handler.command = 'PUT'
        answer = []
        t = threading.Thread(target=lambda: answer.append(handler._dispatch('/fixture/x/files/m', {}, o.payload())))
        t.start(); self.assertTrue(origin.entered.wait(1)); self.assertTrue(t.is_alive())
        origin.unblock(); t.join(1); self.assertFalse(t.is_alive())
        self.assertEqual(answer[0][0], 200)
        self.assertEqual(origin.object_bytes('/fixture/x/files/m'), o.payload())
        self.assertFalse(origin.gate.get('watchdog_fired', False))

    def test_gate_timeout_is_not_product_failure(self):
        origin = o.PausedOrigin()
        handler = object.__new__(origin._handler()); handler.command = 'PUT'
        with patch.object(o, 'GATE_SECONDS', .001):
            answer = handler._dispatch('/fixture/x/files/m', {}, b'x')
        self.assertEqual(answer[0], 503)
        self.assertTrue(origin.gate['watchdog_fired'])

    def test_rpc_records_match_id_and_propagate_errors(self):
        class Conn:
            reply = b''
            def __enter__(self): return self
            def __exit__(self, *a): pass
            def settimeout(self, n): self.timeout = n
            def connect(self, p): pass
            def sendall(self, b): self.sent = json.loads(b)
            def shutdown(self, n): pass
            def makefile(self, mode): return io.BytesIO(self.reply)
        for reply, accepted in [({'id': 'x', 'error': None, 'result': {'suite': 'pq1'}}, True),
                                ({'id': 'wrong', 'error': None, 'result': {}}, False),
                                ({'id': 'x', 'error': {'code': 'BUSY'}, 'result': None}, False)]:
            conn = Conn(); conn.reply = json.dumps(reply).encode()+b'\n'
            c = o.Calls('/unused')
            with patch.object(o.socket, 'socket', return_value=conn):
                if accepted: self.assertEqual(c.call('x', 'hello')['suite'], 'pq1')
                else:
                    with self.assertRaises(AssertionError): c.call('x', 'hello')
                    self.assertIn('error', c.rows['x'])
                    self.assertIn('raw_reply', c.rows['x'])
            self.assertEqual(conn.sent['id'], 'x')
            self.assertEqual(conn.timeout, o.RPC_SECONDS)

    def test_missing_binary_retains_failure_record(self):
        from pathlib import Path
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / 'records'
            with patch('sys.argv', ['observe.py', '--helper', str(Path(td)/'missing'), '--out', str(out)]):
                self.assertEqual(o.main(), 1)
            r = json.loads((out/'result.json').read_text())
            self.assertFalse(r['complete'])
            self.assertIn('FileNotFoundError', r['error'])
            self.assertEqual(r['verdict'], 'SETUP_OR_INCOMPLETE_OBSERVATION')

if __name__ == '__main__': unittest.main(verbosity=2)
