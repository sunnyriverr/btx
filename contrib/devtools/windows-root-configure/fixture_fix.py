"""Paired native fixture regression and real directory-lock/isolation controls."""
from pathlib import Path
import base64, hashlib, json, os, re, shutil, stat, subprocess, sys
import checkpoint
import integration_support as s
from batch_results import classify
from job_tree import ProcessTree

P = Path(__file__).resolve().parent
I = json.loads((P / 'fixture-fix-inputs.json').read_text())
s.STATE = s.E / 'maintained.json'; s.R = json.loads(s.STATE.read_text()); R = s.R
sha = checkpoint.digest
CASES = I['cases']


def contained():
    tree = ProcessTree()
    globals()['process_tree'] = tree
    return tree


def mapped():
    root = Path(R['unit_data'])
    assert root == Path('D:/fp' + os.environ['GITHUB_RUN_ID']) and not Path('S:/').exists()
    root.mkdir(exist_ok=True); (root / 'tmp').mkdir(exist_ok=True)
    s.need('map-' + sys.argv[1], ['subst', 'S:', str(root)], 15)
    os.environ['TMP'] = os.environ['TEMP'] = 'S:/tmp'


def unmap():
    s.need('unmap-' + sys.argv[1], ['subst', 'S:', '/D'], 15)
    R['short_drive_removed'] = not Path('S:/').exists(); s.save()
    assert R['short_drive_removed']


def cases(label, selectors, root='S:/f', timeout=60):
    report = s.E / (label + '.xml')
    cmd = [str(s.BUILD / 'bin/test_btx.exe'), '--run_test=' + ':'.join(selectors),
           '--log_level=test_suite', '--report_level=detailed', '--report_format=XML',
           '--report_sink=' + str(report), '--catch_system_errors=yes', '--']
    if root is not None: cmd.append('-testdatadir=' + root)
    code = s.run(label, cmd, timeout)
    log = (s.E / (label + '.log')).read_text(errors='replace')
    result = classify(selectors, log, report.read_text() if report.exists() else '', code)
    R.setdefault('fixture_cases', {})[label] = result; s.save()
    assert globals()['process_tree'].active() == 1, 'Unexpected descendant after unit exit'
    return result, log


def baseline():
    tree = contained()
    assert R['status'] == 'RESTORED_VERIFIED' and not s.owned_processes()
    assert sha(s.BUILD / 'bin/test_btx.exe') == I['baseline_binary_sha256']
    s.need('baseline-fixture-inventory', [str(s.BUILD / 'bin/test_btx.exe'), '--list_content'], 30)
    R['baseline_inventory_sha256'] = sha(s.E / 'baseline-fixture-inventory.log')
    R['unit_data'] = 'D:/fp' + os.environ['GITHUB_RUN_ID']; s.save()
    assert not Path(R['unit_data']).exists()
    mapped()
    try:
        result, log = cases('baseline-three', CASES)
        assert result['state'] == 'failed'
        assert all(result['cases'][k]['result'] in ('failed', 'aborted') for k in CASES)
        for k in CASES:
            assert any('in "' + k + '"' in line and 'filename or extension is too long' in line
                       for line in log.splitlines()), k
        assert sha(s.BUILD / 'bin/test_btx.exe') == I['baseline_binary_sha256']
        R['baseline_verified'] = True; R['status'] = 'BASELINE_THREE_FAIL'; s.save()
    finally: unmap()


