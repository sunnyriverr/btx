"""Verify restored native objects; regenerate normal CMake graph; inspect only."""
from pathlib import Path
import datetime, hashlib, json, os, re, shutil, subprocess, sys
import checkpoint
import integration_support as s

P = Path(__file__).resolve().parent
I = json.loads((P / 'plan-inputs.json').read_text())
ROOT, SOURCE, BUILD, E = s.ROOT, s.SOURCE, s.BUILD, s.E
s.STATE = E / 'build-plan.json'
s.R = json.loads(s.STATE.read_text()) if s.STATE.exists() else {
    'status': 'SETUP', 'scope': I['scope'], 'source': I['source'],
    'commands': [], 'process_active': False, 'compilation_invoked': False,
    'unit_invoked': False, 'original_cache_preserved': True,
}
R = s.R
sha = checkpoint.digest


def differences(a, b, prefix=''):
    result = {}
    for k in sorted(set(a) | set(b)):
        x, y = a.get(k), b.get(k)
        if isinstance(x, dict) and isinstance(y, dict):
            result.update(differences(x, y, prefix + k + '.'))
        elif x != y:
            result[prefix + k] = [x, y]
    return result


def cache_values():
    result = {}
    for line in (BUILD / 'CMakeCache.txt').read_text().splitlines():
        if line and not line.startswith(('#', '//')) and '=' in line:
            k, v = line.split('=', 1)
            result[k] = v
    return result


def require_settings():
    values = cache_values()
    for k in ['WITH_MODELNET:BOOL', 'BUILD_TESTS:BOOL',
              'ENABLE_WALLET:BOOL', 'WITH_ZMQ:BOOL']:
        assert values.get(k) == 'ON', (k, values.get(k))
    assert values['CMAKE_HOME_DIRECTORY:INTERNAL'].replace('\\', '/') == str(SOURCE).replace('\\', '/')
    return values


def prepare():
    setup = json.loads((E / 'result.json').read_text())
    assert setup['stages']['profile'] == 'COMPLETE'
    marker = BUILD / 'btx-checkpoint.json'
    assert sha(marker) == I['checkpoint_sha256']
    cp = json.loads(marker.read_text())
    assert cp['profile']['source'] == I['source']
    delta = differences(cp['profile']['actual_current_profile'], setup['profile'])
    allowed = json.loads((P / 'profile-transition.json').read_text())['allowed_differences']
    assert delta in [{}, allowed, {k: list(reversed(v)) for k, v in allowed.items()}], delta
    assert subprocess.check_output(['ninja', '--version'], text=True).strip() == '1.13.2'
    s.need('cached-source-fetch', ['git', 'fetch', '--no-tags', '--depth=2',
           'https://github.com/sunnyriverr/btx.git', I['source']], 180)
    s.need('cached-source-checkout', ['git', 'checkout', '--detach', I['source']], 60)
    assert subprocess.check_output(['git', 'rev-parse', 'HEAD^{tree}'], cwd=SOURCE, text=True).strip() == I['tree']
    cat = s.catalog(I['source'], 'cached')
    assert cat == cp['source_catalog']
    R['restore'] = checkpoint.restore(ROOT, SOURCE, cp['profile'], cat)
    assert R['restore']['restored']
    R['actual_profile'] = setup['profile']
    R['profile_transition'] = delta
    R['original_config'] = {n: sha(BUILD / n) for n in
        ['build.ninja', 'CMakeFiles/rules.ninja', 'CMakeCache.txt', 'compile_commands.json']}
    R['original_object_records'] = {k: v for k, v in cp['files'].items() if k.endswith('.obj')}
    assert len(R['original_object_records']) == I['objects']
    R['protected_output_records'] = {k: v for k, v in cp['files'].items()
        if k.replace('\\', '/').startswith('vcpkg-installed/') or Path(k).suffix.lower() in
        ['.obj', '.lib', '.exe', '.dll', '.a', '.o', '.pdb']}
    bookkeeping = ROOT / 'vcpkg-installed/vcpkg/compiler-file-hash-cache.json'
    assert bookkeeping.is_file()
    shutil.copyfile(bookkeeping, E / 'compiler-file-hash-cache-before.json')
    R['original_compile_entries'] = json.loads((BUILD / 'compile_commands.json').read_text())
    R['settings_before'] = require_settings()
    R['initial_resources'] = s.resources()
    assert R['initial_resources']['disk_free'] > 4 * 1024**3
    assert R['initial_resources']['available_ram'] > 2 * 1024**3
    R['status'] = 'RESTORED_VERIFIED'
    s.save()


