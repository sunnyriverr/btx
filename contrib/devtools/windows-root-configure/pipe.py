"""One maintained AHP_PIPE object and its existing runtime suite; not full units."""
from pathlib import Path
import hashlib, json, os, re, shutil, stat, subprocess, sys
import checkpoint
import integration_support as s

P = Path(__file__).resolve().parent
I = json.loads((P / 'pipe-inputs.json').read_text())
ROOT, SOURCE, BUILD, E = s.ROOT, s.SOURCE, s.BUILD, s.E
s.STATE = E / 'maintained.json'
s.R = json.loads(s.STATE.read_text())
R, sha = s.R, checkpoint.digest
TARGET = 'src/test/CMakeFiles/test_btx.dir/modelnet_ahp_comp_tests.cpp.obj'


def config():
    return {n: sha(BUILD / n) for n in R['configuration']}


def plan(label, manifest, target, limit):
    cmd = ['ninja', '-C', str(BUILD), '-f', str(manifest)]
    s.need(label + '-plan', cmd + ['-n', '-d', 'explain', target], 120)
    text = (E / (label + '-plan.log')).read_text(errors='replace')
    steps = re.findall(r'^\[(\d+)/(\d+)\]', text, re.M)
    count = int(steps[-1][1]) if steps else 0
    R.setdefault('scoped_plans', {})[label] = count
    s.save()
    assert 0 < count <= limit, ('Unexpected broad rebuild', label, count)
    assert 'Re-running CMake' not in text and 'stored deps info out of date' not in text
    if label.endswith('-object'):
        expected = {
            'Generating bitcoin-build-info.h',
            'Building CXX object src/CMakeFiles/bitcoin_clientversion.dir/clientversion.cpp.obj',
            'Building CXX object src/CMakeFiles/bitcoin_common.dir/matmul/matmul_v4_rc_production_canary.cpp.obj',
            'Building CXX object src/CMakeFiles/bitcoin_common.dir/matmul/matmul_v4_rc_production_golden_manifest.cpp.obj',
            'Building CXX object ' + TARGET,
            'Linking CXX static library lib/bitcoin_clientversion.lib',
            'Linking CXX static library lib/bitcoin_common.lib',
            'Linking CXX executable bin/btxd.exe',
            'Linking CXX executable bin/btx-modeld.exe',
            'Linking CXX executable bin/btx-open.exe',
        }
        observed = re.findall(r'^\[\d+/\d+\] (.+)', text, re.M)
        assert observed and all(x.replace('\\', '/').strip() in expected for x in observed), observed
    return cmd


def component_manifest():
    text = (BUILD / 'build.ninja').read_text()
    blocks = re.findall(r'^build bin[\\/]test_btx\.exe:.*?(?=\n\n)', text, re.M | re.S)
    assert len(blocks) == 1
    first, rest = blocks[0].split('\n', 1)
    rule = first.split(': ', 1)[1].split(' ', 1)[0]
    suffix = first[first.index(' | '):]
    names = ['main.cpp', 'modelnet_ahp_comp_tests.cpp', 'util/sdk_process.cpp',
             '__/lightwatch.cpp', '__/wallet/test/init_test_fixture.cpp',
             '__/wallet/test/wallet_test_fixture.cpp']
    wanted = ['src/test/CMakeFiles/test_btx.dir/' + f + '.obj' for f in names]
    maintained = first.split(': ', 1)[1].split(' | ', 1)[0].split()[1:]
    by_path = {x.replace('\\', '/'): x for x in maintained}
    assert all(sum(y.replace('\\', '/') == x for y in maintained) == 1 for x in wanted)
    first = 'build bin/windows_pipe_fixture.exe: ' + rule + ' ' + ' '.join(by_path[x] for x in wanted) + suffix
    block = (first + '\n' + rest).replace('test_btx.exe', 'windows_pipe_fixture.exe').replace('test_btx.pdb', 'windows_pipe_fixture.pdb')
    block = re.sub(r'  RSP_FILE = .*', '  RSP_FILE = CMakeFiles/windows_pipe_fixture.rsp', block)
    block = re.sub(r'  TARGET_IMPLIB = .*', '  TARGET_IMPLIB = lib/windows_pipe_fixture.lib', block)
    assert '/FORCE:MULTIPLE' not in block
    path = E / 'pipe-component.ninja'
    path.write_text(text + '\n# Explicitly scoped existing AHP_PIPE runtime suite.\n' + block + '\n')
    R['component_manifest'] = {'sha256': sha(path), 'objects': names, 'link': block}
    s.save()
    return path