def build():
    tree = contained()
    assert R['baseline_verified'] and not s.owned_processes()
    bundle = s.E / 'fixture-candidate.bundle'
    bundle.write_bytes(base64.b64decode((P / 'fixture-candidate.bundle.base64').read_text()))
    assert sha(bundle) == I['bundle_sha256']
    s.need('fixture-bundle-verify', ['git', 'bundle', 'verify', str(bundle)], 30)
    s.need('fixture-bundle-fetch', ['git', 'fetch', str(bundle), I['bundle_ref']], 30)
    changed = subprocess.check_output(['git', 'diff', '--name-only', I['integration_base'], I['integration']], cwd=s.SOURCE, text=True).splitlines()
    assert changed == ['src/test/util/setup_common.cpp']
    s.need('fixture-candidate-checkout', ['git', 'checkout', '--detach', I['integration']], 30)
    assert sha(s.SOURCE / changed[0]) == I['candidate_file_sha256']
    assert subprocess.check_output(['git', 'rev-parse', 'HEAD^{tree}'], cwd=s.SOURCE, text=True).strip() == I['tree']
    candidate = s.catalog(I['integration'], 'fixture-before')
    delta = [k for k in candidate['files'] if candidate['files'][k] != R['source_catalog']['files'][k]]
    assert delta == changed
    R['candidate_catalog'] = candidate
    assert not subprocess.check_output(['git', 'diff', '--name-only'], cwd=s.SOURCE, text=True).strip()
    entries = json.loads((s.BUILD / 'compile_commands.json').read_text())
    R['fixture_compile_commands'] = [x for x in entries if x['file'].replace('\\', '/').endswith('/src/test/util/setup_common.cpp')]
    assert len(R['fixture_compile_commands']) == 1
    s.need('fixture-unit-plan', ['ninja', '-C', str(s.BUILD), '-n', '-d', 'explain', 'test_btx'], 60)
    plan = (s.E / 'fixture-unit-plan.log').read_text(errors='replace')
    steps = re.findall(r'^\[(\d+)/(\d+)\]', plan, re.M)
    R['fixture_planned_steps'] = int(steps[-1][1]) if steps else 0
    assert 0 < R['fixture_planned_steps'] <= 60
    assert 'command line changed for ' not in plan and 'Re-running CMake' not in plan
    R['fixture_planned_objects'] = re.findall(r'Building CXX object ([^\r\n]+\.obj)', plan)
    assert any('setup_common.cpp.obj' in x for x in R['fixture_planned_objects'])
    R['status'] = 'FIXTURE_BUILDING'; s.save()
    s.need('fixture-unit-build', ['cmake', '--build', str(s.BUILD), '--target', 'test_btx', '--parallel', '4', '--', '-k', '1'], 900)
    for name, value in R['original_config'].items(): assert sha(s.BUILD / name) == value, name
    R['candidate_binary_sha256'] = sha(s.BUILD / 'bin/test_btx.exe')
    assert R['candidate_binary_sha256'] != I['baseline_binary_sha256']
    header = (s.BUILD / 'src/bitcoin-build-info.h').read_text()
    assert I['integration'][:7] in header and re.search(r'BUILD_GIT_DIRTY\s+0', header)
    R['build_info'] = header; R['status'] = 'FIXTURE_LINKED'; s.save()
    s.need('candidate-fixture-inventory', [str(s.BUILD / 'bin/test_btx.exe'), '--list_content'], 30)
    assert sha(s.E / 'candidate-fixture-inventory.log') == R['baseline_inventory_sha256']
    R['inventory_identical'] = True
    assert tree.active() == 1
    s.save()


def run():
    import msvcrt
    tree = contained()
    assert R['status'] == 'FIXTURE_LINKED' and not s.owned_processes()
    mapped()
    try:
        root = Path('S:/f') / 'test_common bitcoin'
        names = {k: hashlib.sha256(k.encode()).hexdigest()[:32] for k in CASES}
        assert len(set(names.values())) == 3
        first, second = CASES[:2]
        lock_root = root / names[first]
        sentinel = lock_root / 'datadir' / 'stale-sentinel'
        sentinel.parent.mkdir(parents=True, exist_ok=True); sentinel.write_bytes(b'unchanged-owner-data')
        with (lock_root / '.lock').open('w+b') as handle:
            handle.write(b'\0'); handle.flush(); handle.seek(0)
            msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            try:
                result, log = cases('same-name-lock-refusal', [first])
                assert result['exit'] != 0 and 'Cannot obtain a lock on test data lock directory' in log
                assert sentinel.read_bytes() == b'unchanged-owner-data'
                result, log = cases('different-name-isolation', [second])
                assert result['state'] == 'passed' and names[second] in log
                assert sentinel.read_bytes() == b'unchanged-owner-data'
                R['lock_refusal_and_independence_verified'] = True; s.save()
            finally:
                handle.seek(0); msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
        result, log = cases('candidate-three', CASES)
        assert result['state'] == 'passed'
        assert not sentinel.exists(), 'Fresh test setup did not clear stale owned data'
        for name in CASES:
            assert 'Test case: ' + name in log and names[name] in log
            assert not (root / names[name] / '.lock').exists()
        R['full_name_hash_mapping'] = names
        R['fresh_data_and_lock_cleanup_verified'] = True
        result, log = cases('default-temp-control', [first], root=None)
        assert result['state'] == 'passed' and 'Test case: ' + first in log
        assert not [x for x in Path('S:/tmp').rglob('*') if x.is_file()]
        R['default_temp_control_verified'] = True
        assert tree.active() == 1 and sha(s.BUILD / 'bin/test_btx.exe') == R['candidate_binary_sha256']
        R['status'] = 'FIXTURE_PATHS_PASS'; s.save()
    finally: unmap()