def inspect():
    assert R['status'] == 'RESTORED_VERIFIED'
    # Use the original project configure arguments and real cache. No generated
    # graph modification, source pruning, compiler invocation or fake dependency.
    args = R['actual_profile']['args']
    assert args[0] == 'cmake' and '--preset' in args
    assert '-DWITH_MODELNET=ON' in args and '-DBUILD_TESTS=ON' in args
    # Match runner.configure(), including the preset's environment-expanded
    # pinned vcpkg toolchain and the original dependency binary cache.
    R['configure_environment'] = {
        'VCPKG_ROOT': str(ROOT / 'vcpkg'), 'VCPKG_DISABLE_METRICS': '1',
        'VCPKG_MAX_CONCURRENCY': '2',
        'VCPKG_BINARY_SOURCES': 'clear;files,' + str(ROOT / 'binary-cache') + ',readwrite'}
    os.environ.update(R['configure_environment'])
    R['status'] = 'REGENERATING'
    s.save()
    s.need('normal-cmake-regenerate', args, 900)
    R['settings_after'] = require_settings()
    R['cache_value_delta'] = differences(R['settings_before'], R['settings_after'])
    R['regenerated_config'] = {n: sha(BUILD / n) for n in R['original_config']}
    old = {x['output']: x for x in R['original_compile_entries']}
    new = {x['output']: x for x in json.loads((BUILD / 'compile_commands.json').read_text())}
    assert len(old) == len(R['original_compile_entries'])
    added, removed = sorted(new.keys() - old.keys()), sorted(old.keys() - new.keys())
    changed = sorted(k for k in old.keys() & new.keys() if old[k] != new[k])
    (E / 'compile-command-delta.json').write_text(json.dumps({
        'before_count': len(old), 'after_count': len(new),
        'added': [new[k] for k in added], 'removed': [old[k] for k in removed],
        'changed': [{'before': old[k], 'after': new[k]} for k in changed]}, indent=2) + '\n')
    R['compile_command_counts'] = {'before': len(old), 'after': len(new),
        'added': len(added), 'removed': len(removed), 'changed': len(changed)}
    R['sdk_helper_registered'] = [x for x in new.values()
        if x['file'].replace('\\', '/').endswith('/src/test/util/sdk_process.cpp')
        and '/test_btx.dir/' in x['output'].replace('\\', '/')]
    assert len(R['sdk_helper_registered']) == 1
    common = ['ninja', '-C', str(BUILD)]
    s.need('maintained-unit-plan', common + ['-n', '-d', 'explain', 'test_btx'], 120)
    # Ninja's normal -n stops at its always-dirty CMake glob bootstrap. The
    # existing audit established this behavior. First verify normal CMake globs,
    # then inspect a byte-identical copy of the freshly generated FULL manifest.
    # No graph rule, command hash, test list or object timestamp is edited.
    s.need('normal-verify-globs', ['cmake', '-P',
        str(BUILD / 'CMakeFiles/VerifyGlobs.cmake')], 120, cwd=BUILD)
    assert 'GLOB mismatch!' not in (E / 'normal-verify-globs.log').read_text()
    frozen = E / 'refreshed-full-manifest.ninja'
    shutil.copyfile(BUILD / 'build.ninja', frozen)
    R['generated_manifest_sha256'] = sha(BUILD / 'build.ninja')
    R['observed_manifest_sha256'] = sha(frozen)
    assert R['generated_manifest_sha256'] == R['observed_manifest_sha256']
    rules_before = sha(BUILD / 'CMakeFiles/rules.ninja')
    s.need('maintained-object-plan', common + ['-f', str(frozen),
        '-n', '-d', 'explain', 'test_btx'], 120)
    assert sha(BUILD / 'build.ninja') == R['generated_manifest_sha256']
    assert sha(BUILD / 'CMakeFiles/rules.ninja') == rules_before
    R['query_exits'] = {
        'unit': s.run('maintained-unit-query', common + ['-t', 'query', 'bin/test_btx.exe'], 60),
        'btx_open': s.run('btx-open-target-query', common + ['-t', 'query', 'bin/btx-open.exe'], 60)}
    plan = (E / 'maintained-object-plan.log').read_text(errors='replace')
    steps = re.findall(r'^\[(\d+)/(\d+)\]', plan, re.M)
    R['planned_steps'] = int(steps[-1][1]) if steps else 0
    R['planned_lines'] = [line for line in plan.splitlines() if re.match(r'^\[\d+/\d+\]', line)]
    R['explanations'] = {
        'command_changed': plan.count('ninja explain: command line changed for '),
        'cmake_regenerate': 'Re-running CMake' in plan,
        'rechecking_globs': 'Re-checking globbed' in plan}
    graph = (BUILD / 'build.ninja').read_text()
    R['executable_dependencies'] = {
        'unit_link_mentions_btx_open': 'btx-open' in (E / 'maintained-unit-query.log').read_text(),
        'btx_open_target_registered': 'bin/btx-open.exe' in graph.replace('\\', '/'),
        'macro_lines': [line for line in (SOURCE / 'src/test/CMakeLists.txt').read_text().splitlines()
            if 'MODELNET_BTX_OPEN_PATH=' in line]}
    R['status'] = 'PLAN_READY_FOR_BLOCKER_CLASSIFICATION'
    if removed or changed or R['planned_steps'] > 150 or any(R['explanations'].values()) or any(R['query_exits'].values()):
        R['status'] = 'PLAN_REQUIRES_EXPLANATION'
    cat = s.catalog(I['source'], 'after-regenerate')
    assert cat == json.loads((E / 'cached-candidate-source.json').read_text())
    for name, info in R['original_object_records'].items():
        assert sha(ROOT / name) == info['sha256'], name
    protected_now = {str(f.relative_to(ROOT)) for folder in ['project-build', 'vcpkg-installed']
        for f in (ROOT / folder).rglob('*') if f.is_file() and not f.is_symlink()
        and (folder == 'vcpkg-installed' or f.suffix.lower() in
             ['.obj', '.lib', '.exe', '.dll', '.a', '.o', '.pdb'])}
    R['protected_output_delta'] = {
        'added': sorted(protected_now - R['protected_output_records'].keys()),
        'removed': sorted(R['protected_output_records'].keys() - protected_now),
        'changed': [name for name, info in R['protected_output_records'].items()
                    if name in protected_now and sha(ROOT / name) != info['sha256']]}
    bookkeeping = ROOT / 'vcpkg-installed/vcpkg/compiler-file-hash-cache.json'
    shutil.copyfile(bookkeeping, E / 'compiler-file-hash-cache-after.json')
    R['bookkeeping_change'] = {
        'path': str(bookkeeping.relative_to(ROOT)),
        'before_sha256': sha(E / 'compiler-file-hash-cache-before.json'),
        'after_sha256': sha(E / 'compiler-file-hash-cache-after.json')}
    assert not R['protected_output_delta']['added'] and not R['protected_output_delta']['removed']
    assert set(R['protected_output_delta']['changed']) <= {R['bookkeeping_change']['path']}, R['protected_output_delta']
    for name, expected in R['actual_profile']['openssl_files'].items():
        assert sha(ROOT / 'openssl-3.5.4-static' / name) == expected, name
    R['protected_dependency_outputs_unchanged'] = len(protected_now) - len(R['protected_output_delta']['changed'])
    actual_objects = {str(f.relative_to(ROOT)) for f in BUILD.rglob('*.obj') if f.is_file()}
    assert actual_objects == set(R['original_object_records'])
    R['objects_unchanged'] = len(actual_objects)
    R['tracked_source_unchanged'] = True
    s.save()
    print(json.dumps({k: R.get(k) for k in ['status', 'compile_command_counts',
        'planned_steps', 'planned_lines', 'explanations', 'objects_unchanged',
        'executable_dependencies']}, indent=2), flush=True)


