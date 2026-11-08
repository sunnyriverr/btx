"""Bounded pending-only Windows suite execution; reuse verified full.py prepare."""
from pathlib import Path
import json, os, shutil, stat, sys, time
import subprocess
import checkpoint
import integration_support as s
from batch_results import classify

P = Path(__file__).resolve().parent
M = json.loads((P / 'completion-manifest.json').read_text())
I = json.loads((P / 'maintained-inputs.json').read_text())
s.STATE = s.E / 'maintained.json'
s.R = json.loads(s.STATE.read_text())
R, sha = s.R, checkpoint.digest


def save_progress():
    (s.E / 'batch-results.json').write_text(json.dumps(R['batch_results'], indent=2) + '\n')
    s.save()


def run():
    from job_tree import ProcessTree
    tree = ProcessTree()
    # Preserve handle until Python exits, including unhandled-error cleanup.
    globals()['process_tree'] = tree
    assert R['status'] == 'RESTORED_BINARY_READY'
    exe = s.BUILD / 'bin/test_btx.exe'
    assert sha(exe) == M['binary_sha256'] and M['source'] == json.loads((P/'current-inputs.json').read_text())['target']
    assert not s.owned_processes()
    data = Path('D:/bc' + os.environ['GITHUB_RUN_ID'])
    assert not data.exists() and not Path('S:/').exists()
    data.mkdir(); (data / 'tmp').mkdir()
    R.update(unit_data=str(data), status='BATCHES_RUNNING', batch_results=[], unit_invoked=True)
    s.need('unit-bash-version', [str(Path('C:/Program Files/Git/bin/bash.exe')), '--version'],30)
    R['runtime_binary_sha256']=M['binary_sha256']
    assert os.environ.get('BTX_EXTENDED_CHAINSTATE_TESTS') == '1'
    R['extended_snapshot_environment'] = {'BTX_EXTENDED_CHAINSTATE_TESTS': '1', 'activation_overrides': [], 'file_backed_fixture': True, 'native_free_bytes': shutil.disk_usage('D:/').free}
    assert R['extended_snapshot_environment']['native_free_bytes'] > 4*1024**3
    R['process_tree_policy'] = 'Nested private Windows job; no breakaway; kill descendants on controller exit'
    child = subprocess.Popen([sys.executable, '-c', 'import time;time.sleep(1)'])
    assert tree.active() >= 2
    child.wait(timeout=10)
    assert tree.active() == 1
    R['process_tree_control_passed'] = True
    prior = {k: os.environ.get(k) for k in ['TMP', 'TEMP', 'PATH', 'CXX']}
    os.environ['TMP'] = os.environ['TEMP'] = str(data / 'tmp')
    bash = Path('C:/Program Files/Git/bin/bash.exe')
    assert bash.is_file()
    os.environ['PATH'] = str(bash.parent) + os.pathsep + os.environ['PATH']
    os.environ['CXX'] = 'clang++'
    s.need('unit-cmd-bash-resolution',['cmd','/d','/c','where bash'],30)
    assert Path((s.E/'unit-cmd-bash-resolution.log').read_text().splitlines()[0]).resolve()==bash.resolve()
    s.need('unit-probe-compiler',['clang++','--version'],30)
    start = time.monotonic()
    # One known small pending suite first validates real selector/XML compatibility.
    jobs = sorted(enumerate(M['jobs']), key=lambda x: (x[1]['suite'] != 'modelnet_native_http_tests', x[0]))
    batch, batch_start = 1, start
    mapped = False
    try:
        s.need('map-short-batch-root', ['subst', 'S:', str(data)], 15)
        mapped = True
        R['mapped_short_roots'] = True
        for index, job in jobs:
            now = time.monotonic()
            cap = job['timeout_seconds']
            if now - batch_start + cap > M['batch_budget_seconds']:
                batch += 1; batch_start = now
            if batch > 100 or now - start + cap > M['campaign_test_budget_seconds']:
                R['campaign_stop'] = 'PLANNED_CHECKPOINT_BUDGET'; break
            label = 'suite-' + str(index).zfill(4)
            short_root=Path('S:/'+format(index,'x'));short_root.mkdir()
            short_tmp=short_root/'t';short_tmp.mkdir()
            os.environ['TMP']=os.environ['TEMP']=str(short_tmp)
            report = s.E / (label + '.xml')
            selectors = job['selectors']
            assert selectors and len(set(selectors)) == job['expected_cases']
            selector = ':'.join(selectors)
            assert len(selector) < 26000, 'Selector exceeds safe Windows command length'
            cmd = [str(exe), '--run_test=' + selector, '--log_level=test_suite',
                   '--report_level=detailed', '--report_format=XML', '--report_sink=' + str(report),
                   '--catch_system_errors=yes', '--', '-testdatadir=S:/' + format(index, 'x')]
            before = len(R['commands'])
            try:
                code = s.run(label, cmd, cap)
            except RuntimeError:
                assert len(R['commands']) == before + 1
                row = R['commands'][-1]
                assert row['label'] == label and row['budget_stop'], 'Unexpected execution failure'
                code = row['exit']
            row = R['commands'][-1]
            outcome = classify(selectors, (s.E / (label + '.log')).read_text(errors='replace'),
                               report.read_text(errors='replace') if report.exists() else '',
                               code, row['budget_stop'])
            outcome.update(suite=job['suite'], batch=batch, seconds=row['seconds'],
                           log_sha256=row['log_sha256'], report_sha256=sha(report) if report.exists() else None)
            R['batch_results'].append(outcome); save_progress()
            assert sha(exe) == M['binary_sha256']
            active = tree.active()
            outcome['job_active_processes_after_suite'] = active
            save_progress()
            if active != 1:
                R['job_unexpected_active_processes'] = active
                save_progress(); s.quiesce()
                raise RuntimeError('Suite left owned processes; stopping after cleanup')
            if outcome['state'] in ('selection_or_report_incomplete', 'resource_stop', 'incomplete'):
                raise RuntimeError('Selection/report/resource boundary requires review before more execution')
            if len(R['batch_results']) == 1 and M.get('require_first_pass_control', True):
                assert outcome['state'] == 'passed', 'Initial real selector/XML control failed'
                assert all(int(v.get('assertions_passed','0')) > 0 for c,v in outcome['cases'].items() if c in selectors), 'Initial grouping control has an empty test body'
                R['mixed_suite_pilot'] = dict(passed=True, cases=len(selectors), suites=len({c.split('/')[0]for c in selectors}), substantive_assertions=True, owned_processes=active)
                save_progress()
            print('CHECKPOINT', job['suite'], outcome['state'], len(outcome['cases']), flush=True)
        else:
            R['campaign_stop'] = 'ALL_PENDING_JOBS_ATTEMPTED'
        R['status'] = 'CURRENT_UNIT_RESULTS_RECORDED'
        save_progress()
    finally:
        R['test_wall_seconds'] = round(time.monotonic() - start, 2)
        tails=[]
        for debug in sorted(data.rglob('debug.log'))[:8]:
            with debug.open('rb') as f:
                f.seek(max(0, debug.stat().st_size - 256*1024)); content=f.read(256*1024)
            target=s.E/('snapshot-debug-tail-'+str(len(tails))+'.log');target.write_bytes(content)
            tails.append({'relative_path': str(debug.relative_to(data)), 'original_bytes':debug.stat().st_size, 'tail_bytes':len(content), 'tail_sha256':sha(target)})
        R['snapshot_debug_tails']=tails
        for key, value in prior.items():
            if value is None: os.environ.pop(key, None)
            else: os.environ[key] = value
        if mapped:
            unmap = subprocess.run(['subst', 'S:', '/D'], capture_output=True, timeout=15)
            (s.E / 'unmap-short-batch-root.log').write_bytes(unmap.stdout + unmap.stderr)
            R['short_drive_removed'] = unmap.returncode == 0 and not Path('S:/').exists()
            save_progress()
            assert R['short_drive_removed'], 'Short temporary mapping removal failed'
        save_progress()