def retain():
    assert not R['process_active']
    survivors = s.owned_processes(); R['owned_processes_before_cleanup'] = survivors; s.quiesce()
    assert not survivors and R.get('short_drive_removed', True)
    if R.get('unit_data'):
        root = Path(R['unit_data']); assert root == Path('D:/fp' + os.environ['GITHUB_RUN_ID'])
        def readonly(fn, filename, exc):
            f = Path(filename); assert f.resolve().is_relative_to(root.resolve())
            if not isinstance(exc[1], PermissionError) or f.stat().st_mode & stat.S_IWRITE: raise exc[1]
            os.chmod(f, stat.S_IREAD | stat.S_IWRITE); fn(filename)
        if root.exists(): shutil.rmtree(root, onerror=readonly)
        R['runtime_data_removed'] = not root.exists()
    assert R['status'] == 'FIXTURE_PATHS_PASS' and R['runtime_data_removed']
    assert s.catalog(I['integration'], 'fixture-after') == R['candidate_catalog']
    for name, value in R['original_config'].items(): assert sha(s.BUILD / name) == value, name
    changes = []
    for name, item in R['original_objects'].items():
        assert (s.ROOT / name).is_file(), name
        if sha(s.ROOT / name) != item['sha256']: changes.append(name)
    planned = {'project-build/' + x.replace('\\', '/') for x in R['fixture_planned_objects']}
    assert all(x.replace('\\', '/') in planned for x in changes), changes
    assert any('setup_common.cpp.obj' in x for x in changes)
    R['changed_objects'] = changes; R['original_objects_retained'] = len(R['original_objects'])
    for name, item in R['dependencies_before'].items(): assert sha(s.ROOT / name) == item['sha256'], name
    profile = dict(source=I['integration'], actual_current_profile=R['actual_profile'],
                   configuration=R['original_config'], scope='Incremental unit fixture only; untouched node binaries remain baseline4609')
    R['checkpoint_capture'] = checkpoint.capture(s.ROOT, s.SOURCE, profile, R['candidate_catalog'],
                                               dict(status=R['status'], candidate_binary_sha256=R['candidate_binary_sha256']))
    shutil.copyfile(s.BUILD / 'btx-checkpoint.json', s.E / 'fixture-checkpoint.json')
    R['checkpoint_sha256'] = sha(s.BUILD / 'btx-checkpoint.json')
    R['checkpoint_key'] = hashlib.sha256(json.dumps(profile, sort_keys=True).encode()).hexdigest()
    R['retention_verified'] = True; s.save()
    with open(os.environ['GITHUB_OUTPUT'], 'a') as stream:
        stream.write('checkpoint_valid=true\ncheckpoint_key=' + R['checkpoint_key'] + '\n')


try:
    {'baseline': baseline, 'build': build, 'run': run, 'retain': retain}[sys.argv[1]]()
except BaseException as ex:
    R.setdefault('fixture_failures', []).append(dict(stage=sys.argv[1], type=type(ex).__name__, error=str(ex)))
    s.save(); raise
finally: s.save()
