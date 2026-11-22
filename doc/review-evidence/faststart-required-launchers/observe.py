"""Test whether a verified replacement missing one launcher preserves the old install."""
import gzip
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile

HERE = Path(__file__).resolve().parent
SOURCE = Path(sys.argv[1]).resolve()
INSTALLER = SOURCE / 'contrib/faststart/btx-agent-setup.py'
spec = importlib.util.spec_from_file_location('fixture', SOURCE / 'test/util/btx_agent_setup_test.py')
fixture = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fixture)
case = fixture.BTXAgentSetupTest()
case.setUp()


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def create_release(root, stamp, *, missing_cli=False):
    root.mkdir()
    archive = case._build_fake_archive(root, extra_files={
        'bin/btxd': f'#!/bin/sh\nprintf "%s\\n" {stamp}-daemon\n',
        'bin/btx-cli': f'#!/bin/sh\nprintf "%s\\n" {stamp}-cli\n',
    })
    tree = root / 'package/btx-29.2'
    if missing_cli:
        (tree / 'bin/btx-cli').unlink()
    for path in (tree / 'bin').iterdir():
        path.chmod(0o755)
    def stable(member):
        member.mtime = 0
        return member

    with archive.open('wb') as raw:
        with gzip.GzipFile(filename='', mode='wb', fileobj=raw, mtime=0) as zipped:
            with tarfile.open(fileobj=zipped, mode='w') as bundle:
                bundle.add(tree, arcname=tree.name, filter=stable)
    manifest = case._write_manifest(root, archive, include_snapshot_manifest=False)
    assert digest(archive) in (root / 'SHA256SUMS').read_text()
    return manifest, digest(archive)


def invoke(manifest, install, force=False):
    args = [sys.executable, str(INSTALLER), '--release-manifest', str(manifest),
            '--install-dir', str(install), '--platform', 'linux-x86_64', '--json']
    if force:
        args.append('--force')
    return subprocess.run(args, text=True, capture_output=True, timeout=12)


def launchers(install):
    result = {}
    for name in ('btxd', 'btx-cli'):
        path = install / 'btx-29.2/bin' / name
        if path.is_file():
            out = subprocess.run([str(path), '--version'], text=True, capture_output=True,
                                 check=True, timeout=5)
            result[name] = dict(marker=out.stdout.strip(), sha256=digest(path))
        else:
            result[name] = None
    return result


with tempfile.TemporaryDirectory(prefix='faststart-required-launchers-') as temp:
    root = Path(temp)
    install = root / 'install'
    sentinel = root / 'data-sentinel'
    sentinel.write_text('separate node state')
    recorded = digest(sentinel)
    a, _ = create_release(root / 'a', 'A')
    invalid, archive_hash = create_release(root / 'incomplete', 'B', missing_cli=True)
    repaired, retry_archive_hash = create_release(root / 'complete', 'B')
    assert invoke(a, install).returncode == 0
    before = launchers(install)
    assert [before[x]['marker'] for x in before] == ['A-daemon', 'A-cli']
    refusal = invoke(invalid, install)
    assert refusal.returncode != 0 and 'Install directory is not empty' in refusal.stderr
    assert launchers(install) == before
    failed = invoke(invalid, install, force=True)
    assert failed.returncode != 0 and 'could not find any of btx-cli' in failed.stderr
    after_failure = launchers(install)
    retry = invoke(repaired, install, force=True)
    assert retry.returncode == 0, retry.stderr
    after_retry = launchers(install)
    assert [after_retry[x]['marker'] for x in after_retry] == ['B-daemon', 'B-cli']
    assert digest(sentinel) == recorded
    assert not list(root.glob('install.*'))
    observation = dict(installer_sha256=digest(INSTALLER), malformed_archive_sha256=archive_hash,
                       complete_archive_sha256=retry_archive_hash,
                       forced_failure_exit=failed.returncode, before=before, after_failure=after_failure,
                       after_complete_retry=after_retry, no_force_and_data_controls=True,
                       failed_attempt_preserved_install=after_failure == before)
(HERE / sys.argv[2]).write_text(json.dumps(observation, indent=2) + '\n')
assert after_failure == before, 'The installed launchers changed during a rejected replacement'
