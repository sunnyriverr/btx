"""One normal-runner wallet invocation, bounded and collected without rebuilding."""
from pathlib import Path
import csv
import importlib.util
import json
import os
import re
import shutil
import signal
import stat
import subprocess
import sys
import time
from restore import ROOT, RECORDS, manifest, save, sha, selection, get


def preflight():
    """Construct the actual entrypoint; deliberately do not call main/setup/run_test."""
    m = manifest()
    assert json.loads((RECORDS / 'restore-result.json').read_text())['status'] == 'RESTORE_AND_STATIC_PREFLIGHT_PASS'
    source = ROOT / 'source/test/functional/wallet_sendall.py'
    assert sha(source) == m['critical_sources']['test/functional/wallet_sendall.py']
    sys.path.insert(0, str(source.parent))
    os.environ.update(BTXD=str(ROOT / 'build/bin/btxd'), BITCOIND=str(ROOT / 'build/bin/btxd'),
                      BTXCLI=str(ROOT / 'build/bin/btx-cli'), BITCOINCLI=str(ROOT / 'build/bin/btx-cli'))
    sys.argv = [str(source), '--descriptors', '--configfile=' + str(ROOT / 'build/test/config.ini'),
                '--tmpdir=' + str(ROOT / 'preflight-unused'), '--timeout-factor=1']
    spec = importlib.util.spec_from_file_location('sendall_entrypoint_preflight', source)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    case = module.SendallTest(str(source))
    case.set_binary_paths()  # Path selection only; setup/main and node startup remain uncalled.
    assert case.num_nodes == 1 and case.setup_clean_chain and case.chain == 'regtest'
    assert case.nodes == [] and case.network_thread is None and case.options.descriptors
    assert case.options.bitcoind == str(ROOT / 'build/bin/btxd')
    assert case.options.bitcoincli == str(ROOT / 'build/bin/btx-cli')
    assert not (ROOT / 'preflight-unused').exists() and not (ROOT / 'runtime').exists()
    save('controlled-preflight.json', {'status': 'ENTRYPOINT_CONSTRUCTION_PASS', 'source': m['source'],
         'class': 'SendallTest', 'nodes_created': 0, 'main_setup_run_test_called': False,
         'BTX_binaries_executed': False, 'tests_run': False, 'compiled': False})


def listeners(m):
    output = subprocess.check_output(['ss', '-H', '-ltn'], text=True, timeout=15)
    ports = []
    for line in output.splitlines():
        port = line.split()[3].rsplit(':', 1)[-1]
        if port.isdigit() and m['port_min'] <= int(port) < m['port_max_exclusive']:
            ports.append(int(port))
    return ports


def scratch_bytes(root):
    def walk_error(error):
        if not isinstance(error, FileNotFoundError):
            raise error
    total = 0
    for directory, _, names in os.walk(root, followlinks=False, onerror=walk_error):
        for name in names:
            try:
                info = (Path(directory) / name).lstat()
            except FileNotFoundError:
                continue  # Ordinary cache/SQLite cleanup may remove files while sampling.
            if stat.S_ISREG(info.st_mode):
                total += info.st_size
    return total


def bounded(sample, m):
    return (sample['seconds'] <= 1200 and sample['scratch_bytes'] <= m['bounds']['scratch_cap_bytes']
            and sample['free_disk'] >= m['bounds']['host_free_stop_min_bytes'])


def stop_group(pgid):
    """Only the fresh session this controller created; never signal the CI parent group."""
    assert pgid > 1 and pgid != os.getpgrp()
    try:
        os.killpg(pgid, signal.SIGTERM)
    except ProcessLookupError:
        return True
    for i in range(150):
        try:
            os.killpg(pgid, 0)
        except ProcessLookupError:
            return True
        if i == 100:
            os.killpg(pgid, signal.SIGKILL)
        time.sleep(0.2)
    return False


def owned_daemons():
    result = []
    for proc in Path('/proc').iterdir():
        if not proc.name.isdigit():
            continue
        try:
            args = (proc / 'cmdline').read_bytes().split(b'\0')
            if str(ROOT / 'build/bin/btxd').encode() in args and any(
                    a.startswith(('-datadir=' + str(ROOT / 'runtime')).encode()) for a in args):
                result.append(int(proc.name))
        except (FileNotFoundError, ProcessLookupError, PermissionError):
            pass
    return result