def retain():
    assert R['status'] in ['PLAN_READY_FOR_BLOCKER_CLASSIFICATION', 'PLAN_REQUIRES_EXPLANATION']
    assert not R['process_active']
    assert R['objects_unchanged'] == I['objects'] and R['tracked_source_unchanged']
    if R['status'] == 'PLAN_REQUIRES_EXPLANATION':
        R['checkpoint_not_saved_reason'] = 'Known broad command-spelling invalidation: original immutable cache remains the reusable predecessor; no compile or cache replacement.'
        s.save()
        return
    cat = s.catalog(I['source'], 'retained')
    profile = {'source': I['source'], 'actual_current_profile': R['actual_profile'],
        'input_checkpoint_sha256': I['checkpoint_sha256'], 'input_cache_key': I['cache_key'],
        'configuration': R['regenerated_config'], 'scope': I['scope'],
        'normal_cmake_regeneration': True, 'controls_sha256': sha(P / 'plan.py')}
    R['checkpoint_capture'] = checkpoint.capture(ROOT, SOURCE, profile, cat,
        {'status': R['status'], 'unit_built': False, 'unit_invoked': False,
         'objects_unchanged': R['objects_unchanged']})
    R['checkpoint_sha256'] = sha(BUILD / 'btx-checkpoint.json')
    R['checkpoint_key'] = hashlib.sha256(json.dumps(profile, sort_keys=True).encode()).hexdigest()
    s.save()
    with open(os.environ['GITHUB_OUTPUT'], 'a') as f:
        f.write('checkpoint_valid=true\ncheckpoint_key=' + R['checkpoint_key'] + '\n')


stage = sys.argv[1]
failed = False
try:
    {'prepare': prepare, 'inspect': inspect, 'retain': retain}[stage]()
except BaseException as ex:
    failed = True
    R.setdefault('failures', []).append({'stage': stage, 'type': type(ex).__name__, 'error': str(ex)})
    print(type(ex).__name__, str(ex), flush=True)
finally:
    s.save()
raise SystemExit(1 if failed else 0)