def qualify():
    assert R['status'] == 'NORMAL_CONFIGURED' and R['configuration_validated']
    assert R['source'] == I['base'] and config() == R['configuration']
    # Use installed Git Bash rather than the optional WSL launcher. The unchanged
    # source-gating script accepts a normal GCC-style CXX driver explicitly.
    bashdir = Path('C:/Program Files/Git/bin')
    assert (bashdir / 'bash.exe').is_file()
    os.environ['PATH'] = str(bashdir) + os.pathsep + os.environ['PATH']
    os.environ['CXX'] = 'clang++'
    R['script_environment'] = {'bash': str(bashdir / 'bash.exe'), 'CXX': 'clang++',
                               'script_sha256': sha(SOURCE / 'contrib/modelnet/check-with-modelnet-off.sh')}
    s.need('bash-prerequisite', ['bash', '--version'], 30)
    s.need('probe-compiler-prerequisite', ['clang++', '--version'], 30)
    s.need('bash-tool-prerequisites', ['bash', '-c', 'command -v bash awk grep mktemp clang++; type mapfile'], 30)
    rows = json.loads((BUILD / 'compile_commands.json').read_text())
    entries = [x for x in rows if x['file'].replace('\\', '/').endswith('/' + I['file'])
               and '/test_btx.dir/' in x['output'].replace('\\', '/')]
    assert len(entries) == 1
    R['same_generated_compiler_entry'] = entries[0]
    assert sha(SOURCE / I['file']) == I['base_sha256']
    assert not (BUILD / TARGET).exists(), 'Baseline output should be absent after original failure'
    s.need('verify-globs', ['cmake', '-P', str(BUILD / 'CMakeFiles/VerifyGlobs.cmake')], 120, cwd=BUILD)
    assert 'GLOB mismatch!' not in (E / 'verify-globs.log').read_text()
    manifest = E / 'normal-maintained.ninja'
    shutil.copyfile(BUILD / 'build.ninja', manifest)
    assert sha(manifest) == R['configuration']['build.ninja']
    cmd = plan('baseline-object', manifest, TARGET, 12)
    code = s.run('baseline-object', cmd + ['--verbose', '-j', '1', TARGET], 300)
    log = (E / 'baseline-object.log').read_text(errors='replace')
    R['baseline_object_exit'] = code
    s.save()
    assert code != 0 and "undeclared identifier 'popen'" in log and "undeclared identifier 'pclose'" in log
    assert not (BUILD / TARGET).exists()
    s.need('pipe-candidate-checkout', ['git', 'checkout', '--detach', I['target']], 60)
    changed = subprocess.check_output(['git', 'diff', '--name-only', I['base'], I['target']], cwd=SOURCE, text=True).splitlines()
    assert changed == [I['file']]
    assert subprocess.check_output(['git', 'rev-parse', 'HEAD^{tree}'], cwd=SOURCE, text=True).strip() == I['tree']
    cat = s.catalog(I['target'], 'pipe-candidate')
    assert [k for k in cat['files'] if cat['files'][k] != R['source_catalog']['files'][k]] == changed
    R['source'], R['source_catalog'] = I['target'], cat
    R['profile'].update(source=I['target'], scope=I['scope'], controller_sha256=sha(P / 'pipe.py'), qualification='AHP_PIPE component only; full maintained graph retained')
    R['candidate_only_cpp_input_changed'] = True
    s.save()
    assert sha(SOURCE / I['file']) == I['candidate_sha256']
    assert config() == R['configuration'] and sha(manifest) == R['configuration']['build.ninja']
    assert json.loads((BUILD / 'compile_commands.json').read_text()) == rows
    cmd = plan('candidate-object', manifest, TARGET, 12)
    s.need('candidate-object', cmd + ['--verbose', '-j', '1', TARGET], 300)
    R['candidate_object_sha256'] = sha(BUILD / TARGET)
    R['candidate_object_exit'] = 0
    s.save()
    component = component_manifest()
    cmd = plan('pipe-component', component, 'bin/windows_pipe_fixture.exe', 40)
    s.need('pipe-component-build', cmd + ['--verbose', '-j', '4', '-k', '1', 'bin/windows_pipe_fixture.exe'], 900)
    exe = BUILD / 'bin/windows_pipe_fixture.exe'
    R['component_binary_sha256'] = sha(exe)
    s.need('pipe-component-imports', ['dumpbin', '/dependents', str(exe)], 60)
    data = Path('D:/pf' + os.environ['GITHUB_RUN_ID'])
    assert not data.exists() and not s.owned_processes()
    data.mkdir(); (data / 'tmp').mkdir()
    R['unit_data'] = str(data)
    prior = {k: os.environ.get(k) for k in ['TMP', 'TEMP']}
    os.environ['TMP'] = os.environ['TEMP'] = str(data / 'tmp')
    R['status'] = 'AHP_PIPE_COMPONENT_RUNNING'; s.save()
    try:
        code = s.run('pipe-existing-suite', [str(exe), '--run_test=modelnet_ahp_comp_tests',
            '--log_level=all', '--report_level=detailed', '--catch_system_errors=yes',
            '--', '-testdatadir=' + str(data / 'node')], 180)
    finally:
        for k, value in prior.items():
            if value is None: os.environ.pop(k, None)
            else: os.environ[k] = value
    text = (E / 'pipe-existing-suite.log').read_text(errors='replace')
    announced = re.search(r'Running (\d+) test cases?', text)
    completed = re.search(r'Test module "Bitcoin Core Test Suite" has passed with:\s+(\d+) test cases? out of (\d+) passed', text)
    R['runtime_exit'] = code
    R['cases_announced'] = int(announced.group(1)) if announced else 0
    R['cases_completed'] = int(completed.group(1)) if completed else 0
    assert sha(exe) == R['component_binary_sha256']
    R['status'] = 'AHP_PIPE_FIXTURE_PASS' if code == 0 and R['cases_completed'] == R['cases_announced'] == I['expected_cases'] else 'AHP_PIPE_RUNTIME_FAILURE'
    s.save()
    assert R['status'] == 'AHP_PIPE_FIXTURE_PASS', 'Existing valid compatibility controls must pass'