def run():
    m = manifest()
    restored = json.loads((RECORDS / 'restore-result.json').read_text())
    assert restored['status'] == 'RESTORE_AND_STATIC_PREFLIGHT_PASS' and restored['source'] == m['source']
    assert json.loads((RECORDS / 'controlled-preflight.json').read_text())['status'] == 'ENTRYPOINT_CONSTRUCTION_PASS'
    assert not (RECORDS / 'run-state.json').exists(), 'One attempt only; no automatic retry'
    assert shutil.disk_usage(ROOT).free >= m['bounds']['host_free_start_min_bytes']
    assert not listeners(m) and not owned_daemons()
    runtime = ROOT / 'runtime'
    assert not runtime.exists()
    runtime.mkdir()
    for name in ('home', 'xdg'):
        (runtime / name).mkdir(mode=0o700)
    selection(ROOT / 'source', m)
    for name, expected in m['binary_sha256'].items():
        assert sha(ROOT / 'build/bin' / name) == expected
    argv = [sys.executable, str(ROOT / 'source/test/functional/test_runner.py'), 'wallet_sendall.py',
            '--filter=' + m['filter'], '--jobs=1', '--configfile=' + str(ROOT / 'build/test/config.ini'),
            '--tmpdirprefix=' + str(runtime), '--resultsfile=' + str(RECORDS / 'functional-results.csv'),
            '--timeout-factor=1', '--randomseed=783', '--nocleanup']
    env = dict(os.environ)
    for key in ('GH_TOKEN', 'GITHUB_TOKEN'):
        env.pop(key, None)
    env.update(HOME=str(runtime / 'home'), XDG_RUNTIME_DIR=str(runtime / 'xdg'),
               BTXD=str(ROOT / 'build/bin/btxd'), BITCOIND=str(ROOT / 'build/bin/btxd'),
               BTXCLI=str(ROOT / 'build/bin/btx-cli'), BITCOINCLI=str(ROOT / 'build/bin/btx-cli'),
               TEST_RUNNER_PORT_MIN=str(m['port_min']), BTX_MATMUL_BACKEND='cpu',
               BTX_MATMUL_V4_BACKEND='cpu', BTX_MATMUL_REQUIRE_BACKEND='cpu')
    save('invocation.json', {'argv': argv, 'source': m['source'], 'selected': m['selected'],
         'binary_sha256': m['binary_sha256'], 'profile': 'Normal framework economic/CPU diagnostic regtest; no method overrides',
         'runtime_bound_s': 1200, 'compiled': False})
    state = {'status': 'STARTING', 'attempts': 1, 'compiled': False, 'runner_exit': None, 'samples': []}
    with get('repos/btxchain/btx/git/ref/heads/release-0.34.17') as response:
        head = json.load(response)
    assert head['object']['sha'] == m['source'], 'Head changed after restore; stop, do not retarget'
    save('execution-head.json', head)
    save('run-state.json', state)
    process = None
    start = time.monotonic()
    try:
        with (RECORDS / 'runner.log').open('w') as log:
            process = subprocess.Popen(argv, env=env, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
            state.update(status='RUNNING', pgid=process.pid)
            save('run-state.json', state)
            while process.poll() is None:
                elapsed = time.monotonic() - start
                sample = {'seconds': round(elapsed, 1), 'scratch_bytes': scratch_bytes(runtime),
                          'free_disk': shutil.disk_usage(ROOT).free}
                state['samples'].append(sample)
                if (elapsed >= 1200 or sample['scratch_bytes'] > m['bounds']['scratch_cap_bytes']
                        or sample['free_disk'] < m['bounds']['host_free_stop_min_bytes']):
                    state['stop_reason'] = 'runtime_bound' if elapsed >= 1200 else 'resource_bound'
                    raise RuntimeError(state['stop_reason'])
                print('normal-runner progress', sample, flush=True)
                time.sleep(min(5, max(0.05, 1200 - elapsed)))
            state['runner_exit'] = process.returncode
            final = {'seconds': time.monotonic() - start, 'scratch_bytes': scratch_bytes(runtime),
                     'free_disk': shutil.disk_usage(ROOT).free}
            state['final_sample'] = final
            state['bounds_passed'] = bounded(final, m)
            state['status'] = 'RUNNER_PASSED' if process.returncode == 0 else 'RUNNER_FAILED'
            if not state['bounds_passed']:
                state.update(status='BOUND_STOP', stop_reason='final_sample_outside_bounds')
    finally:
        if process is not None:
            if process.poll() is None:
                try:
                    os.killpg(process.pid, signal.SIGTERM)
                except ProcessLookupError:
                    pass
                try:
                    process.wait(timeout=20)
                except subprocess.TimeoutExpired:
                    os.killpg(process.pid, signal.SIGKILL)
                    process.wait(timeout=5)
            # Reap the direct child before checking group absence, so its zombie
            # cannot turn a completed cleanup into a false failure.
            state['process_group_quiescent'] = stop_group(process.pid)
        else:
            state['process_group_quiescent'] = True
        state['elapsed_seconds'] = round(time.monotonic() - start, 2)
        state['owned_daemons_remaining'] = owned_daemons()
        if state['status'] in ('STARTING', 'RUNNING'):
            state['status'] = 'BOUND_STOP' if state.get('stop_reason') else 'CONTROLLER_FAILED'
        save('run-state.json', state)
    assert state['status'] == 'RUNNER_PASSED' and state['bounds_passed']
    assert state['process_group_quiescent'] and not state['owned_daemons_remaining']


def collect():
    """Always preserve logs; qualification is stricter than runner exit0 or a green job."""
    m = manifest()
    state_path = RECORDS / 'run-state.json'
    state = json.loads(state_path.read_text()) if state_path.exists() else {'status': 'NOT_STARTED'}
    # An externally killed controller may have left its known group alive.
    if state.get('pgid') and state['status'] == 'RUNNING':
        state['process_group_quiescent'] = stop_group(state['pgid'])
        state['status'] = 'INTERRUPTED'
        save('run-state.json', state)
    result = {'source': m['source'], 'selected': m['selected'], 'scenario_calls_in_source': 24,
              'compiled': False, 'status': 'NOT_QUALIFIED', 'run_state': state}
    runtime = ROOT / 'runtime'
    logs = RECORDS / 'logs'
    logs.mkdir(exist_ok=True)
    index = []
    if runtime.exists():
        for path in sorted(runtime.rglob('*')):
            if path.is_file() and not path.is_symlink() and path.name in ('debug.log', 'test_framework.log'):
                dest = logs / f'{len(index):03d}-{path.name}'
                shutil.copy2(path, dest)
                index.append({'original': str(path.relative_to(runtime)), 'file': str(dest.relative_to(RECORDS)),
                              'sha256': sha(dest)})
    save('logs-index.json', index)
    try:
        assert state['status'] == 'RUNNER_PASSED' and state['runner_exit'] == 0
        assert state['bounds_passed'] and bounded(state['final_sample'], m)
        assert state['process_group_quiescent'] and not owned_daemons() and not listeners(m)
        with (RECORDS / 'functional-results.csv').open(newline='') as stream:
            reader = csv.DictReader(stream)
            assert reader.fieldnames == ['test', 'status', 'duration(seconds)']
            rows = list(reader)
        assert len(rows) == 2 and [r['test'] for r in rows] == m['selected'] + ['ALL']
        assert all(r['status'] == 'Passed' for r in rows)
        case_logs = [runtime / row['original'] for row in index if row['file'].endswith('test_framework.log')
                     and Path(row['original']).parent.name.startswith('wallet_sendall_')]
        cache_logs = [runtime / row['original'] for row in index if row['file'].endswith('test_framework.log')
                      and Path(row['original']).parent.name == 'cache_setup']
        assert len(case_logs) == len(cache_logs) == 1
        text = case_logs[0].read_text(errors='replace')
        assert 'Test that sendall fails if resulting transaction is too large' in text and 'Tests successful' in text
        assert 'Tests successful' in cache_logs[0].read_text(errors='replace')
        # Cache debug.log is deliberately deleted by the normal framework; its successful
        # setup includes the unchanged199-height assertion. Do not invent a missing-log failure.
        configs = []
        for path in runtime.rglob('bitcoin.conf'):
            lines = path.read_text().splitlines()
            assert lines[0] == 'regtest=1' and lines.count('connect=0') == 1
            configs.append({'path': str(path.relative_to(runtime)), 'regtest': True, 'connect_zero_count': 1})
        assert configs
        save('regtest-config-summary.json', configs)  # Never upload RPC passwords or wallet databases.
        selection(ROOT / 'source', m)
        for name, expected in m['critical_sources'].items():
            assert sha(ROOT / 'source' / name) == expected
        for name, expected in m['binary_sha256'].items():
            assert sha(ROOT / 'build/bin' / name) == expected
        result.update(status='SCOPED_NORMAL_RUNNER_PASS', rows=rows, binary_sha256=m['binary_sha256'],
                      limits='One descriptor script and its24source calls on Ubuntu economic/CPU regtest; not full suite/branch coverage')
    except BaseException as error:
        result['failure'] = str(error) or type(error).__name__
        if state.get('stop_reason') or state['status'] in ('CONTROLLER_FAILED', 'INTERRUPTED'):
            result['failure_class'] = 'controller_or_bound_stop'
        elif state['status'] == 'NOT_STARTED':
            result['failure_class'] = 'restore_or_preparation'
        elif not (RECORDS / 'functional-results.csv').exists():
            result['failure_class'] = 'runner_or_cache_setup'
        elif state['status'] == 'RUNNER_PASSED':
            result['failure_class'] = 'qualification_or_evidence_check'
        else:
            result['failure_class'] = 'test_or_runner_failure_unclassified_not_a_product_defect_claim'
    finally:
        save('qualification.json', result)
    # Preserve logs first. Only remove disposable data once affirmative shutdown is proven.
    cleanup_safe = bool(state.get('process_group_quiescent')) and not owned_daemons() and not listeners(m)
    if cleanup_safe and runtime.exists():
        shutil.rmtree(runtime)
    save('cleanup.json', {'runtime_removed': cleanup_safe, 'owned_daemons_remaining': owned_daemons(),
                         'remaining_listeners': listeners(m), 'logs_preserved': True})
    assert result['status'] == 'SCOPED_NORMAL_RUNNER_PASS', result.get('failure', 'Not qualified')


if __name__ == '__main__':
    assert Path.cwd() == ROOT and os.environ['GITHUB_REPOSITORY'] == 'sunnyriverr/btx'
    assert sys.argv[1:] in [['preflight'], ['run'], ['collect']]
    {'preflight': preflight, 'run': run, 'collect': collect}[sys.argv[1]]()
