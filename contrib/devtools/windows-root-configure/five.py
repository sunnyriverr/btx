"""Five maintained Windows fixture objects with real native runtime controls."""
from pathlib import Path
import base64, hashlib, json, os, re, shutil, stat, subprocess, sys, time
import checkpoint
import integration_support as s

P = Path(__file__).resolve().parent
I = json.loads((P / 'five-inputs.json').read_text())
ROOT, SOURCE, BUILD, E = s.ROOT, s.SOURCE, s.BUILD, s.E
s.STATE = E / 'five.json'
s.R = json.loads(s.STATE.read_text()) if s.STATE.exists() else {
    'status': 'SETUP', 'commands': [], 'process_active': False, 'scope': I['scope'],
    'base': I['cached_source'], 'target': I['target'], 'unit_built': False,
    'unit_invoked': False, 'full_unit_qualified': False}
R, sha = s.R, checkpoint.digest


def diff(a, b, prefix=''):
    out = {}
    for k in sorted(set(a) | set(b)):
        x, y = a.get(k), b.get(k)
        if isinstance(x, dict) and isinstance(y, dict):
            out.update(diff(x, y, prefix + k + '.'))
        elif x != y:
            out[prefix + k] = [x, y]
    return out


def prepare():
    setup = json.loads((E / 'result.json').read_text())
    assert setup['stages']['profile'] == 'COMPLETE'
    marker = BUILD / 'btx-checkpoint.json'
    assert sha(marker) == I['checkpoint_sha256']
    cp = json.loads(marker.read_text())
    assert cp['profile']['source'] == I['cached_source']
    delta = diff(cp['profile']['actual_current_profile'], setup['profile'])
    allowed = json.loads((P / 'profile-transition.json').read_text())['allowed_differences']
    assert delta in [{}, allowed, {k: list(reversed(v)) for k, v in allowed.items()}], delta
    assert subprocess.check_output(['ninja', '--version'], text=True).strip() == '1.13.2'
    s.need('source-parent-fetch', ['git', 'fetch', '--no-tags', '--depth=2',
        'https://github.com/sunnyriverr/btx.git', I.get('public_parent', I['cached_source'])], 180)
    bundle = E / 'five-source.bundle'
    bundle.write_bytes(base64.b64decode((P / 'five-source.bundle.base64').read_text()))
    assert sha(bundle) == I['bundle_sha256']
    s.need('bundle-verify', ['git', 'bundle', 'verify', str(bundle)], 60)
    s.need('bundle-fetch', ['git', 'fetch', str(bundle), *I.get('bundle_refs', [I['bundle_ref']])], 60)
    s.need('cached-checkout', ['git', 'checkout', '--detach', I['cached_source']], 60)
    cat = s.catalog(I['cached_source'], 'cached')
    assert cat == cp['source_catalog']
    R['restore'] = checkpoint.restore(ROOT, SOURCE, cp['profile'], cat)
    assert R['restore']['restored']
    R['actual_profile'], R['host_transition'] = setup['profile'], delta
    R['original_config'] = {n: sha(BUILD / n) for n in
        ['build.ninja', 'CMakeFiles/rules.ninja', 'CMakeCache.txt', 'compile_commands.json']}
    for flag in ['WITH_MODELNET:BOOL=ON', 'BUILD_TESTS:BOOL=ON',
                 'ENABLE_WALLET:BOOL=ON', 'WITH_ZMQ:BOOL=ON']:
        assert flag in (BUILD / 'CMakeCache.txt').read_text()
    commands = json.loads((BUILD / 'compile_commands.json').read_text())
    for row in I['files']:
        matches = [x for x in commands if x['file'].replace('\\', '/').endswith('/' + row['path'])
                   and '/test_btx.dir/' in x['output'].replace('\\', '/')]
        assert matches == [row['command']]
    R['sdk_helper_sha256'] = sha(ROOT / I['sdk_cached_object'])
    assert R['sdk_helper_sha256'] == I['sdk_cached_object_sha256']
    R['reused_passing_groups'] = I['reuse_passing_groups']
    for row in I['files']:
        assert sha(BUILD / row['target']) == I['fixture_objects_guard'][row['file']]
    s.need('candidate-checkout', ['git', 'checkout', '--detach', I['target']], 60)
    changed = subprocess.check_output(['git', 'diff', '--name-only', I['cached_source'], I['target']],
                                     cwd=SOURCE, text=True).splitlines()
    assert changed == I['changed']
    assert subprocess.check_output(['git', 'rev-parse', 'HEAD^{tree}'], cwd=SOURCE, text=True).strip() == I['tree']
    candidate = s.catalog(I['target'], 'candidate-before')
    assert set(cat['files']) == set(candidate['files'])
    assert sorted(k for k in cat['files'] if cat['files'][k] != candidate['files'][k]) == changed
    original = (BUILD / 'build.ninja').read_bytes()
    graph = E / 'five.ninja'
    graph.write_bytes(original + b'\n# Scoped component using maintained fixture objects and original library closure.\n'
                      + I['component_link_block'].encode() + b'\n')
    assert graph.read_bytes().startswith(original)
    assert '/FORCE:MULTIPLE' not in I['component_link_block']
    R['graph_sha256'] = sha(graph)
    R['status'] = 'CANDIDATE_READY'
    s.save()


