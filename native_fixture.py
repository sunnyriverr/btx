"""Bounded, observational import/save/retry/restart experiment for real modeld.

Prepared only: importing this module or --help does not start a helper.
No node, wallet, network peer, inference, or product source mutation is used.
See fixture-notes.md for source assumptions and interpretation.
"""
from pathlib import Path
import argparse
import hashlib
import json
import os
import shutil
import signal
import socket
import struct
import subprocess
import tempfile
import time
import traceback


BASE = 'dac9aee53520bd49ed320ec7a49b9072fc7d88d9'
AUTHOR_503 = '08fd0a6245598e8f9fedc6dac97629310335dd2d'
MAX_RPC_BYTES = 1024 * 1024


def sha_bytes(data):
    return hashlib.sha256(data).hexdigest()


def sha(path):
    return sha_bytes(path.read_bytes())


def require(ok, message):
    if not ok:
        raise RuntimeError(message)


def tiny_model(path, tag):
    # Exact TinySafeTensors / WriteTinyModel shape in modelnet_hosting_tests.
    header = ('{"__metadata__":{"t":"' + str(tag) + '"}}').encode()
    payload = struct.pack('<Q', len(header)) + header
    path.mkdir(parents=True)
    (path / 'model.safetensors').write_bytes(payload)
    return payload


class Helper:
    """Adapted from the delivered #495 real Linux Unix-socket fixture."""
    def __init__(self, binary, root, output, label):
        self.binary = binary.resolve()
        self.root, self.output, self.label = root, output, label
        self.store = root / 'modeldir'
        self.store.mkdir(parents=True)
        self.sock = root / 'rpc.sock'
        self.proc = self.log = None
        self.seq = self.starts = 0
        self.transcript, self.cleanup_signals = [], []

    def start(self):
        require(self.proc is None and not self.sock.exists(), 'owned helper not stopped')
        self.starts += 1
        self.log = (self.output / f'{self.label}-{self.starts}.log').open('wb')
        home = self.root / 'home'
        home.mkdir(exist_ok=True)
        args = [str(self.binary), '-modeldir=' + str(self.store),
                '-modelrpcsocket=' + str(self.sock), '-modelstorage=8MiB',
                '-modellandiscovery=0', '-modelfollowpeers=0', '-modelnatpmp=0',
                '-modelhost=0', '-modelseed=off', '-pwcchain=regtest']
        self.proc = subprocess.Popen(args, stdout=self.log, stderr=subprocess.STDOUT,
            start_new_session=True, env=dict(os.environ, HOME=str(home),
                XDG_DATA_HOME=str(home / 'data'), XDG_RUNTIME_DIR=str(self.root)))
        until = time.monotonic() + 30
        while not self.sock.exists():
            require(self.proc.poll() is None and time.monotonic() < until,
                    'helper startup failed or exceeded 30s')
            time.sleep(.1)
        require(Path(f'/proc/{self.proc.pid}/exe').resolve() == self.binary,
                'Linux process does not use the pinned binary')
        info = self.ok('getmodelnetworkinfo', [])
        require(info['follow_configured_peers'] is False, 'peer following enabled')

    def rpc(self, method, params):
        self.seq += 1
        request = {'jsonrpc': '1.0', 'id': self.seq, 'method': method, 'params': params}
        with socket.socket(socket.AF_UNIX) as client:
            client.settimeout(10)
            client.connect(str(self.sock))
            client.sendall(json.dumps(request).encode() + b'\n')
            client.shutdown(socket.SHUT_WR)
            with client.makefile('rb') as stream:
                raw = stream.read(MAX_RPC_BYTES + 1)
        require(len(raw) <= MAX_RPC_BYTES, 'RPC response exceeded fixture bound')
        response = json.loads(raw)
        require(response['id'] == self.seq, 'RPC id mismatch')
        self.transcript.append({'at': time.time(), 'request': request, 'response': response})
        return response

    def ok(self, method, params):
        answer = self.rpc(method, params)
        require(answer.get('error') is None, f'{method} legitimate control failed: {answer}')
        return answer['result']

    def stop(self):
        if self.proc is None:
            return
        require(self.proc.poll() is None, 'helper exited unexpectedly')
        self.proc.send_signal(signal.SIGTERM)
        self.proc.wait(timeout=25)
        require(self.proc.returncode == 0 and not self.sock.exists(),
                'helper shutdown was not clean')
        self.proc = None
        self.log.close()
        self.log = None

    def cleanup(self):
        try:
            self.stop()
        finally:
            if self.proc is not None and self.proc.poll() is None:
                self.cleanup_signals.append('SIGKILL')
                os.killpg(self.proc.pid, signal.SIGKILL)
                self.proc.wait(timeout=10)
            if self.log:
                self.log.close()
            require(self.proc is None or self.proc.poll() is not None, 'owned process left alive')
            shutil.rmtree(self.root)


