"""Run four maintained file-recovery cases from an immutable cached binary."""
from pathlib import Path
import json, os, re, shutil, stat, sys, time
import checkpoint
import integration_support as s

P = Path(__file__).resolve().parent
I = json.loads((P / 'slice-inputs.json').read_text())
INPUT = json.loads((P / 'maintained-inputs.json').read_text())
s.STATE = s.E / 'maintained.json'
s.R = json.loads(s.STATE.read_text())
R, sha = s.R, checkpoint.digest


def run():
    assert R['status'] == 'RESTORED_VERIFIED'
    exe = s.BUILD / 'bin/test_btx.exe'
    assert sha(exe) == I['binary_sha256']
    data = Path('D:/fr' + os.environ['GITHUB_RUN_ID'])
    assert not data.exists() and not s.owned_processes()
    data.mkdir(); (data / 'tmp').mkdir()
    R.update(unit_data=str(data), cases=[], binary_sha256=sha(exe), status='FILE_RECOVERY_RUNNING')
    prior = {k: os.environ.get(k) for k in ['TMP', 'TEMP']}
    os.environ['TMP'] = os.environ['TEMP'] = str(data / 'tmp')
    deadline = time.monotonic() + I['total_test_timeout_seconds']
    try:
        for index, name in enumerate(I['cases']):
            remaining = deadline - time.monotonic()
            assert remaining > 0, 'Aggregate test-time budget exhausted'
            selector = I['suite'] + '/' + name
            label = 'file-case-' + str(index + 1)
            code = s.run(label, [str(exe), '--run_test=' + selector,
                '--log_level=message', '--report_level=detailed',
                '--catch_system_errors=yes', '--',
                '-testdatadir=' + str(data / ('case' + str(index + 1)))],
                min(I['case_timeout_seconds'], remaining))
            log = (s.E / (label + '.log')).read_text(errors='replace')
            announced = re.search(r'Running (\d+) test cases?', log)
            completed = re.search(r'Test module "Bitcoin Core Test Suite" has passed with:\s+(\d+) test cases? out of (\d+) passed', log)
            assertions = re.search(r'Test module "Bitcoin Core Test Suite" has passed with:.*?(\d+) assertions? out of (\d+) passed', log, re.S)
            result = {'selector': selector, 'exit': code,
                'announced': int(announced.group(1)) if announced else 0,
                'passed_selected_cases': int(completed.group(1)) if completed else 0,
                'registered_case_denominator': int(completed.group(2)) if completed else None,
                'assertions': [int(x) for x in assertions.groups()] if assertions else None}
            result['passed'] = code == 0 and result['announced'] == result['passed_selected_cases'] == 1
            R['cases'].append(result)
            assert sha(exe) == I['binary_sha256'] and not s.owned_processes()
            s.save()
        R['status'] = 'FILE_RECOVERY_PASS' if len(R['cases']) == I['expected_case_count'] and all(x['passed'] for x in R['cases']) else 'FILE_RECOVERY_FAILURE'
    finally:
        for key, value in prior.items():
            if value is None: os.environ.pop(key, None)
            else: os.environ[key] = value
        s.save()
    assert R['status'] == 'FILE_RECOVERY_PASS', 'Actual selected-case failure retained'


def verify():
    assert not R['process_active']
    R['owned_processes_before_cleanup'] = s.owned_processes()
    s.quiesce()
    assert not R['owned_processes_before_cleanup']
    if R.get('unit_data'):
        data = Path(R['unit_data'])
        assert data.parent == Path('D:/') and data.name == 'fr' + os.environ['GITHUB_RUN_ID']
        def readonly(function, filename, exc_info):
            path = Path(filename); error = exc_info[1]
            assert path.resolve().is_relative_to(data.resolve())
            if not isinstance(error, PermissionError) or path.stat().st_mode & stat.S_IWRITE: raise error
            os.chmod(path, stat.S_IREAD | stat.S_IWRITE); function(filename)
        if data.exists(): shutil.rmtree(data, onerror=readonly)
        R['runtime_data_removed'] = not data.exists()
    assert s.catalog(I['source'], 'after-file-recovery') == R['source_catalog']
    marker = s.BUILD / 'btx-checkpoint.json'
    assert sha(marker) == INPUT['checkpoint_sha256']
    cp = json.loads(marker.read_text())
    for name, record in cp['files'].items():
        assert sha(s.ROOT / name) == record['sha256'], name
    R['cached_files_unchanged'] = len(cp['files'])
    R['cached_objects_unchanged'] = sum(x.endswith('.obj') for x in cp['files'])
    assert R['cached_objects_unchanged'] == INPUT['objects']
    assert sha(s.BUILD / 'bin/test_btx.exe') == I['binary_sha256']
    R['cache_unchanged_verified'] = True
    s.save()
    assert R['status'] == 'FILE_RECOVERY_PASS' and R.get('runtime_data_removed')


try:
    {'run': run, 'verify': verify}[sys.argv[1]]()
except BaseException as ex:
    R.setdefault('failures', []).append({'stage': sys.argv[1], 'type': type(ex).__name__, 'error': str(ex)})
    s.save(); raise
finally:
    s.save()
    print(json.dumps({k: R.get(k) for k in ['status', 'cases', 'runtime_data_removed', 'cache_unchanged_verified']}, indent=2), flush=True)
