"""Future manual-only Mac regtest controller. Source preparation, not an executed recipe."""
from pathlib import Path
import configparser
import hashlib
import json
import os
import platform
import signal
import subprocess
import time

import restore

W, P, S, B, R, M = restore.W, restore.P, restore.S, restore.B, restore.R, restore.M
D = W / 'session3-mac-wallet-regtest'
STATE = {'source': M['source'], 'build_run': M['build_run'], 'compiled': False,
         'tests_started': False, 'tests_invoked': False, 'startup_confirmed': False,
         'recovery_controls_confirmed': False, 'tests_passed': False, 'complete': False,
         'classification': 'setup_pending'}
MARKERS = ['CONTROL: original locked encrypted wallet recognizes both receipts',
           'CONTROL: plain backup recovers both receipts without encrypted recovery warning',
           'RECOVERY: explicit refill/rescan restores exact receipts at same tip; relock succeeds',
           'PAYMENT: restored signer payment confirmed with exact fee and recipient',
           'RESTART: exact restored payment and inventory persist; relock succeeds']


def save():
    (R / 'runtime-result.json').write_text(json.dumps(STATE, indent=2) + '\n')


def classify(code, text, *, timed_out=False, bound_reason=None):
    """A preserved log must establish completion, all controls and no skipped test."""
    if bound_reason:
        return {'time': 'timeout', 'storage': 'storage_bound', 'scratch': 'scratch_bound'}[bound_reason]
    if timed_out:
        return 'timeout'
    if code == 77 or 'Test skipped' in text or 'Skipping test' in text or 'Test Skipped:' in text:
        return 'skipped'
    if code != 0:
        return 'fixture_failed' if MARKERS[0] in text else 'setup_or_initialization_failed'
    if 'Tests successful' not in text or any(marker not in text for marker in MARKERS):
        return 'incomplete_evidence'
    return 'passed'


def owned_scratch_bytes():
    total = 0
    for path in D.rglob('*'):
        try:
            if path.is_file() and not path.is_symlink():
                total += path.stat().st_size
        except FileNotFoundError:
            # Normal database/log deletion can race the sampled size walk.
            continue
    return total


