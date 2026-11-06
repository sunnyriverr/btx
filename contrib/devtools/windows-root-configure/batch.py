"""Focused maintained Windows fixture objects; never a full-unit acceptance claim."""
from pathlib import Path
import base64, hashlib, json, os, re, shutil, subprocess, sys, time
import checkpoint
import integration_support as s

P = Path(__file__).resolve().parent
I = json.loads((P / 'batch-inputs.json').read_text())
ROOT, SOURCE, BUILD, E = s.ROOT, s.SOURCE, s.BUILD, s.E
s.STATE = E / 'batch.json'
s.R = json.loads(s.STATE.read_text()) if s.STATE.exists() else {
    'status': 'SETUP', 'commands': [], 'process_active': False,
    'full_unit_qualified': False, 'scope': I['scope']}
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


def environment():
    os.environ.update(VCPKG_ROOT=str(ROOT / 'vcpkg'), VCPKG_DISABLE_METRICS='1',
        VCPKG_MAX_CONCURRENCY='2',
        VCPKG_BINARY_SOURCES='clear;files,' + str(ROOT / 'binary-cache') + ',readwrite')


def config_hashes():
    return {n: sha(BUILD / n) for n in
        ['build.ninja', 'CMakeFiles/rules.ninja', 'CMakeCache.txt', 'compile_commands.json']}


def graph(label, files):
    # Retain every maintained compiler rule, library and flag. Only this added
    # link target selects a bounded collection of the maintained test objects.
    text = (BUILD / 'build.ninja').read_text()
    blocks = re.findall(r'^build bin[\\/]test_btx\.exe:.*?(?=\n\n)', text, re.M | re.S)
    assert len(blocks) == 1
    block = blocks[0]
    first, rest = block.split('\n', 1)
    rule = first.split(': ', 1)[1].split(' ', 1)[0]
    suffix = first[first.index(' | '):]
    objects = ['src/test/CMakeFiles/test_btx.dir/' + f + '.obj' for f in
        ['main.cpp'] + files + ['util/sdk_process.cpp', '__/lightwatch.cpp',
                              '__/wallet/test/init_test_fixture.cpp', '__/wallet/test/wallet_test_fixture.cpp']]
    maintained_objects = first.split(': ', 1)[1].split(' | ', 1)[0].split()[1:]
    by_path = {x.replace('\\', '/'): x for x in maintained_objects}
    assert all(sum(y.replace('\\', '/') == x for y in maintained_objects) == 1 for x in objects), objects
    selected = [by_path[x] for x in objects]
    output = 'windows_' + label
    first = 'build bin/' + output + '.exe: ' + rule + ' ' + ' '.join(selected) + suffix
    block = first + '\n' + rest
    block = block.replace('test_btx.exe', output + '.exe').replace('test_btx.pdb', output + '.pdb')
    block = re.sub(r'  RSP_FILE = .*', '  RSP_FILE = CMakeFiles/' + output + '.rsp', block)
    block = re.sub(r'  TARGET_IMPLIB = .*', '  TARGET_IMPLIB = lib/' + output + '.lib', block)
    assert '/FORCE:MULTIPLE' not in block
    path = E / (label + '.ninja')
    path.write_text(text + '\n# Explicitly scoped maintained fixture component.\n' + block + '\n')
    R.setdefault('graphs', {})[label] = {'sha256': sha(path), 'files': files, 'link': block}
    s.save()
    return path, 'bin/' + output + '.exe'


def build_component(label, files):
    manifest, exe = graph(label, files)
    cmd = ['ninja', '-C', str(BUILD), '-f', str(manifest)]
    targets = [exe, 'bin/btx-open.exe', 'bin/btx-modeld.exe', 'bin/btxd.exe']
    s.need(label + '-plan', cmd + ['-n', '-d', 'explain'] + targets, 120)
    text = (E / (label + '-plan.log')).read_text(errors='replace')
    steps = re.findall(r'^\[(\d+)/(\d+)\]', text, re.M)
    planned = int(steps[-1][1]) if steps else 0
    R.setdefault('planned', {})[label] = planned
    assert 0 < planned <= 220, ('Unexpected broad rebuild', planned)
    assert 'Re-running CMake' not in text
    R['status'] = label.upper() + '_BUILDING'
    s.save()
    s.need(label + '-build', cmd + ['--verbose', '-j', '4', '-k', '1'] + targets, 1800)
    path = BUILD / exe
    R.setdefault('binaries', {})[label] = sha(path)
    s.need(label + '-helper-imports', ['dumpbin', '/dependents', str(BUILD / 'bin/btx-open.exe')], 60)
    s.save()
    return path


