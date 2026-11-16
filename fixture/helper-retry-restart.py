"""Bounded native helper settings qualification; no wallet/node/peers or queued action execution.

Baseline records expected product defects while keeping setup/valid controls strict.
Candidate requires every contract check to pass. All roots are disposable.
"""
import argparse
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import socket
import subprocess
import tempfile
import time
from uuid import uuid4


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class Fixture:
    def __init__(self, binary, root, out):
        self.binary, self.root, self.out = binary, root, out
        self.endpoint = root / 'rpc.sock'
        self.model = root / 'model'
        self.model.mkdir()
        self.calls = []
        self.starts = 0

    def rpc(self, method, *params):
        payload = {'id': 'settings-qualification', 'method': method, 'params': list(params)}
        with socket.socket(socket.AF_UNIX) as conn:
            conn.settimeout(10)
            conn.connect(str(self.endpoint))
            conn.sendall(json.dumps(payload).encode() + b'\n')
            conn.shutdown(socket.SHUT_WR)
            with conn.makefile('rb') as wire:
                line = wire.readline(2 * 1024 * 1024)
            assert line.endswith(b'\n'), 'missing/oversized RPC reply'
            reply = json.loads(line)
        self.calls.append({'method': method, 'params': list(params), 'reply': reply})
        return reply

    def ok(self, method, *params):
        reply = self.rpc(method, *params)
        assert reply.get('error') is None, reply
        return reply['result']

    def watches(self):
        return self.ok('listmodelwatches')['watches']

    def peek(self):
        row = self.ok('getmodelwatchactions', {'drain': False})
        assert row['drained'] is False and row['executed_free_downloads'] is False, row
        assert row['automatic_spend_atoms'] == 0 and row['actions'] == [], row
        return row

    @contextmanager
    def running(self):
        self.starts += 1
        env = {k: v for k, v in os.environ.items()
               if not k.startswith(('BTX_', 'DYLD_', 'BITCOIN_'))}
        if os.environ.get('BTX_OPENSSL'):
            env['BTX_OPENSSL'] = os.environ['BTX_OPENSSL']
        logpath = self.out / f'helper-start-{self.starts}.log'
        with logpath.open('wb') as log:
            proc = subprocess.Popen([
                str(self.binary), f'-modeldir={self.model}',
                f'-modelrpcsocket={self.endpoint}', '-modelstorage=8MiB',
                '-modellandiscovery=0', '-modelnatpmp=0', '-modelfollowpeers=0',
                '-modelseed=off', '-modelpreserverare=0', '-modeluploadlimit=1KiB',
            ], cwd=self.root, env=env, stdout=log, stderr=subprocess.STDOUT)
            try:
                deadline = time.monotonic() + 30
                while True:
                    assert proc.poll() is None, logpath.read_text(errors='replace')[-6000:]
                    try:
                        self.ok('listmodelwatches')
                        break
                    except (FileNotFoundError, ConnectionRefusedError):
                        if time.monotonic() >= deadline:
                            raise
                        time.sleep(.05)
                yield
                assert proc.poll() is None, logpath.read_text(errors='replace')[-6000:]
            finally:
                if proc.poll() is None:
                    proc.terminate()
                    try:
                        proc.wait(timeout=15)
                    except subprocess.TimeoutExpired:
                        proc.kill()
                        proc.wait(timeout=5)
                        raise AssertionError('helper exceeded clean shutdown bound')
                assert proc.returncode == 0, (proc.returncode, logpath.read_text(errors='replace')[-6000:])

    def finish(self):
        (self.out / 'calls.json').write_text(json.dumps(self.calls, indent=2) + '\n')


def watch_creation(f):
    with f.running():
        other = f.ok('watchmodel', {'model_id': 'c' * 96, 'action': 'NOTIFY'})
        old = (f.model / 'watches.json').read_bytes()
        block = f.model / 'watches.json.tmp'
        block.mkdir()
        wanted = {'model_id': 'a' * 96, 'action': 'NOTIFY'}
        failed = f.rpc('watchmodel', wanted)
        assert failed['error'] is not None and failed['error']['code'] == 'INVALID_PARAMETER', failed
        assert (f.model / 'watches.json').read_bytes() == old
        live = f.watches()
        checks = {'rejected_creation_absent_live': [x['model_id'] for x in live] == ['c' * 96]}
        assert any(x['watch_id'] == other['watch_id'] for x in live)
        f.peek()
        block.rmdir()
        retry = f.ok('watchmodel', wanted)
        assert retry['model_id'] == wanted['model_id']
        post = f.watches()
        checks['identical_retry_has_one_target'] = sum(x['model_id'] == wanted['model_id'] for x in post) == 1
        f.peek()
    with f.running():
        post_restart = f.watches()
        checks['healthy_retry_survives_restart_once'] = sum(x['model_id'] == wanted['model_id'] for x in post_restart) == 1
        assert any(x['watch_id'] == other['watch_id'] for x in post_restart)
        f.peek()
    return checks