def imported(result):
    return {'model_id': result['model_id'], 'artifact_id': result['artifact_id']}


def disk(helper):
    path = helper.store / 'catalog.json'
    if not path.exists():
        return {'exists': False, 'models': []}
    raw = path.read_bytes()
    obj = json.loads(raw)
    return {'exists': True, 'sha256': sha_bytes(raw), 'models': obj['models'],
            'peers': obj.get('peers', [])}


def artifacts(helper):
    root = helper.store / 'store' / 'artifacts'
    result = {}
    if root.exists():
        for directory in sorted(root.iterdir()):
            if directory.is_dir():
                result[directory.name] = {
                    str(p.relative_to(directory)): {'bytes': p.stat().st_size, 'sha256': sha(p)}
                    for p in sorted(directory.rglob('*')) if p.is_file()}
    return result


def snapshot(helper, name, record, live=True):
    # Capture both sides of listmodels: do not assume observation cannot heal.
    before = disk(helper)
    value = {'catalog_before_list': before, 'artifacts': artifacts(helper)}
    if live:
        value['listmodels'] = helper.ok('listmodels', [])
    value['catalog_after_list'] = disk(helper)
    value['list_changed_catalog'] = before != value['catalog_after_list']
    record['snapshots'][name] = value
    return value


def ids(rows):
    return {row['model_id'] for row in rows}


def exact_entries(rows, expected):
    return len(rows) == len(expected) and ids(rows) == {v['model_id'] for v in expected}


def byte_controls(helper, expected, payloads, record):
    controls = {}
    for name, entry in expected.items():
        piece = (helper.store / 'store' / 'artifacts' / entry['artifact_id'] / '0' / '0.piece')
        piece_ok = piece.is_file() and piece.read_bytes() == payloads[name]
        answer = helper.rpc('exportmodelpath', [entry['model_id']])
        export_ok = False
        if answer.get('error') is None:
            checkout = Path(answer['result']['path']).resolve()
            require(checkout.is_relative_to(helper.root.resolve()), 'checkout escaped disposable root')
            file = checkout / 'model.safetensors'
            export_ok = file.is_file() and file.read_bytes() == payloads[name]
        controls[name] = {'committed_piece_matches': piece_ok,
                          'export_response': answer, 'export_matches': export_ok}
    record['byte_controls'] = controls
    return all(v['committed_piece_matches'] and v['export_matches'] for v in controls.values())