def run_cases(label, exe, cases, expect_pass):
    assert not s.owned_processes()
    data = Path('D:/rb' + os.environ['GITHUB_RUN_ID']) / label
    data.mkdir(parents=True)
    R.setdefault('runtime_roots', []).append(str(data))
    temp = data / 'tmp'
    temp.mkdir()
    previous_temp = {key: os.environ.get(key) for key in ['TMP', 'TEMP']}
    os.environ['TMP'] = os.environ['TEMP'] = str(temp)
    try:
        for idx, selector in enumerate(cases):
            key = label + '-' + str(idx)
            code = s.run(key, [str(exe), '--run_test=' + selector, '--report_level=detailed',
                '--log_level=test_suite', '--', '-testdatadir=' + str(data / ('node' + str(idx)))], 180)
            text = (E / (key + '.log')).read_text(errors='replace')
            count = re.search(r'Running (\d+) test cases?', text)
            row = {'selector': selector, 'exit': code,
                'cases_started': int(count.group(1)) if count else 0,
                'binary_sha256': sha(exe), 'owned_processes': s.owned_processes(),
                'assertions': re.findall(r'(\d+) assertions? out of (\d+) passed', text),
                'fatal': [x for x in text.splitlines() if 'fatal error:' in x or 'error: in ' in x]}
            R.setdefault('runtime', {}).setdefault(label, []).append(row)
            s.save()
            assert row['cases_started'] > 0 and not row['owned_processes'], row
            if expect_pass:
                assert code == 0 and '*** No errors detected' in text, row
            else:
                assert code != 0 and any('fs::exists' in x for x in row['fatal']), row
    finally:
        for key, value in previous_temp.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
    shutil.rmtree(data)
    assert not data.exists()
    R.setdefault('removed_roots', []).append(str(data))
    s.save()


def prepare():
    setup = json.loads((E / 'result.json').read_text())
    assert setup['stages']['profile'] == 'COMPLETE'
    cpfile = BUILD / 'btx-checkpoint.json'
    assert sha(cpfile) == I['checkpoint_sha256']
    cp = json.loads(cpfile.read_text())
    assert cp['profile']['source'] == I['base']
    delta = diff(cp['profile']['actual_current_profile'], setup['profile'])
    allowed = json.loads((P / 'profile-transition.json').read_text())['allowed_differences']
    assert delta in [{}, allowed, {k: list(reversed(v)) for k, v in allowed.items()}], delta
    assert subprocess.check_output(['ninja', '--version'], text=True).strip() == '1.13.2'
    s.need('base-fetch', ['git', 'fetch', '--no-tags', '--depth=3',
        'https://github.com/sunnyriverr/btx.git', I['base']], 180)
    s.need('base-checkout', ['git', 'checkout', '--detach', I['base']], 60)
    cat = s.catalog(I['base'], 'base-before')
    assert cat == cp['source_catalog']
    R['restore'] = checkpoint.restore(ROOT, SOURCE, cp['profile'], cat)
    R['actual_profile'], R['profile_transition'] = setup['profile'], delta
    R['base_catalog'] = cat
    R['original_configuration'] = config_hashes()
    assert R['original_configuration'] == cp['profile']['configuration']
    R['original_objects'] = {k: v for k, v in cp['files'].items() if k.endswith('.obj')}
    assert len(R['original_objects']) == I['objects']
    R['dependencies'] = {k: v for k, v in cp['files'].items() if k.replace('\\', '/').startswith('vcpkg-installed/')}
    cache = (BUILD / 'CMakeCache.txt').read_text()
    for flag in ['WITH_MODELNET:BOOL=ON', 'BUILD_TESTS:BOOL=ON', 'ENABLE_WALLET:BOOL=ON', 'WITH_ZMQ:BOOL=ON']:
        assert flag in cache
    table = json.loads((BUILD / 'compile_commands.json').read_text())
    R['compiler_entries'] = []
    for row in I['compiler_cohort']:
        matches = [x for x in table if x['file'].replace('\\', '/').endswith('/' + row['source']) and '/test_btx.dir/' in x['output'].replace('\\', '/')]
        assert len(matches) == 1
        R['compiler_entries'].append(matches[0])
    shutil.copyfile(BUILD / 'compile_commands.json', E / 'baseline-compile-commands.json')
    R['source'] = I['base']
    R['status'] = 'BASE_VERIFIED'
    R['configuration_validated'] = True
    s.save()


