"""Missing signer/recovery contracts; real release helpers, simulated GPG/API only.

Run with run_guarded.py. Maintained test fixtures supply the bundles, so the
additional cases do not create another bundle implementation.
"""
import contextlib
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

SOURCE = Path(__file__).resolve().parents[1] / 'source'
sys.path.insert(0, str(SOURCE / 'scripts/release'))
PRIMARY = '11' * 20
SUBKEY = '22' * 20
OTHER = '33' * 20
COMMIT = '44' * 20


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, SOURCE / path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


publisher_fixture = load('publisher_fixture', 'test/util/publish_github_release_test.py')
signer_fixture = load('signer_fixture', 'test/util/sign_release_bundle_test.py')
installer_fixture = load('installer_fixture', 'test/util/btx_agent_setup_test.py')


def valid_status(signer=SUBKEY, primary=PRIMARY):
    return ('[GNUPG:] VALIDSIG ' + signer +
            ' 2026-11-14 1794693600 0 4 0 1 10 00 ' + primary + '\n')


class SignerValidationTest(unittest.TestCase):
    def setUp(self):
        self.publisher = publisher_fixture.load_module()

    def test_valid_subkey_status_exposes_subkey_and_primary(self):
        with patch.object(self.publisher.subprocess, 'run', return_value=
                          subprocess.CompletedProcess([], 0, valid_status(), '')) as run:
            self.assertEqual(self.publisher.verify_checksum_signature(
                Path('SHA256SUMS'), Path('SHA256SUMS.asc'), 'fake-gpg'), {SUBKEY, PRIMARY})
        self.assertEqual(run.call_args.args[0],
                         ['fake-gpg', '--status-fd=1', '--verify', 'SHA256SUMS.asc', 'SHA256SUMS'])

    def test_nonzero_gpg_rejected_even_with_validsig_text(self):
        with patch.object(self.publisher.subprocess, 'run', return_value=
                          subprocess.CompletedProcess([], 2, valid_status(), 'synthetic verification failure')):
            with self.assertRaisesRegex(RuntimeError, 'signature verification failed'):
                self.publisher.verify_checksum_signature(Path('sums'), Path('sig'), 'fake-gpg')

    def test_success_without_validsig_rejected(self):
        with patch.object(self.publisher.subprocess, 'run', return_value=
                          subprocess.CompletedProcess([], 0, '[GNUPG:] GOODSIG 123 example\n', '')):
            with self.assertRaisesRegex(RuntimeError, 'no VALIDSIG fingerprint'):
                self.publisher.verify_checksum_signature(Path('sums'), Path('sig'), 'fake-gpg')

    def test_public_dry_run_accepts_primary_pin_rejects_different_signer(self):
        with tempfile.TemporaryDirectory() as tmp:
            fixture = publisher_fixture.PublishGitHubReleaseTest()
            fixture.module = self.publisher
            bundle = fixture._build_bundle(Path(tmp), include_signature=True, manifest_overrides={
                'release_tag': 'v0.34.16', 'source_repository': 'btxchain/btx', 'source_commit': COMMIT})
            args = ['--repo', 'btxchain/btx', '--tag', 'v0.34.16', '--bundle-dir', str(bundle),
                    '--target-commit', COMMIT, '--expected-signing-fingerprint', PRIMARY,
                    '--validate-public-release', '--dry-run']
            with patch.object(self.publisher.subprocess, 'run') as run:
                run.return_value = subprocess.CompletedProcess([], 0, valid_status(), '')
                with contextlib.redirect_stdout(io.StringIO()):
                    self.assertEqual(self.publisher.main(args), 0)
                run.return_value = subprocess.CompletedProcess([], 0, valid_status(OTHER, OTHER), '')
                with self.assertRaisesRegex(RuntimeError, 'signer mismatch'):
                    self.publisher.main(args)
            self.assertEqual(run.call_count, 2)

    def test_valid_provenance_missing_signature_reaches_signature_guard(self):
        with tempfile.TemporaryDirectory() as tmp:
            fixture = publisher_fixture.PublishGitHubReleaseTest()
            fixture.module = self.publisher
            bundle = fixture._build_bundle(Path(tmp), manifest_overrides={
                'release_tag': 'v0.34.16', 'source_repository': 'btxchain/btx', 'source_commit': COMMIT})
            with self.assertRaisesRegex(FileNotFoundError, 'must include a declared SHA256SUMS signature'):
                self.publisher.main(['--repo', 'btxchain/btx', '--tag', 'v0.34.16',
                    '--bundle-dir', str(bundle), '--target-commit', COMMIT,
                    '--expected-signing-fingerprint', PRIMARY, '--validate-public-release', '--dry-run'])


