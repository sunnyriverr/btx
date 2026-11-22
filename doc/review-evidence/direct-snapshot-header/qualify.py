import contextlib
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
from unittest.mock import patch

root = Path(__file__).resolve().parent
fixture_path = root / 'source/test/util/btx_faststart_test.py'
spec = importlib.util.spec_from_file_location('existing_fixture', fixture_path)
fixture = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fixture)
snapshot = root / 'snapshot.dat'
digest = '45392da4550a66ccd4ed949cc0e47cb2197dbf2fd238f79367c921adf8508890'
base = '0104909051a017c9045faf7382627e89c5b83c4bbd3c1270706d5d2ef2ab0c87'
height = 228000
assert hashlib.sha256(snapshot.read_bytes()).hexdigest() == digest

def run(route, header_at, *, checksum=digest, stalled=False, payload=snapshot):
    module = fixture.load_module()
    elapsed = 0
    loaded_at = None
    events = []

    def sleep(seconds):
        nonlocal elapsed
        elapsed += seconds
        assert elapsed <= 20, 'Fixture exceeded simulated time limit'

    def call(cmd, **kwargs):
        nonlocal loaded_at
        method, *args = [part for part in cmd[1:] if not part.startswith('-')]
        available = elapsed >= header_at
        events.append(dict(method=method, seconds=elapsed, base_known=available))
        if method == 'getblockheader':
            assert args == [base]
            if stalled:
                timeout = kwargs['timeout']
                assert 0 < timeout <= 10
                sleep(timeout)
                raise subprocess.TimeoutExpired(cmd, timeout)
            return subprocess.CompletedProcess(cmd, 0 if available else 1)
        if method == 'getblockhash':
            assert args == [str(height)]
            return subprocess.CompletedProcess(cmd, 1, stdout='')
        if method == 'getblockcount':
            return subprocess.CompletedProcess(cmd, 0, stdout='0')
        if method == 'getblockchaininfo':
            reply = {'headers': height if available else height - 1, 'blocks': 0}
        elif method == 'loadtxoutset':
            assert hashlib.sha256(Path(args[0]).read_bytes()).hexdigest() == digest
            if not available:
                raise subprocess.CalledProcessError(1, cmd, output=(
                    f'The base block header ({base}) must appear in the headers chain. '
                    'Make sure all headers are syncing, and call loadtxoutset again'))
            assert loaded_at is None
            loaded_at = elapsed
            reply = {'base_height': height}
        elif method == 'getchainstates':
            assert loaded_at is not None
            states = [{'blocks': height, 'validated': True}]
            if elapsed == loaded_at:
                states = [{'blocks': 0}, {'blocks': height, 'snapshot_blockhash': base}]
            reply = {'chainstates': states}
        else:
            raise AssertionError(f'Unexpected CLI call: {method}')
        return json.dumps(reply)

    with tempfile.TemporaryDirectory(prefix='btx-faststart-test-') as temp:
        d = Path(temp)
        manifest = d / 'manifest.json'
        manifest.write_text(json.dumps({'main': {'url': payload.as_uri(),
                                                  'sha256': digest, 'height': height,
                                                  'blockhash': base}}))
        options = ([f'--snapshot-manifest={manifest}'] if route == 'manifest'
                   else [f'--snapshot-url={payload.as_uri()}', f'--snapshot-sha256={checksum}'])
        output = io.StringIO()
        with patch.object(module, 'time', SimpleNamespace(time=lambda: elapsed, monotonic=lambda: elapsed, sleep=sleep)), \
             patch.object(module.subprocess, 'run', side_effect=call), \
             patch.object(module.subprocess, 'check_output', side_effect=call), \
             contextlib.redirect_stdout(output):
            try:
                rc = module.main(['service', '--chain=main', f'--datadir={d / "node"}',
                                  '--no-start-daemon', '--header-wait-secs=10',
                                  '--poll-secs=1', *options])
                error = None
            except (RuntimeError, ValueError, TimeoutError) as exc:
                rc, error = 1, str(exc)
        return dict(route=route, header_at=header_at, exit=rc, error=error, events=events,
                    stdout=output.getvalue(), elapsed=elapsed)

candidate = sys.argv[1] == "candidate"
if candidate:
    fixture.SCRIPT_PATH = root / "candidate/btx-faststart.py"
results = [run('manifest', 3), run('direct', 3), run('direct', 0)]
direct_expected = (0, 3, True) if candidate else (1, 0, False)
for result, expected in zip(results, [(0, 3, True), direct_expected, (0, 0, True)]):
    load, = [event for event in result['events'] if event['method'] == 'loadtxoutset']
    assert (result['exit'], load['seconds'], load['base_known']) == expected, result
    if result['exit'] == 0:
        assert 'chainstate bootstrap complete' in result['stdout'], result
    else:
        assert 'must appear in the headers chain' in result['error'], result
if candidate:
    controls = {
        'header_missing': run('direct', 99),
        'stalled_cli': run('direct', 99, stalled=True),
        'checksum_mismatch': run('direct', 0, checksum='0' * 64),
    }
    with tempfile.TemporaryDirectory() as tmp:
        truncated = Path(tmp) / 'snapshot.dat'
        truncated.write_bytes(snapshot.read_bytes()[:43])
        controls['truncated_metadata'] = run(
            'direct', 0, checksum=hashlib.sha256(truncated.read_bytes()).hexdigest(),
            payload=truncated)
    for key, error in [('header_missing', 'Timed out'), ('stalled_cli', 'Timed out'),
                       ('checksum_mismatch', 'SHA256 mismatch'),
                       ('truncated_metadata', 'Invalid UTXO snapshot metadata')]:
        result = controls[key]
        assert result['exit'] == 1 and error in result['error'], result
        assert not any(e['method'] == 'loadtxoutset' for e in result['events']), result
    assert controls['header_missing']['elapsed'] == controls['stalled_cli']['elapsed'] == 10
    assert not any(e['method'] == 'getblockheader'
                   for e in controls['checksum_mismatch']['events'])
else:
    controls = {}
print(json.dumps(dict(snapshot_sha256=digest, results=results, controls=controls), indent=2))