def baseline():
    assert R['status'] == 'BASE_VERIFIED'
    environment()
    # Compile the exact three maintained outputs together; collect every real
    # error rather than hiding later failures behind the first one.
    s.need('baseline-compiler-plan', ['ninja', '-C', str(BUILD), '-n', '-d', 'explain'] + [x['output'] for x in I['compiler_cohort']], 120)
    plan = (E / 'baseline-compiler-plan.log').read_text(errors='replace')
    steps = re.findall(r'^\[(\d+)/(\d+)\]', plan, re.M)
    assert steps and int(steps[-1][1]) <= 220, 'Unexpected baseline-cohort rebuild'
    for row in I['compiler_cohort']:
        label = 'baseline-' + Path(row['source']).stem
        code = s.run(label, ['ninja', '-C', str(BUILD), '-v', '-k', '0', row['output']], 300)
        text = (E / (label + '.log')).read_text(errors='replace')
        errors = [x for x in text.splitlines() if 'error:' in x or 'fatal error' in x]
        R.setdefault('compile_before', []).append({'source': row['source'], 'output': row['output'], 'exit': code, 'errors': errors})
        s.save()
        expected = ['S_IRUSR', 'S_IWUSR', 'S_IXUSR'] if 'swarm_' in row['source'] else ['arpa/inet.h']
        assert code != 0 and errors and any(token in '\n'.join(errors) for token in expected), 'Intended baseline compiler discriminator missing'
    R['baseline_commands_unchanged'] = config_hashes() == R['original_configuration']
    assert R['baseline_commands_unchanged']
    exe = build_component('baseline_paths', I['path_files'])
    run_cases('baseline_paths', exe, I['path_cases'], False)
    assert s.catalog(I['base'], 'base-after') == R['base_catalog']
    R['status'] = 'BASELINE_REPRODUCED'
    s.save()


def candidate():
    assert R['status'] == 'BASELINE_REPRODUCED'
    environment()
    bundle = E / 'batch-source.bundle'
    bundle.write_bytes(base64.b64decode((P / 'batch-source.bundle.base64').read_text()))
    assert sha(bundle) == I['bundle_sha256']
    s.need('bundle-verify', ['git', 'bundle', 'verify', str(bundle)], 60)
    s.need('bundle-fetch', ['git', 'fetch', str(bundle), I['bundle_ref']], 60)
    s.need('candidate-checkout', ['git', 'checkout', '--detach', I['target']], 60)
    changed = subprocess.check_output(['git', 'diff', '--name-only', I['base'], I['target']], cwd=SOURCE, text=True).splitlines()
    assert changed == I['changed']
    assert subprocess.check_output(['git', 'rev-parse', 'HEAD^{tree}'], cwd=SOURCE, text=True).strip() == I['tree']
    R['source'], R['candidate_catalog'] = I['target'], s.catalog(I['target'], 'candidate-before')
    R['configuration_validated'] = False
    s.save()
    args = R['actual_profile']['args']
    # Prove the optional daemon does not become a configure-time requirement.
    s.need('candidate-daemon-off-configure', args + ['-DBUILD_DAEMON=OFF'], 900)
    off = (BUILD / 'CMakeCache.txt').read_text()
    assert 'BUILD_DAEMON:BOOL=OFF' in off
    s.need('candidate-normal-configure', args + ['-DBUILD_DAEMON=ON'], 900)
    assert 'BUILD_DAEMON:BOOL=ON' in (BUILD / 'CMakeCache.txt').read_text()
    old = {x['output']: x for x in json.loads((E / 'baseline-compile-commands.json').read_text())}
    new = {x['output']: x for x in json.loads((BUILD / 'compile_commands.json').read_text())}
    assert old.keys() == new.keys()
    def normalize(cmd):
        cmd = re.sub(r'-DMODELNET_(BTX_OPEN|MODELD|BTXD)_PATH=\S+', r'-DMODELNET_\1_PATH=<TARGET>', cmd)
        return re.sub(r'(?<!\S)(-I|-imsvc|/I)(\s*)("[^"\r\n]*"|[^\s]+)',
            lambda m: m.group(1) + m.group(2) + m.group(3).replace('\\', '/'), cmd)
    unexpected = [k for k in old if {**old[k], 'command': normalize(old[k]['command'])} !=
                  {**new[k], 'command': normalize(new[k]['command'])}]
    R['command_delta_count'] = sum(old[k] != new[k] for k in old)
    R['unexpected_commands'] = unexpected
    s.save()
    assert not unexpected
    test = next(x for x in new.values() if x['file'].replace('\\', '/').endswith('/src/test/swarm_confine_tests.cpp'))
    for name, exe in [('BTX_OPEN', 'btx-open'), ('MODELD', 'btx-modeld'), ('BTXD', 'btxd')]:
        assert exe + '.exe' in test['command']
    R['generated_test_command'] = test
    R['configuration'] = config_hashes()
    R['configuration_validated'] = True
    shutil.copyfile(BUILD / 'compile_commands.json', E / 'candidate-compile-commands.json')
    s.save()
    for n, h in R['actual_profile']['openssl_files'].items():
        assert sha(ROOT / 'openssl-3.5.4-static' / n) == h
    for name, row in R['dependencies'].items():
        if not name.replace('\\', '/').endswith('compiler-file-hash-cache.json'):
            assert sha(ROOT / name) == row['sha256']
    preflight = ['ninja', '-C', str(BUILD), '-n', '-d', 'explain'] + [x['output'] for x in I['compiler_cohort']]
    s.need('candidate-compiler-plan', preflight, 120)
    plan = (E / 'candidate-compiler-plan.log').read_text(errors='replace')
    steps = re.findall(r'^\[(\d+)/(\d+)\]', plan, re.M)
    assert steps and int(steps[-1][1]) <= 220, 'Unexpected compiler-cohort rebuild'
    for row in I['compiler_cohort']:
        label = 'candidate-' + Path(row['source']).stem
        s.need(label, ['ninja', '-C', str(BUILD), '-v', row['output']], 300)
        R.setdefault('compile_after', []).append({'source': row['source'], 'output': row['output'], 'sha256': sha(BUILD / row['output'])})
        s.save()
    exe = build_component('candidate_batch', I['path_files'] + [Path(x['source']).name for x in I['compiler_cohort']])
    run_cases('candidate_paths', exe, I['path_cases'] + I['launch_controls'], True)
    run_cases('candidate_platforms', exe, I['platform_cases'], True)
    R['status'] = 'SCOPED_BATCH_PASS'
    s.save()