class SigningRecoveryTest(unittest.TestCase):
    def exercise_recovery(self, stage, error):
        signer = signer_fixture.load_module()
        fixture = signer_fixture.SignReleaseBundleTest()
        fixture.module = signer
        with tempfile.TemporaryDirectory() as tmp:
            bundle = fixture._build_bundle(Path(tmp))
            before = {p.name: p.read_bytes() for p in bundle.iterdir()}
            calls = []
            real_write = signer.collector.write_checksum_file
            real_ensure = signer.publisher.ensure_bundle

            def write(*args):
                real_write(*args)
                if stage == 'checksums':
                    calls.append(stage)
                    raise error

            def sign(*args, **kwargs):
                (bundle / 'SHA256SUMS.asc').write_text('synthetic signature\n')
                if stage == 'sign':
                    calls.append(stage)
                    raise error

            def verify(*args):
                if stage == 'verify':
                    calls.append(stage)
                    raise error
                return {PRIMARY}

            def ensure(*args):
                result = real_ensure(*args)
                if stage == 'final-check' and (bundle / 'SHA256SUMS.asc').exists():
                    calls.append(stage)
                    raise error
                return result

            args = ['--bundle-dir', str(bundle), '--sign-with', 'synthetic-key',
                    '--expected-signing-fingerprint', PRIMARY]
            with patch.object(signer.collector, 'write_checksum_file', write), \
                    patch.object(signer.collector, 'sign_checksum_file', sign), \
                    patch.object(signer.publisher, 'verify_checksum_signature', verify), \
                    patch.object(signer.publisher, 'ensure_bundle', ensure):
                with self.assertRaises(type(error)):
                    signer.main(args)
            self.assertEqual(calls, [stage], 'must reach the intended injected interruption')
            self.assertEqual({p.name: p.read_bytes() for p in bundle.iterdir()}, before)
            real_ensure(bundle)
            with patch.object(signer.collector, 'sign_checksum_file',
                              lambda *a, **kw: (bundle / 'SHA256SUMS.asc').write_text('synthetic retry\n')), \
                    patch.object(signer.publisher, 'verify_checksum_signature', return_value={PRIMARY}), \
                    contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(signer.main(args), 0)
            real_ensure(bundle)
            self.assertEqual(json.loads((bundle / 'btx-release-manifest.json').read_text())['signature_file'],
                             'SHA256SUMS.asc')

    def test_checksum_interruption_restores_then_retries(self):
        self.exercise_recovery('checksums', KeyboardInterrupt('synthetic interruption'))

    def test_partial_signature_error_restores_then_retries(self):
        self.exercise_recovery('sign', RuntimeError('synthetic signing error'))

    def test_verify_interruption_restores_then_retries(self):
        self.exercise_recovery('verify', KeyboardInterrupt('synthetic interruption'))

    def test_final_bundle_check_error_restores_then_retries(self):
        self.exercise_recovery('final-check', RuntimeError('synthetic final check failure'))