def bounded(args, name, seconds, *, test=False, env=None):
    """Every invoked command has a time/storage bound and owns only its process group."""
    assert restore.shutil.disk_usage(W).free > restore.preservation_floor()
    path = R / (name + '.log')
    start = time.monotonic()
    timeout = False
    bound_reason = None
    max_scratch = 0
    with path.open('wb') as log:
        proc = subprocess.Popen([str(a) for a in args], stdout=log,
                                stderr=subprocess.STDOUT, start_new_session=True, env=env)
        if test:
            STATE['tests_invoked'] = True
            save()
        try:
            while proc.poll() is None:
                scratch_bytes = owned_scratch_bytes() if test and D.exists() else 0
                max_scratch = max(max_scratch, scratch_bytes)
                if time.monotonic() - start > seconds:
                    bound_reason = 'time'
                elif restore.shutil.disk_usage(W).free < restore.preservation_floor():
                    bound_reason = 'storage'
                elif scratch_bytes > 512 * 1024**2:
                    bound_reason = 'scratch'
                if bound_reason:
                    timeout = True
                    break
                time.sleep(1)
        finally:
            # Kill only this exact owned process group even when its leader has
            # already exited; a crashed fixture can leave daemon descendants.
            try:
                os.killpg(proc.pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
            until = time.monotonic() + 10
            while time.monotonic() < until:
                try:
                    os.killpg(proc.pid, 0)
                except ProcessLookupError:
                    break
                time.sleep(.2)
            else:
                try:
                    os.killpg(proc.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
            proc.wait(timeout=10)
            cleanup_until = time.monotonic() + 5
            cleanup_absent = False
            while time.monotonic() < cleanup_until:
                try:
                    os.killpg(proc.pid, 0)
                except ProcessLookupError:
                    cleanup_absent = True
                    break
                time.sleep(.2)
            STATE[name + '_cleanup'] = {'owned_process_group': proc.pid, 'absent': cleanup_absent}
            save()
    if test and D.exists():
        max_scratch = max(max_scratch, owned_scratch_bytes())
        if max_scratch > 512 * 1024**2 and bound_reason is None:
            bound_reason = 'scratch'
            timeout = True
    text = path.read_text(errors='replace')
    STATE[name] = {'exit_code': proc.returncode, 'seconds': round(time.monotonic() - start, 3),
                   'bound_exceeded': timeout, 'bound_reason': bound_reason, 'peak_sampled_scratch_bytes': max_scratch,
                   'log_sha256': restore.sha(path)}
    if test:
        STATE['observed_stage_markers'] = [marker for marker in MARKERS if marker in text]
        STATE['startup_confirmed'] = MARKERS[0] in text
        STATE['recovery_controls_confirmed'] = MARKERS[2] in text
    if not cleanup_absent:
        STATE['classification'] = 'cleanup_failed'
        STATE['tests_passed'] = False
    save()
    assert cleanup_absent, 'Owned process group still present after bounded cleanup: ' + name
    if test:
        verdict = classify(proc.returncode, text, timed_out=timeout, bound_reason=bound_reason)
        STATE['classification'] = verdict
        STATE['tests_passed'] = verdict == 'passed'
        save()
        assert verdict == 'passed', verdict
    else:
        assert not timeout and proc.returncode == 0, (name, proc.returncode, timeout)
    return text


def main():
    assert os.environ.get('RUNTIME_APPROVED') == 'true', 'Manual runtime approval absent'
    assert os.environ.get('GITHUB_ACTIONS') == 'true'
    assert os.environ.get('GITHUB_REPOSITORY') == 'sunnyriverr/btx'
    assert platform.system() == 'Darwin' and platform.machine() == 'arm64'
    assert restore.shutil.disk_usage(W).free >= 15 * 1024**3
    assert D.parent == W and not D.exists() and not D.is_symlink()
    STATE['host'] = {'system': platform.system(), 'architecture': platform.machine(), 'macos': platform.mac_ver()[0]}
    assert bounded(['git', '-C', S, 'rev-parse', 'HEAD'], 'source-head', 30).strip() == M['source']
    assert not bounded(['git', '-C', S, 'status', '--porcelain'], 'source-clean', 30).strip()
    restore.restore()
    assert restore.sha(B / 'CMakeCache.txt') == M['cache_sha256']
    assert restore.sha(B / 'test/config.ini') == M['config_sha256']
    config = configparser.ConfigParser()
    config.read(B / 'test/config.ini')
    assert Path(config['environment']['SRCDIR']).resolve() == S
    assert Path(config['environment']['BUILDDIR']).resolve() == B
    for key in ['ENABLE_WALLET', 'USE_SQLITE', 'ENABLE_BITCOIND', 'ENABLE_CLI']:
        assert config['components'].getboolean(key)
    for key in ['ENABLE_MODELNET', 'ENABLE_ZMQ']:
        assert not config['components'].getboolean(key, fallback=False)
    for name, meta in M['binaries'].items():
        binary = B / 'bin' / name
        assert binary.stat().st_size == meta['bytes'] and restore.sha(binary) == meta['sha256']
        assert 'arm64' in bounded(['file', binary], name + '-format', 30)
        bounded(['otool', '-L', binary], name + '-dependencies', 30)
    python = Path(os.environ['BTX_BUILD_PYTHON']).resolve()
    assert python == Path(M['python']['executable']).resolve(), 'Embedded Python framework location drift'
    assert restore.sha(python) == M['python']['executable_sha256']
    assert restore.sha(P / 'dependencies.json') == M['dependency_lock_sha256']
    # The unchanged locked bootstrap verifies retained headers/static libraries
    # and installs only the exact wheels into this ephemeral setup-python runtime.
    bounded([python, P / 'bootstrap.py'], 'dependency-bootstrap', 300)
    for name, key in [('test_framework.py', 'framework_sha256'), ('test_node.py', 'test_node_sha256')]:
        assert restore.sha(S / 'test/functional/test_framework' / name) == M[key]
    target = S / 'test/functional/wallet_encrypted_backup_recovery.py'
    assert restore.sha(target) == M['original_fixture_sha256']
    assert restore.sha(P / target.name) == M['fixture_sha256']
    target.write_bytes((P / target.name).read_bytes())
    assert restore.sha(target) == M['fixture_sha256']
    env = os.environ.copy()
    env.pop('GH_TOKEN', None)
    env.pop('GITHUB_TOKEN', None)
    for name in ['BTXD', 'BITCOIND', 'BTXCLI', 'BITCOINCLI', 'BITCOINWALLET', 'BTXWALLET', 'BITCOINUTIL', 'BTXUTIL']:
        env.pop(name, None)
    env.update(BTXD=str(B / 'bin/btxd'), BTXCLI=str(B / 'bin/btx-cli'), PYTHONDONTWRITEBYTECODE='1',
               BTX_MATMUL_BACKEND='cpu', BTX_MATMUL_V4_BACKEND='cpu', BTX_MATMUL_REQUIRE_BACKEND='cpu')
    # This framework entry-point check imports/constructs the exact overlaid
    # fixture before any node starts. It is not a test pass or startup proof.
    bounded([python, target, '--configfile=' + str(B / 'test/config.ini'), '--help'],
            'fixture-entrypoint', 60, env=env)
    bounded([python, P / 'entrypoint.py', target, B / 'test/config.ini', D, M['portseed']],
            'fixture-construction', 60, env=env)
    STATE['classification'] = 'runtime_started'
    STATE['tests_started'] = True
    save()
    bounded([python, target, '--configfile=' + str(B / 'test/config.ini'),
             '--tmpdir=' + str(D), '--portseed=' + str(M['portseed']), '--nocleanup'],
            'functional', M['runtime_seconds'], test=True, env=env)
    STATE['complete'] = True


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        STATE['error'] = str(error)
        if not STATE['tests_started']:
            STATE['classification'] = 'setup_failed'
        elif STATE['classification'] == 'runtime_started':
            STATE['classification'] = 'runtime_controller_failed'
        raise
    finally:
        save()