def retain():
    assert not R.get('process_active') and R.get('configuration_validated') and R.get('cleanup_confirmed', True)
    survivors = s.owned_processes()
    R['survivors_before_retention'] = survivors
    s.quiesce()
    if survivors:
        R['status'] = 'CHILD_CLEANUP_FAILURE'
    cat = s.catalog(R['source'], 'retained')
    assert cat == R.get('candidate_catalog', R['base_catalog'])
    config = config_hashes()
    assert config == R.get('configuration', R['original_configuration'])
    for n, h in R['actual_profile']['openssl_files'].items():
        assert sha(ROOT / 'openssl-3.5.4-static' / n) == h
    for name, row in R['dependencies'].items():
        if name.replace('\\', '/').endswith('compiler-file-hash-cache.json'):
            continue
        assert sha(ROOT / name) == row['sha256']
    R['remaining_runtime_roots'] = []
    for name in R.get('runtime_roots', []):
        path = Path(name)
        assert path.parent.name == 'rb' + os.environ['GITHUB_RUN_ID']
        if path.exists():
            shutil.rmtree(path)
        assert not path.exists()
    profile = {'source': R['source'], 'actual_current_profile': R['actual_profile'],
        'configuration': config, 'scope': I['scope'], 'input_cache_key': I['cache_key'],
        'input_checkpoint_sha256': I['checkpoint_sha256'], 'controller_sha256': sha(P / 'batch.py')}
    R['checkpoint_capture'] = checkpoint.capture(ROOT, SOURCE, profile, cat,
        {'status': R['status'], 'full_unit_qualified': False})
    shutil.copyfile(BUILD / 'btx-checkpoint.json', E / 'batch-checkpoint.json')
    R['checkpoint_sha256'] = sha(BUILD / 'btx-checkpoint.json')
    R['checkpoint_key'] = hashlib.sha256(json.dumps(profile, sort_keys=True).encode()).hexdigest()
    R['objects_retained'] = sum(k.endswith('.obj') for k in json.loads((BUILD / 'btx-checkpoint.json').read_text())['files'])
    R['retention_verified'] = True
    s.save()
    with open(os.environ['GITHUB_OUTPUT'], 'a') as f:
        f.write('checkpoint_valid=true\ncheckpoint_key=' + R['checkpoint_key'] + '\n')


def verdict():
    assert R['status'] == 'SCOPED_BATCH_PASS' and not R.get('survivors_before_retention') and R.get('retention_verified'), R['status']


stage = sys.argv[1]
failed = False
try:
    {'prepare': prepare, 'baseline': baseline, 'candidate': candidate,
     'retain': retain, 'verdict': verdict}[stage]()
except BaseException as ex:
    failed = True
    R.setdefault('failures', []).append({'stage': stage, 'type': type(ex).__name__, 'error': str(ex)})
    print(type(ex).__name__, str(ex), flush=True)
finally:
    s.save()
    print(json.dumps({k: R.get(k) for k in ['status', 'source', 'planned', 'failures']}, indent=2), flush=True)
raise SystemExit(1 if failed else 0)
