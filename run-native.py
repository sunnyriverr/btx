"""One bounded normal-framework paired wallet transition; disposable regtest only."""
from pathlib import Path
import csv
import hashlib
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import time

root = Path.cwd()
records = root / 'records'
package = root / 'previous-package/btx-0.34.16'
private = root / 'transition-private'
producer = {}
old = {}
inputs = {}
receipt = dict(passed=False, compiled=False, native_test_attempted=False)
started = time.monotonic()
process = None
private_owned = False
peak = 0
reason = None


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def group_exists(pid):
    try:
        os.killpg(pid, 0)
        return True
    except ProcessLookupError:
        return False


def stop_owned(child):
    assert child.pid != os.getpgrp()
    for sig, seconds in ((signal.SIGTERM, 10), (signal.SIGKILL, 5)):
        if not group_exists(child.pid):
            break
        os.killpg(child.pid, sig)
        end = time.monotonic() + seconds
        while group_exists(child.pid) and time.monotonic() < end:
            child.poll()
            time.sleep(.1)
    child.wait(timeout=5)
    return not group_exists(child.pid)


try:
    producer = json.loads((root / 'saved/producer.json').read_text())
    assert producer['source_identity'] == '1e2f8b5f12295002334d3390c12cac0bb4ae2aff'
    old = json.loads((records / 'old-runtime-preflight.json').read_text())
    assert old['status'] == 'OLD_STATIC_CLOSURE_PASS'
    inputs = json.loads((root / 'inputs.json').read_text())


    for name, digest in inputs.items():
        path = root / 'suite-inputs' / name
        assert sha(path) == digest
        (root / 'source/test/functional' / name).write_bytes(path.read_bytes())
    for name, digest in producer['binary_sha256'].items():
        assert sha(root / 'build/bin' / name) == digest
    link = root / 'build/test/functional/wallet_release_transition.py'
    assert not link.exists() and not link.is_symlink()
    link.symlink_to(root / 'source/test/functional/wallet_release_transition.py')
    assert not private.exists()
    private.mkdir(mode=0o700)
    private_owned = True
    (private / 'rt').mkdir()
    (private / 'startup').mkdir()
    env = dict(os.environ, XDG_RUNTIME_DIR=str(private / 'rt'))
    for key in ('BTX_GLIBC_PREFIX', 'LD_LIBRARY_PATH', 'LD_PRELOAD', 'PYTHONHOME', 'PYTHONPATH'):
        env.pop(key, None)
    for variable, binary in [('BTXD', 'btxd'), ('BITCOIND', 'btxd'), ('BTXCLI', 'btx-cli'), ('BITCOINCLI', 'btx-cli')]:
        env[variable] = str(root / 'build/bin' / binary)
    env['BTX_PREVIOUS_DAEMON'] = str(package / 'bin/btxd')
    env.pop('BTX_PREVIOUS_MODELNET', None)
    receipt = dict(source=producer['source_identity'], binaries=producer['binary_sha256'],
                   old_entrypoints=old['entrypoints'], old_source_association=old['source_association'],
                   inputs=inputs, normal_runner=True, compiled=False, deadline_seconds=900,
                   scratch_limit_bytes=1024*2**20, startup=[], native_test_attempted=False)
    # Help/version execute only after both static closures. No daemon or user data.
    for label, executable in [('old', package / 'bin/btxd'), ('current', root / 'build/bin/btxd')]:
        for mode in ('version', 'help'):
            logfile = private / (label + '-' + mode + '.log')
            args = [str(executable), '-regtest', '-datadir=' + str(private / 'startup')]
            args += ['-version'] if mode == 'version' else ['-help', '-help-debug']
            with logfile.open('w') as log:
                process = subprocess.Popen(args, env=env, cwd=private, stdout=log,
                                           stderr=subprocess.STDOUT, start_new_session=True)
                try:
                    process.wait(timeout=30)
                finally:
                    receipt['group_absent'] = stop_owned(process)
            assert receipt['group_absent'] and process.returncode == 0, (label, mode, process.returncode)
            text = logfile.read_text(errors='replace')
            receipt['startup'].append(dict(binary=label, mode=mode, exit_code=0, output_sha256=sha(logfile)))
            if label == 'old' and mode == 'help':
                has_modelnet = '-modelnet' in text
                receipt['old_modelnet_help_option'] = has_modelnet
                if has_modelnet:
                    env['BTX_PREVIOUS_MODELNET'] = '1'
            process = None
    command = [sys.executable, str(root / 'source/test/functional/test_runner.py'),
               'wallet_release_transition.py', '--configfile=' + str(root / 'build/test/config.ini'),
               '-j1', '--tmpdirprefix=' + str(private), '--resultsfile=' + str(private / 'results.csv'), '--nocleanup']
    receipt['native_test_attempted'] = True
    with (private / 'runner.log').open('w') as log:
        process = subprocess.Popen(command, cwd=root, env=env, stdout=log,
                                   stderr=subprocess.STDOUT, start_new_session=True)
        while process.poll() is None:
            total = 0
            for path in private.rglob('*'):
                try:
                    if path.is_file() and not path.is_symlink():
                        total += path.stat().st_size
                except FileNotFoundError:
                    pass  # The runner removes its own scratch concurrently.
            peak = max(peak, total)
            if time.monotonic() - started > 900:
                reason = 'DEADLINE'
            elif peak > 1024*2**20:
                reason = 'SCRATCH_LIMIT'
            elif shutil.disk_usage(root).free < 1.25*2**30:
                reason = 'DISK_RESERVE'
            if reason:
                break
            time.sleep(1)
    receipt['group_absent'] = stop_owned(process)
    receipt['exit_code'] = process.returncode
    rows = list(csv.DictReader((private / 'results.csv').open())) if (private / 'results.csv').exists() else []
    receipt['results_csv'] = rows
    receipt['stop_reason'] = reason
    text = (private / 'runner.log').read_text(errors='replace')
    # Runner normally hides successful test stdout. Read only fixed checkpoint
    # labels from the private framework logs, then delete those raw logs.
    framework_text = '\n'.join(path.read_text(errors='replace')
                               for path in sorted(private.rglob('test_framework.log')))
    receipt['checkpoints'] = re.findall(r'Transition checkpoint: ([a-z-]+)', framework_text)
    receipt['failure_frames'] = [dict(file=f.replace(str(root), 'WORKSPACE'), line=int(n), function=fn)
        for f, n, fn in re.findall(r'File "([^"\n]+)", line (\d+), in ([^\n]+)', text)][-12:]
    receipt['exception_classes'] = re.findall(r'(?m)^([A-Za-z_]\w*(?:Error|Exception))(?=:|$)', text)[-5:]
    expected = ['old-baseline-confirmed', 'old-reopen-passed', 'existing-open-passed', 'backup-restore-passed']
    receipt['passed'] = (not reason and receipt['group_absent'] and process.returncode == 0
                         and len(rows) == 2 and all(row['status'] == 'Passed' for row in rows)
                         and rows[0]['test'] == 'wallet_release_transition.py --descriptors'
                         and rows[1]['test'] == 'ALL' and receipt['checkpoints'] == expected)