def retain():
    assert not R['process_active'] and R.get('cleanup_confirmed', True)
    assert R.get('configuration_validated'), 'Do not retain an unvalidated generated graph'
    R['owned_processes_before_retention'] = s.owned_processes()
    s.quiesce()
    if R['owned_processes_before_retention']: R['status'] = 'OWNED_CLEANUP_REQUIRED'
    if R.get('unit_data'):
        data = Path(R['unit_data'])
        assert data.parent == Path('D:/') and data.name == 'pf' + os.environ['GITHUB_RUN_ID']
        def readonly(function, filename, exc_info):
            path = Path(filename); error = exc_info[1]
            assert path.resolve().is_relative_to(data.resolve())
            if not isinstance(error, PermissionError) or path.stat().st_mode & stat.S_IWRITE: raise error
            R.setdefault('readonly_cleanup_paths', []).append(str(path))
            os.chmod(path, stat.S_IREAD | stat.S_IWRITE); function(filename)
        if data.exists(): shutil.rmtree(data, onerror=readonly)
        R['runtime_data_removed'] = not data.exists()
    assert config() == R['configuration']
    assert s.catalog(R['source'], 'pipe-retained') == R['source_catalog']
    for n, h in R['actual_profile']['openssl_files'].items(): assert sha(ROOT / 'openssl-3.5.4-static' / n) == h
    for n, h in R['dependencies_after'].items(): assert sha(ROOT / n) == h
    R['checkpoint_capture'] = checkpoint.capture(ROOT, SOURCE, R['profile'], R['source_catalog'], {'status': R['status'], 'full_unit_qualified': False})
    shutil.copyfile(BUILD / 'btx-checkpoint.json', E / 'pipe-checkpoint.json')
    cp = json.loads((BUILD / 'btx-checkpoint.json').read_text())
    R['objects_retained'] = sum(k.endswith('.obj') for k in cp['files'])
    R['checkpoint_sha256'] = sha(BUILD / 'btx-checkpoint.json')
    R['checkpoint_key'] = hashlib.sha256(json.dumps(R['profile'], sort_keys=True).encode()).hexdigest()
    R['retention_verified'] = True; s.save()
    with open(os.environ['GITHUB_OUTPUT'], 'a') as f: f.write('checkpoint_valid=true\ncheckpoint_key=' + R['checkpoint_key'] + '\n')


def verdict():
    assert R['status'] == 'AHP_PIPE_FIXTURE_PASS' and R.get('retention_verified') and R.get('runtime_data_removed') and not R.get('owned_processes_before_retention')


stage = sys.argv[1]
try:
    {'qualify': qualify, 'retain': retain, 'verdict': verdict}[stage]()
except BaseException as ex:
    R.setdefault('failures', []).append({'stage': stage, 'type': type(ex).__name__, 'error': str(ex)})
    s.save(); print(type(ex).__name__, str(ex), flush=True); raise
finally:
    s.save(); print(json.dumps({k: R.get(k) for k in ['status', 'baseline_object_exit', 'candidate_object_exit', 'runtime_exit', 'cases_completed', 'objects_retained']}, indent=2), flush=True)