def verify():
    assert not R['process_active']
    survivors = s.owned_processes()
    R['owned_processes_before_cleanup'] = survivors
    s.quiesce()
    if R.get('unit_data'):
        data = Path(R['unit_data'])
        assert data.parent == Path('D:/') and data.name == 'bc' + os.environ['GITHUB_RUN_ID']
        def readonly(function, filename, exc_info):
            path = Path(filename)
            assert path.resolve().is_relative_to(data.resolve())
            if not isinstance(exc_info[1], PermissionError) or path.stat().st_mode & stat.S_IWRITE: raise exc_info[1]
            os.chmod(path, stat.S_IREAD | stat.S_IWRITE); function(filename)
        if data.exists(): shutil.rmtree(data, onerror=readonly)
        R['runtime_data_removed'] = not data.exists()
    assert s.catalog(I['source'], 'after-batches') == R['source_catalog']
    marker = s.BUILD / 'btx-checkpoint.json'
    assert sha(marker) == I['checkpoint_sha256']
    cp = json.loads(marker.read_text())
    for name, item in cp['files'].items(): assert sha(s.ROOT / name) == item['sha256'], name
    R['cached_files_unchanged'] = len(cp['files'])
    R['cached_objects_unchanged'] = sum(x.endswith('.obj') for x in cp['files'])
    assert R['cached_objects_unchanged'] == I['objects']
    assert sha(s.BUILD / 'bin/test_btx.exe') == M['binary_sha256']
    R['cache_unchanged_verified'] = True
    s.save()
    assert not survivors and R.get('runtime_data_removed')
    if R.get('mapped_short_roots'): assert R['short_drive_removed']


try:
    {'run': run, 'verify': verify}[sys.argv[1]]()
except BaseException as ex:
    R.setdefault('failures', []).append(dict(stage=sys.argv[1], type=type(ex).__name__, error=str(ex)))
    s.save(); raise
finally:
    s.save()