except BaseException as error:
    receipt.update(passed=False, failure_class=type(error).__name__,
                   stage='native-test' if receipt.get('native_test_attempted') else 'setup-or-startup-preflight')
finally:
    finalization_errors = []
    safe_to_remove = process is None
    if process is not None:
        try:
            receipt['group_absent'] = stop_owned(process)
            safe_to_remove = receipt['group_absent']
        except BaseException as error:
            receipt['group_absent'] = False
            finalization_errors.append('process-stop: ' + type(error).__name__)
    # Record integrity failures without suppressing the cleanup disposition.
    for label, base, expected in [('old', package, old.get('entrypoints', {})),
                                  ('current', root / 'build/bin', producer.get('binary_sha256', {}))]:
        for name, digest in expected.items():
            try:
                assert sha(base / name) == digest
            except BaseException as error:
                finalization_errors.append(label + '-integrity/' + name + ': ' + type(error).__name__)
    if safe_to_remove:
        paths = ([private] if private_owned else [])
        if old.get('status') == 'OLD_STATIC_CLOSURE_PASS':
            paths.append(root / 'previous-package')
        for path in paths:
            try:
                if path.exists():
                    shutil.rmtree(path)
            except BaseException as error:
                finalization_errors.append('cleanup/' + path.name + ': ' + type(error).__name__)
    receipt.update(elapsed_seconds=round(time.monotonic() - started, 2),
                   peak_sampled_private_bytes=peak,
                   private_data_removed=not private.exists(),
                   old_package_removed=not package.exists(),
                   raw_logs_uploaded=False, finalization_errors=finalization_errors)
    if finalization_errors or not receipt['private_data_removed'] or not receipt['old_package_removed']:
        receipt['passed'] = False
    records.mkdir(exist_ok=True)
    (records / 'native-transition-result.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps(receipt), flush=True)
raise SystemExit(0 if receipt.get('passed') else 1)