class PublishingRecoveryTest(unittest.TestCase):
    def exercise_recovery(self, failure):
        publisher = publisher_fixture.load_module()
        fixture = publisher_fixture.PublishGitHubReleaseTest()
        fixture.module = publisher
        with tempfile.TemporaryDirectory() as tmp:
            bundle = fixture._build_bundle(Path(tmp), include_signature=True, manifest_overrides={
                'release_tag': 'v0.34.16', 'source_repository': 'btxchain/btx', 'source_commit': COMMIT})
            state = {'release': None, 'assets': {}, 'events': [], 'fail': True, 'next_id': 0}

            def snapshot():
                if state['release'] is None:
                    return None
                return dict(state['release'], assets=[dict(a) for a in state['assets'].values()])

            def create(repo, tag, token, payload):
                self.assertTrue(payload['draft'])
                state['events'].append('create-draft')
                state['release'] = dict(payload, id=1, html_url='https://example.invalid/release')
                return snapshot()

            def update(repo, release_id, token, payload):
                if not payload['draft']:
                    expected = {p.name: p.stat().st_size for p in bundle.iterdir()}
                    self.assertEqual({n: a['size'] for n, a in state['assets'].items()}, expected)
                    self.assertIn('verified-complete', state['events'])
                state['events'].append('stage-draft' if payload['draft'] else 'publish')
                state['release'].update(payload)
                return snapshot()

            def upload(repo, release, asset, token):
                self.assertTrue(state['release']['draft'])
                state['next_id'] += 1
                state['assets'][asset.name] = {'id': state['next_id'], 'name': asset.name,
                                              'size': asset.stat().st_size}
                state['events'].append('upload:' + asset.name)
                if state['fail'] and failure in ('upload-error', 'upload-interrupt'):
                    state['fail'] = False
                    raise (KeyboardInterrupt('synthetic upload interruption') if failure == 'upload-interrupt'
                           else RuntimeError('synthetic upload failure after server accepted asset'))

            def get(*args):
                result = snapshot()
                if result is not None and len(state['assets']) == len(list(bundle.iterdir())):
                    if state['fail'] and failure == 'readback-incomplete':
                        state['fail'] = False
                        result['assets'] = result['assets'][:-1]
                        state['events'].append('incomplete-readback')
                    else:
                        state['events'].append('verified-complete')
                return result

            def delete(repo, asset_id, token):
                name = next(n for n, a in state['assets'].items() if a['id'] == asset_id)
                state['events'].append('delete:' + name)
                state['assets'].pop(name)

            args = ['--repo', 'btxchain/btx', '--tag', 'v0.34.16', '--bundle-dir', str(bundle),
                    '--target-commit', COMMIT, '--expected-signing-fingerprint', PRIMARY, '--publish']
            with contextlib.ExitStack() as stack:
                for name, replacement in {
                    'read_token': lambda args: 'synthetic-token',
                    'require_repository_commit': lambda *a: None,
                    'resolve_repository_commit': lambda *a: COMMIT,
                    'verify_checksum_signature': lambda *a: {PRIMARY},
                    'create_release': create, 'update_release': update, 'get_release': get,
                    'upload_asset': upload,
                    'delete_asset': delete,
                }.items():
                    stack.enter_context(patch.object(publisher, name, replacement))
                error = KeyboardInterrupt if failure == 'upload-interrupt' else RuntimeError
                with self.assertRaises(error):
                    publisher.main(args)
                self.assertFalse(state['fail'], 'must reach the injected API fault')
                self.assertTrue(state['release']['draft'])
                self.assertNotIn('publish', state['events'])
                self.assertTrue(state['assets'], 'server must retain accepted upload progress')
                with contextlib.redirect_stdout(io.StringIO()):
                    self.assertEqual(publisher.main(args), 0)
            self.assertFalse(state['release']['draft'])
            self.assertEqual(state['events'].count('publish'), 1)
            self.assertEqual(state['events'].count('create-draft'), 1)
            self.assertTrue(any(e.startswith('delete:') for e in state['events']))

    def test_upload_error_leaves_draft_then_retry_completes(self):
        self.exercise_recovery('upload-error')

    def test_upload_interrupt_leaves_draft_then_retry_completes(self):
        self.exercise_recovery('upload-interrupt')

    def test_incomplete_readback_leaves_draft_then_retry_completes(self):
        self.exercise_recovery('readback-incomplete')


class InstallerSignerPolicyTest(unittest.TestCase):
    def exercise_installer(self, status, returncode):
        fixture = installer_fixture.BTXAgentSetupTest()
        fixture.setUp()
        installer = fixture.module
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            archive = fixture._build_fake_archive(root)
            manifest = fixture._write_manifest(root, archive, include_signature=True)
            install = root / 'install'
            args = ['--release-manifest', manifest.as_uri(), '--platform', 'linux-x86_64',
                    '--install-dir', str(install), '--json']
            with patch.object(installer.subprocess, 'run', return_value=
                              subprocess.CompletedProcess([], returncode, status, 'synthetic status')) as run:
                if returncode:
                    with self.assertRaisesRegex(RuntimeError, 'signature verification failed'):
                        installer.main(args)
                    self.assertFalse(install.exists())
                else:
                    output = io.StringIO()
                    with contextlib.redirect_stdout(output):
                        self.assertEqual(installer.main(args), 0)
                    installed = Path(json.loads(output.getvalue())['btxd'])
                    self.assertTrue(installed.is_file())
                    self.assertIn(install, installed.parents)
            self.assertEqual(run.call_count, 1)
            command = run.call_args.args[0]
            self.assertEqual(command[:2], ['gpg', '--verify'])
            self.assertEqual(Path(command[2]).name, 'SHA256SUMS.asc')
            self.assertEqual(Path(command[3]).name, 'SHA256SUMS')

    def test_current_installer_accepts_both_verification_success_identities(self):
        # Characterizes the present caller; does not assert a new authorization rule.
        for identity in (PRIMARY, OTHER):
            with self.subTest(identity=identity):
                self.exercise_installer(valid_status(identity, identity), 0)

    def test_installer_rejects_verification_failure_before_install(self):
        self.exercise_installer('[GNUPG:] BADSIG synthetic\n', 2)


if __name__ == '__main__':
    unittest.main()