def build():
    assert R['status'] == 'CANDIDATE_READY'
    common = ['ninja', '-C', str(BUILD), '-f', str(E / 'five.ninja')]
    targets = ['bin/windows_fixture_five.exe', 'bin/btx-open.exe', 'bin/btx-modeld.exe', 'bin/btxd.exe']
    s.need('five-plan', common + ['-n', '-d', 'explain'] + targets, 120)
    text = (E / 'five-plan.log').read_text(errors='replace')
    steps = re.findall(r'^\[(\d+)/(\d+)\]', text, re.M)
    R['planned_steps'] = int(steps[-1][1]) if steps else 0
    assert 0 < R['planned_steps'] <= 100, R['planned_steps']
    assert 'command line changed for' not in text and 'stored deps info out of date' not in text
    assert 'Re-running CMake' not in text and 'Re-checking globbed' not in text
    assert s.resources()['disk_free'] > 4 * 1024**3
    R['status'] = 'BUILDING'
    s.save()
    code = s.run('focused-build', common + ['--verbose', '-j', '4', '-k', '1'] + targets, 1800)
    R['build_exit'] = code
    assert code == 0, 'Native compiler/link barrier; no runtime claim'
    R['binaries'] = {name: sha(BUILD / 'bin' / (name + '.exe'))
                     for name in ['windows_fixture_five', 'btx-open', 'btx-modeld', 'btxd']}
    R['fixture_objects'] = {x['file']: sha(BUILD / x['target']) for x in I['files']}
    assert R['fixture_objects'] == I['fixture_objects_guard']
    assert sha(ROOT / I['sdk_cached_object']) == R['sdk_helper_sha256']
    info = (BUILD / 'src/bitcoin-build-info.h').read_text()
    assert I['target'][:7] in info and re.search(r'BUILD_GIT_DIRTY\s+0', info)
    R['build_info'] = info
    R['status'] = 'LINKED'
    s.save()