def run_journey(binary, output, label, fault, expected=None):
    root = Path(tempfile.mkdtemp(prefix='import-recovery-'))
    helper = Helper(binary, root, output, label)
    record = {'snapshots': {}, 'fault': fault, 'binary_sha256': sha(binary)}
    blocker = helper.store / 'catalog.json.tmp'
    try:
        payloads = {name: tiny_model(root / 'inputs' / name, tag)
                    for name, tag in [('a', 11), ('b', 22)]}
        record['input_sha256'] = {name: sha_bytes(data) for name, data in payloads.items()}
        helper.start()
        require(helper.ok('listmodels', [])['models'] == [], 'fresh catalog not empty')
        opts = {'pin': True, 'publish': False}
        a = imported(helper.ok('importmodel', [str(root / 'inputs' / 'a'), opts]))
        record['preexisting_entry'] = a
        first = snapshot(helper, 'preexisting', record)
        require(exact_entries(first['listmodels']['models'], [a]), 'preexisting live entry wrong')
        require(exact_entries(first['catalog_after_list']['models'], [a]), 'preexisting disk entry wrong')
        if expected is not None:
            require(a == expected['a'], 'fixture A identity differs from healthy control')
        require(not blocker.exists(), 'catalog temp path unexpectedly occupied')
        if fault:
            # Nonempty obstruction cannot be removed by a writer's remove(tmp).
            # Only this disposable catalog temp path is affected, never payload storage.
            blocker.mkdir()
            (blocker / 'fixture-obstruction').write_text('owned catalog-save obstruction\n')
            record['obstruction'] = str(blocker)
        first_b = helper.rpc('importmodel', [str(root / 'inputs' / 'b'), opts])
        record['first_b_reply'] = first_b
        after_first = snapshot(helper, 'after_first_b', record)
        if fault:
            # Remove only our marker/directory; do not alter product artifacts/catalog.
            require((blocker / 'fixture-obstruction').is_file(), 'obstruction changed unexpectedly')
            (blocker / 'fixture-obstruction').unlink()
            blocker.rmdir()
            record['obstruction_removed_before_retry'] = True
            error_text = json.dumps(first_b.get('error'))
            record['catalog_save_fault_reached'] = (first_b.get('error') is not None
                                                   and 'catalog write failed' in error_text)
            require(record['catalog_save_fault_reached'],
                    'first failure did not establish the intended catalog-write boundary')
            require(after_first['catalog_after_list']['sha256'] == first['catalog_after_list']['sha256'],
                    'failed write changed previous catalog bytes')
            require(a['model_id'] in ids(after_first['listmodels']['models']), 'previous entry lost live')
            b = expected['b']
            record['artifact_present_after_failed_save'] = b['artifact_id'] in after_first['artifacts']
            retry = helper.rpc('importmodel', [str(root / 'inputs' / 'b'), opts])
            record['same_process_retry_reply'] = retry
        else:
            require(first_b.get('error') is None, 'ordinary model B import failed')
            b = imported(first_b['result'])
            retry = first_b
        require(a['model_id'] != b['model_id'] and a['artifact_id'] != b['artifact_id'],
                'tiny fixtures did not create distinct content identities')
        record['expected_entries'] = {'a': a, 'b': b}
        before_stop = snapshot(helper, 'before_clean_stop', record)
        # No corrective catalog call follows the retry. Allow ordinary background work.
        time.sleep(2)
        snapshot(helper, 'after_two_second_grace', record, live=False)
        helper.stop()
        stopped = snapshot(helper, 'after_clean_stop', record, live=False)
        helper.start()
        restarted = snapshot(helper, 'after_restart', record)
        record['shutdown_changed_catalog'] = (stopped['catalog_after_list'] !=
            record['snapshots']['after_two_second_grace']['catalog_after_list'])
        record['restart_changed_catalog'] = (restarted['catalog_before_list'] != stopped['catalog_after_list'])
        record['retry_acknowledged'] = retry.get('error') is None
        record['retry_returns_expected_entry'] = (record['retry_acknowledged']
            and imported(retry['result']) == b)
        record['retry_durable_before_stop'] = exact_entries(before_stop['catalog_after_list']['models'], [a, b])
        record['restart_has_exact_two_live'] = exact_entries(restarted['listmodels']['models'], [a, b])
        record['restart_has_exact_two_disk'] = exact_entries(restarted['catalog_after_list']['models'], [a, b])
        record['preexisting_entry_retained'] = (a['model_id'] in ids(restarted['listmodels']['models'])
            and a['model_id'] in ids(restarted['catalog_after_list']['models']))
        original_a = first['catalog_after_list']['models'][0]
        restored_a = [row for row in restarted['catalog_after_list']['models']
                      if row['model_id'] == a['model_id']]
        record['preexisting_catalog_entry_unchanged'] = restored_a == [original_a]
        # Characterize normal user recovery after recording restart state, even if B is absent.
        post = helper.rpc('importmodel', [str(root / 'inputs' / 'b'), opts])
        record['postrestart_import_reply'] = post
        snapshot(helper, 'after_postrestart_import', record)
        record['postrestart_import_succeeds'] = post.get('error') is None
        record['postrestart_import_returns_expected_entry'] = (record['postrestart_import_succeeds']
            and imported(post['result']) == b)
        record['both_model_bytes_usable'] = byte_controls(helper, {'a': a, 'b': b}, payloads, record)
        helper.stop()
        record['clean_shutdown'] = True
        required = ['retry_acknowledged', 'retry_returns_expected_entry', 'retry_durable_before_stop',
                    'restart_has_exact_two_live', 'restart_has_exact_two_disk',
                    'preexisting_entry_retained', 'preexisting_catalog_entry_unchanged',
                    'postrestart_import_succeeds', 'postrestart_import_returns_expected_entry',
                    'both_model_bytes_usable', 'clean_shutdown']
        record['acceptance_pass'] = all(record[k] for k in required)
        record['failed_acceptance'] = [k for k in required if not record[k]]
        record['observed_lost_acknowledged_import'] = (record['retry_acknowledged']
            and not record['restart_has_exact_two_live'])
        record['observed_orphan_retry_failure'] = (post.get('error') is not None
            and 'destination artifact exists' in json.dumps(post['error']))
    except Exception as error:
        record.update(experiment_error=repr(error), traceback=traceback.format_exc(), acceptance_pass=False)
    finally:
        try:
            if blocker.is_dir() and (blocker / 'fixture-obstruction').is_file():
                (blocker / 'fixture-obstruction').unlink()
                blocker.rmdir()
            helper.cleanup()
        except Exception as error:
            record['cleanup_error'] = repr(error)
        record.update(transcript=helper.transcript, cleanup_signals=helper.cleanup_signals,
                      owned_runtime_removed=not root.exists())
        (output / (label + '-result.json')).write_text(json.dumps(record, indent=2) + '\n')
    return record


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--binary', type=Path, required=True)
    parser.add_argument('--expected-sha256', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    binary = args.binary.resolve(strict=True)
    require(sha(binary) == args.expected_sha256, 'binary digest mismatch')
    require(os.access(binary, os.X_OK), 'binary not executable')
    output = args.output.resolve()
    require(not output.exists() or not any(output.iterdir()), 'output must be new or empty')
    output.mkdir(parents=True, exist_ok=True)
    def interrupted(signum, frame):
        raise TimeoutError('bounded owned experiment interrupted')
    signal.signal(signal.SIGTERM, interrupted)
    signal.signal(signal.SIGALRM, interrupted)
    signal.alarm(240)
    result = {'profile': 'native Linux, real helper Unix RPC, disposable 8MiB storage',
              'source_assumption': {'base': BASE, 'author503': AUTHOR_503,
                                    'binary_source_identity_requires_build_receipt': True},
              'fixture_sha256': sha(Path(__file__)), 'binary_sha256': sha(binary)}
    try:
        control = run_journey(binary, output, 'healthy', False)
        result['healthy'] = control
        if (control.get('acceptance_pass') and control.get('owned_runtime_removed')
                and not control.get('cleanup_signals') and not control.get('cleanup_error')):
            result['fault'] = run_journey(binary, output, 'catalog-save-fault', True,
                                          control['expected_entries'])
        else:
            result['fault_not_started'] = 'legitimate control did not pass and clean up'
        result['experiment_complete'] = ('fault' in result
            and not result['fault'].get('experiment_error')
            and result['fault'].get('owned_runtime_removed')
            and not result['fault'].get('cleanup_error')
            and not result['fault'].get('cleanup_signals'))
        result['recovery_acceptance_pass'] = bool(result['experiment_complete']
                                                and result['fault']['acceptance_pass'])
        (output / 'summary.json').write_text(json.dumps(result, indent=2) + '\n')
        # A characterized product failure remains evidence, not a fixture crash.
        return 0 if result['experiment_complete'] else 2
    finally:
        signal.alarm(0)


if __name__ == '__main__':
    raise SystemExit(main())