def watch_replacement(f):
    # Only setmodelmirror exposes deterministic PutWatch replacement through RPC.
    selector = {'publisher_id': 'b' * 96}
    with f.running():
        first = f.ok('setmodelmirror', {**selector, 'keep_latest': 1, 'idempotency_key': uuid4().hex})
        target = first['watch_id']
        other = f.ok('watchmodel', {'model_id': 'c' * 96, 'action': 'NOTIFY'})
        old = (f.model / 'watches.json').read_bytes()
        block = f.model / 'watches.json.tmp'
        block.mkdir()
        wanted = {**selector, 'keep_latest': 2, 'idempotency_key': uuid4().hex}
        failed = f.rpc('setmodelmirror', wanted)
        assert failed['error'] is not None and failed['error']['code'] == 'IO_ERROR', failed
        assert (f.model / 'watches.json').read_bytes() == old
        got = f.ok('getmodelwatch', {'watch_id': target})
        checks = {'rejected_replacement_keeps_previous_live': got['keep_n'] == 1}
        assert any(x['watch_id'] == other['watch_id'] for x in f.watches())
        f.peek()
        block.rmdir()
        # Existing network02 semantics cache unsuccessful idempotency-key outcomes.
        replay = f.rpc('setmodelmirror', wanted)
        assert replay == failed, 'same-key error replay contract changed'
        retry = f.ok('setmodelmirror', {**wanted, 'idempotency_key': uuid4().hex})
        assert retry['watch_id'] == target and retry['keep_latest'] == 2
        assert f.ok('getmodelwatch', {'watch_id': target})['keep_n'] == 2
        f.peek()
    with f.running():
        assert f.ok('getmodelwatch', {'watch_id': target})['keep_n'] == 2
        assert any(x['watch_id'] == other['watch_id'] for x in f.watches())
        f.peek()
    checks['healthy_fresh_key_retry_survives_restart'] = True
    return checks


def channel(f, records, replacing):
    prior, wanted, other = (records[x] for x in ('target_1', 'target_2', 'unrelated_1'))
    key = {k: wanted[k] for k in ('publisher_id', 'name', 'channel')}
    def events():
        return [x for x in f.ok('getmodelevents', {'cursor': 0, 'limit': 100})['events']
                if x['event_type'] == 'CHANNEL_UPDATED']
    with f.running():
        f.ok('observemodelchannel', other)
        if replacing:
            f.ok('observemodelchannel', prior)
        old = (f.model / 'channels.json').read_bytes()
        before = events()
        assert len(before) == (2 if replacing else 1), before
        block = f.model / 'channels.json.tmp'
        block.mkdir()
        failed = f.rpc('observemodelchannel', wanted)
        assert failed['error'] is not None and failed['error']['code'] == 'REJECTED', failed
        assert (f.model / 'channels.json').read_bytes() == old
        assert events() == before, 'rejected save emitted an event'
        got = f.rpc('getmodelchannel', key)
        if replacing:
            checks = {'rejected_sequence_keeps_previous_live': got['error'] is None and got['result']['sequence'] == 1}
        else:
            checks = {'rejected_creation_absent_live': got['error'] is not None and got['error']['code'] == 'NOT_FOUND'}
        f.peek()
        block.rmdir()
        retried = f.rpc('observemodelchannel', wanted)
        checks['identical_signed_retry_accepted_without_restart'] = retried['error'] is None
        after = events()
        checks['healthy_retry_emits_exactly_one_update'] = len(after) == len(before) + 1
        if retried['error'] is None:
            assert after[-1]['record_sequence'] == wanted['sequence']
            assert after[-1]['new_state'] == wanted['target_uri']
            # Real persisted duplicates and decreasing sequences stay rejected.
            assert f.rpc('observemodelchannel', wanted)['error'] is not None
            assert f.rpc('observemodelchannel', prior)['error'] is not None
            assert events() == after
        unrelated = f.ok('getmodelchannel', {k: other[k] for k in ('publisher_id', 'name', 'channel')})
        assert unrelated['sequence'] == 1 and unrelated['target_uri'] == other['target_uri']
    with f.running():
        got = f.rpc('getmodelchannel', key)
        checks['healthy_retry_survives_restart'] = got['error'] is None and got['result']['sequence'] == 2 and got['result']['target_uri'] == wanted['target_uri']
        durable = events()
        checks['retry_event_survives_restart'] = len(durable) == len(before) + 1
        unrelated = f.ok('getmodelchannel', {k: other[k] for k in ('publisher_id', 'name', 'channel')})
        assert unrelated['sequence'] == 1
        f.peek()
    return checks