def run():
    assert R['status'] == 'LINKED'
    exe = BUILD / 'bin/windows_fixture_five.exe'
    s.need('suite-inventory', [str(exe), '--list_content'], 60)
    data = Path('D:/f5' + os.environ['GITHUB_RUN_ID'])
    assert not data.exists()
    data.mkdir()
    R['unit_data'], R['suite_results'] = str(data), []
    old = {k: os.environ.get(k) for k in ['TMP', 'TEMP']}
    runtime_start = time.monotonic()
    for k in ['BTX_REMOTE_PROCESS_BTXD', 'BTX_MIXED_0347']:
        assert not os.environ.get(k), 'No environment-gated external/legacy binary execution'
    try:
        for idx, (suite, minimum) in enumerate(zip(I['runtime_suites'], I['minimum_cases'])):
            scratch = data / str(idx) / 'temp'
            scratch.mkdir(parents=True)
            os.environ['TMP'] = os.environ['TEMP'] = str(scratch)
            R['unit_invoked'] = True
            s.save()
            label = 'suite-' + str(idx)
            remaining = int(600 - (time.monotonic() - runtime_start))
            assert remaining > 0, 'Scoped runtime campaign exhausted its ten-minute bound'
            code = s.run(label, [str(exe), '--run_test=' + suite, '--report_level=detailed',
                '--log_level=test_suite', '--', '-testdatadir=' + str(data / str(idx) / 'node')], remaining)
            text = (E / (label + '.log')).read_text(errors='replace')
            count = re.search(r'Running (\d+) test cases?', text)
            assertions = re.search(r'(\d+) assertions? out of (\d+) passed', text)
            row = {'suite': suite, 'exit': code, 'cases_started': int(count.group(1)) if count else 0,
                'assertions': list(map(int, assertions.groups())) if assertions else None,
                'passed': code == 0 and ('Test suite "' + suite + '" has passed with:') in text,
                'owned_processes_after_suite': s.owned_processes(),
                'applicability_messages': [line for line in text.splitlines()
                    if any(x in line for x in ['NOT_RUN', 'not run', 'Symbolic links absent', 'Sparse fixture'])]}
            R['suite_results'].append(row)
            s.save()
            assert row['cases_started'] >= minimum, row
            assert not row['owned_processes_after_suite'], row
            # Keep all results, rather than lose the other supported groups if one fails.
    finally:
        for k, value in old.items():
            if value is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = value
        R['owned_processes_before_cleanup'] = s.owned_processes()
        s.quiesce()
        R['readonly_cleanup'] = []
        def denied(func, path, exc):
            file = Path(path)
            assert data in file.parents and not file.is_symlink()
            assert not file.lstat().st_file_attributes & stat.FILE_ATTRIBUTE_REPARSE_POINT
            os.chmod(file, stat.S_IREAD | stat.S_IWRITE)
            R['readonly_cleanup'].append(str(file.relative_to(data)))
            func(path)
        shutil.rmtree(data, onerror=denied)
        R['owned_data_removed'] = not data.exists()
        s.save()
    assert not R['owned_processes_before_cleanup']
    assert len(R['suite_results']) == len(I['runtime_suites']) and all(x['passed'] for x in R['suite_results']), 'Relevant native control failed'
    for name, expected in R['binaries'].items():
        assert sha(BUILD / 'bin' / (name + '.exe')) == expected
    R['status'] = 'SCOPED_RUNTIME_PASS'
    s.save()


def retain():
    assert not R['process_active'] and R.get('cleanup_confirmed', True)
    assert isinstance(R.get('build_exit'), int), 'No completed compiler attempt to checkpoint'
    s.quiesce()
    cat = s.catalog(I['target'], 'retained')
    assert cat == json.loads((E / 'candidate-before-candidate-source.json').read_text())
    assert all(sha(BUILD / name) == expected for name, expected in R['original_config'].items())
    profile = {'source': I['target'], 'actual_current_profile': R['actual_profile'],
        'input_checkpoint_sha256': I['checkpoint_sha256'], 'input_cache_key': I['cache_key'],
        'configuration': R['original_config'], 'controls_sha256': sha(P / 'five.py'),
        'source_bundle_sha256': I['bundle_sha256'], 'scope': I['scope'], 'normal_ninja_dependencies': True}
    R['checkpoint_capture'] = checkpoint.capture(ROOT, SOURCE, profile, cat,
        {'status': R['status'], 'full_unit': False, 'build_exit': R['build_exit'],
         'suite_exit': [x['exit'] for x in R.get('suite_results', [])]})
    cp = json.loads((BUILD / 'btx-checkpoint.json').read_text())
    R['objects_retained'] = sum(x.endswith('.obj') for x in cp['files'])
    R['checkpoint_sha256'] = sha(BUILD / 'btx-checkpoint.json')
    R['checkpoint_key'] = hashlib.sha256(json.dumps(profile, sort_keys=True).encode()).hexdigest()
    s.save()
    with open(os.environ['GITHUB_OUTPUT'], 'a') as f:
        f.write('checkpoint_valid=true\ncheckpoint_key=' + R['checkpoint_key'] + '\n')


stage, failed = sys.argv[1], False
try:
    {'prepare': prepare, 'build': build, 'run': run, 'retain': retain}[stage]()
except BaseException as ex:
    failed = True
    R.setdefault('failures', []).append({'stage': stage, 'type': type(ex).__name__, 'error': str(ex)})
    print(type(ex).__name__, str(ex), flush=True)
finally:
    s.save()
    print(json.dumps({k: R.get(k) for k in ['status', 'planned_steps', 'build_exit', 'suite_results', 'failures']}), flush=True)
raise SystemExit(1 if failed else 0)
