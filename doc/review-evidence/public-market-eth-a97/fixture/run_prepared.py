"""Explicitly executed bounded local controller; preparation never invokes it."""
from pathlib import Path
import argparse
import datetime
import hashlib
import json
import os
import platform
import shutil
import signal
import subprocess
import threading
import time
import uuid

P = Path(__file__).resolve().parent
M = json.loads((P / 'manifest.json').read_text())


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(1048576), b''):
            h.update(block)
    return h.hexdigest()


def bytes_used(root):
    total = 0
    for path in root.rglob('*'):
        try:
            if path.is_file() and not path.is_symlink():
                total += path.stat().st_size
        except FileNotFoundError:
            pass
    return total


def group_absent(pid):
    try:
        os.killpg(pid, 0)
        return False
    except ProcessLookupError:
        return True


def execute_case(case, env, python):
    assert case in M['cases']
    # Never overwrite an earlier pass, wallet, failed checkpoint or evidence.
    target = P.parent / 'execution' / (datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ') + '-' + case)
    target.mkdir(parents=True, exist_ok=False, mode=0o700)
    root = Path(M['runtime_root'])
    root.mkdir(mode=0o700)
    records = target / 'records'
    child_env = {**env, 'BTX_PUBLIC_ETH_EXECUTE': 'disposable-regtest-only',
                 'BTX_PUBLIC_ETH_RECORDS': str(records), 'BTX_PUBLIC_ETH_ROOT': str(root)}
    assert shutil.disk_usage(P).free > M['disk_reserve_bytes'] + M['scratch_bytes']
    started = time.monotonic()
    stopped = threading.Event()
    reason = error_text = None
    proc = timer = None
    def kill_group():
        if proc is None:
            return
        stopped.set()
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
    try:
        with (target / 'controller.log').open('wb') as log:
            proc = subprocess.Popen([str(python), '-B', '-I', str(P / 'public_eth.py'), str(root), case],
                stdout=log, stderr=subprocess.STDOUT, env=child_env, start_new_session=True)
            (target / 'owned-process.json').write_text(json.dumps({'controller_pid': os.getpid(),
                'fixture_pid_and_group': proc.pid, 'scratch': str(root)}) + '\n')
            timer = threading.Timer(max(0, started + M['case_seconds'] - time.monotonic()), kill_group)
            timer.daemon = True
            timer.start()
            while proc.poll() is None:
                if shutil.disk_usage(P).free < M['disk_reserve_bytes']:
                    reason = 'free-space reserve'
                elif bytes_used(target) + bytes_used(root) > M['scratch_bytes']:
                    reason = 'case scratch bound'
                if reason:
                    kill_group()
                    break
                time.sleep(0.5)
            proc.wait(timeout=10)
    except BaseException as error:
        error_text = type(error).__name__ + ': ' + str(error)
        reason = reason or 'controller interrupted or setup/monitor failed'
    finally:
        if timer is not None:
            timer.cancel()
        if proc is not None:
            if not group_absent(proc.pid):
                kill_group()
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                kill_group()
            end = time.monotonic() + 2
            while not group_absent(proc.pid) and time.monotonic() < end:
                time.sleep(0.1)
    receipt = {'case': case, 'exit': proc.returncode if proc is not None else None,
        'seconds': round(time.monotonic() - started, 3), 'error': error_text,
        'bound': reason or ('600-second case deadline or surviving child' if stopped.is_set() else None),
        'process_group_absent': proc is None or group_absent(proc.pid), 'source': M['source'],
        'binary_sha256': {k: M[k]['sha256'] for k in ('btx', 'anvil', 'contract')},
        'runtime_preserved': str(root), 'compiled': False, 'upstream_posted': False}
    try:
        receipt['native_result'] = json.loads((records / 'result.json').read_text())
    except (OSError, ValueError) as error:
        receipt['native_result_error'] = type(error).__name__ + ': ' + str(error)
    staging = target / 'execution-receipt.json.tmp'
    staging.write_text(json.dumps(receipt, indent=2) + '\n')
    staging.replace(target / 'execution-receipt.json')
    assert receipt['exit'] == 0 and not receipt['bound'] and not error_text and receipt['process_group_absent'], receipt
    assert 'native_result' in receipt, receipt.get('native_result_error')
    assert receipt['native_result']['status'] == 'PASS' and not receipt['native_result']['cleanup_errors']
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execute', action='store_true', help='Only after user authorizes the native disposable test run')
    parser.add_argument('cases', nargs='*', help='single public Ethereum settlement/restart case: settle')
    args = parser.parse_args()
    assert args.execute, 'Prepared only: native execution requires explicit --execute'
    assert platform.system() == 'Darwin' and platform.machine() == 'arm64'
    assert not (P.parent / 'execution').is_symlink()
    for filename, expected in M['fixture_sha256'].items():
        assert sha(P / filename) == expected, filename
    for role in ('btx', 'anvil', 'contract'):
        binary = Path(M[role]['path'])
        assert binary.is_file() and sha(binary) == M[role]['sha256']
    runtime = Path(M['python_runtime'])
    framework = runtime / 'Python.framework/Versions/3.12'
    python = framework / 'bin/python3.12'
    assert sha(python) == M['python_executable_sha256']
    env = os.environ.copy()
    for name in ('GH_TOKEN', 'GITHUB_TOKEN', 'PYTHONPATH', 'PYTHONHOME', '__PYVENV_LAUNCHER__',
                 'LD_PRELOAD', 'DYLD_INSERT_LIBRARIES'):
        env.pop(name, None)
    env.update(DYLD_FRAMEWORK_PATH=str(runtime), DYLD_LIBRARY_PATH=str(framework / 'lib'),
               PYTHONDONTWRITEBYTECODE='1')
    # No installs or runtime upgrades. Reuse the already-qualified Python copy.
    probe = subprocess.check_output([str(python), '-B', '-I', '-c',
        'import json,sys,cryptography,cffi,pycparser;print(json.dumps([list(sys.version_info[:3]),cryptography.__version__,cffi.__version__,pycparser.__version__]))'],
        env=env, text=True, timeout=20)
    assert json.loads(probe) == [[3, 12, 10], '46.0.4', '2.1.1', '3.12']
    def interrupted(number, frame):
        raise InterruptedError('Controller received signal ' + str(number))
    signal.signal(signal.SIGTERM, interrupted)
    signal.signal(signal.SIGINT, interrupted)
    cases = args.cases or M['cases']
    assert len(cases) == len(set(cases)), 'Do not repeat a case in one invocation'
    for case in cases:
        execute_case(case, env, python)


if __name__ == '__main__':
    main()