def policy(f):
    with f.running():
        initial = f.ok('setmodelpolicy', {'seed': 'off', 'preserve_rare': False,
                                       'follow_configured_peers': False, 'upload_bps': 1024})
        old = (f.model / 'policy.json').read_bytes()
        block = f.model / 'policy.json.tmp'
        block.mkdir()
        wanted = {'preserve_rare': True}
        failed = f.rpc('setmodelpolicy', wanted)
        assert failed['error'] is not None and failed['error']['code'] == 'IO', failed
        assert (f.model / 'policy.json').read_bytes() == old
        after = f.ok('getmodelpolicy')
        checks = {'rejected_policy_keeps_previous_live': after == initial}
        for k, value in initial.items():
            if k not in {'preserve_rare', 'preservation_propagation'}:
                assert after[k] == value, (k, after[k], value)
        block.rmdir()
        retried = f.ok('setmodelpolicy', wanted)
        assert retried['preserve_rare'] is True
        saved = json.loads((f.model / 'policy.json').read_text())
        assert saved['preserve_rare'] is True and saved['upload_bps'] == 1024
        for bad in ({'auto_pay': True}, {'automatic_spend_atoms': 1}):
            assert f.rpc('setmodelpolicy', bad)['error'] is not None
            assert f.ok('getmodelpolicy') == retried
        f.peek()
    # Startup intentionally reapplies launch settings and rewrites policy.json.
    with f.running():
        restarted = f.ok('getmodelpolicy')
        assert restarted['preserve_rare'] is False and restarted['seed'] == 'off'
        assert restarted['follow_configured_peers'] is False
        assert json.loads((f.model / 'policy.json').read_text())['preserve_rare'] is False
        recovered = f.ok('setmodelpolicy', wanted)
        assert recovered['preserve_rare'] is True
        f.peek()
    checks['retry_durable_before_shutdown'] = True
    checks['documented_launch_reset_and_reapply_work'] = True
    return checks


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--helper', type=Path, required=True)
    ap.add_argument('--channel-fixture', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--expect', choices=('baseline', 'candidate'), required=True)
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    records = json.loads(args.channel_fixture.read_text())
    assert all(records[k].get('signature') and records[k].get('pubkey') for k in ('target_1','target_2','unrelated_1'))
    binary = args.helper.resolve()
    report = {'helper_sha256': sha(binary), 'channel_fixture_sha256': sha(args.channel_fixture),
              'expect': args.expect, 'cases': {}, 'scope': 'native helper/private Unix RPC and real files/signatures; no node/wallet/peers/action execution'}
    started = time.monotonic()
    try:
        with tempfile.TemporaryDirectory(prefix='msettings-', dir='/tmp') as temp:
            root = Path(temp)
            for name, action in [('watch_creation', watch_creation), ('watch_replacement_via_mirror', watch_replacement),
                                 ('channel_creation', lambda f: channel(f, records, False)),
                                 ('channel_replacement', lambda f: channel(f, records, True)), ('policy', policy)]:
                assert time.monotonic() - started < 180, 'fixture total-runtime bound exceeded'
                case_out = args.out / name
                case_out.mkdir()
                case_root = root / name
                case_root.mkdir()
                fixture = Fixture(binary, case_root, case_out)
                try:
                    checks = action(fixture)
                    report['cases'][name] = {'checks': checks, 'contract_pass': all(checks.values()), 'helper_clean_starts': fixture.starts}
                finally:
                    fixture.finish()
            report['scratch_removed'] = True
        contracts = [x['contract_pass'] for x in report['cases'].values()]
        report['expected_observation'] = all(contracts) if args.expect == 'candidate' else not any(contracts)
        report['complete'] = True
    except Exception as exc:
        report['error'] = repr(exc)
        report['complete'] = False
        report['expected_observation'] = False
    finally:
        report['seconds'] = time.monotonic() - started
        (args.out / 'native-result.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))
    return 0 if report['complete'] and report['expected_observation'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
