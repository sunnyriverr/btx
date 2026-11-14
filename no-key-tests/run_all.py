"""Reproduce the bounded local campaign; children cannot execute tools or connect."""
import datetime
import json
from pathlib import Path
import platform
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
selections = [
    ('cut-release', 'source/test/util/cut_release_test.py', []),
    ('sign-release', 'source/test/util/sign_release_bundle_test.py', []),
    ('publish-release', 'source/test/util/publish_github_release_test.py', []),
    ('collector-signing', 'source/test/util/release_bundle_manifest_test.py', [
        'ReleaseBundleManifestTest.test_main_sign_with_invokes_signer',
        'ReleaseBundleManifestTest.test_sign_checksum_file_uses_loopback_passphrase_when_requested']),
    ('installer-signature', 'source/test/util/btx_agent_setup_test.py', [
        'BTXAgentSetupTest.test_remote_release_requires_signature_unless_overridden',
        'BTXAgentSetupTest.test_remote_release_verifies_signature_when_present']),
    ('new-contracts', 'no-key-tests/release_signer_recovery_test.py', []),
    ('broken-controls', 'no-key-tests/broken_controls_test.py', []),
]
results = []
for name, path, names in selections:
    command = [sys.executable, '-B', str(HERE / 'run_guarded.py'), str(ROOT / path), *names]
    run = subprocess.run(command, capture_output=True, text=True, timeout=45)
    output = run.stdout + run.stderr
    (HERE / (name + '.log')).write_text(output)
    lines = [line[15:] for line in output.splitlines() if line.startswith('GUARDED_RESULT ')]
    summary = json.loads(lines[-1]) if lines else {'success': False, 'error': 'missing checked aggregate'}
    summary.update(suite=name, exit_code=run.returncode, command=command)
    results.append(summary)
    print(name, 'PASS' if run.returncode == 0 and summary['success'] else 'FAIL', summary.get('tests'))
totals = {key: sum(run.get(key, 0) for run in results) for key in ('tests', 'failures', 'errors', 'skipped')}
receipt = {'utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
           'platform': platform.platform(), 'machine': platform.machine(), 'python': sys.version,
           'source_commit': 'a5d1637facc925ff176507fae87fc2042940829d', 'runs': results, 'totals': totals}
(HERE / 'results.json').write_text(json.dumps(receipt, indent=2) + '\n')
print('TOTAL', totals)
raise SystemExit(0 if all(run['exit_code'] == 0 and run['success'] for run in results) else 1)
