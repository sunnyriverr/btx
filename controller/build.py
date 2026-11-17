"""FUTURE EXECUTION ONLY: bounded current-source build, package and verified retention.

No execution is performed by preparing this file. Never invoke an old producer.
"""
from pathlib import Path
import json
import hashlib
import os
import re
import selectors
import shutil
import signal
import subprocess
import sys
import time
from checkpoint import ROOTS, RESERVE, MAX_BYTES, create, require, restore, sha

WORKSPACE = '/home/runner/work/btx/btx'
SOURCE = '074dac167c26c1e091198f691ed5727817dba88a'
INNER = '1cbafdf6724a697a6063d99c21c9e8dd2490d8f00da6f810e7f51a9ad14a5da0'
MANIFEST = '12bb2cc692f782143b49be34f377c78d04f86512c2456ab8ff8e6e5a7a8ea229'
TARGETS = ('btxd', 'btx-cli', 'btx-util', 'btx-tx', 'btx-wallet', 'btx-qt',
           'btx-guardd', 'btx-security', 'btx-native-qualify', 'btx-modeld',
           'btx-hcpd', 'btx-hosted', 'btx-open', 'btx-capability', 'btx-capabilityd',
           'btx-modelcheck', 'btx-matmul-backend-info')
ON = ('BUILD_DAEMON', 'BUILD_CLI', 'BUILD_UTIL', 'BUILD_TX', 'BUILD_WALLET_TOOL',
      'BUILD_GUI', 'WITH_MODELNET', 'ENABLE_WALLET', 'WITH_ZMQ', 'WITH_SQLITE')
OFF = ('BUILD_TESTS', 'BUILD_GUI_TESTS', 'BUILD_BENCH', 'BUILD_FUZZ_BINARY',
       'BUILD_FOR_FUZZING', 'WITH_CCACHE', 'BTX_ENABLE_CUDA_EXPERIMENTAL',
       'BTX_ENABLE_HIP', 'BTX_ENABLE_METAL', 'BTX_ENABLE_ASCEND',
       'BTX_ENABLE_TPU_PJRT', 'BTX_ENABLE_TRAINIUM_NEURON')


def main():
    w = Path(os.environ['GITHUB_WORKSPACE']).resolve()
    require(str(w) == WORKSPACE, 'Recorded isolated absolute workspace required')
    out = w / 'build-records'
    out.mkdir(exist_ok=True)
    require(not (out / 'result.json').exists(), 'Prior build result exists')
    start = time.monotonic()
    # Workflow admits dependencies/fetch outside this controller. Leave at least
    # two minutes after setup/controller inside the 107-minute container bound.
    hard_end = start + 5820
    phase_end = min(start + 300, hard_end - 420)
    retention = False
    restored = False
    compile_pass = False
    result = {'source': SOURCE, 'verdict': 'INCOMPLETE', 'commands': [],
              'compile_pass': False, 'checkpoint_verified': False,
              'product_compile_started': False, 'product_execution_started': False,
              'product_execution_state': 'NOT_REQUESTED',
              'native_package_probes': 'Packaging helper performs disclosed isolated probes; no wallet access.'}
    env = os.environ.copy()
    last_capacity = 0

    def save():
        result['elapsed_seconds'] = time.monotonic() - start
        p = out / 'result.json.tmp'
        p.write_text(json.dumps(result, indent=2) + '\n')
        p.replace(out / 'result.json')

    def capacity():
        nonlocal last_capacity
        total = 0
        # Count all task-owned content including fetched inputs, accepted checkout,
        # package staging and diagnostics. Retention gets separate full-copy headroom.
        for directory, dirs, files in os.walk(w, followlinks=False):
            for name in files:
                p = Path(directory) / name
                if not p.is_symlink():
                    total += p.stat().st_size
        result['owned_live_bytes'] = total
        require(total <= MAX_BYTES, '4 GiB total owned live-byte cap')
        live = sum(p.stat().st_size for root in ROOTS for p in (w / root).rglob('*')
                   if p.is_file() and not p.is_symlink())
        require(shutil.disk_usage(w).free >= live + RESERVE + 512 * 1024**2,
                'Insufficient checkpoint retention headroom')
        last_capacity = time.monotonic()

    def tick():
        require(time.monotonic() < phase_end, 'Controlled phase deadline')
        free = shutil.disk_usage(w).free
        result['minimum_free_bytes'] = min(result.get('minimum_free_bytes', free), free)
        require(free >= RESERVE, '2 GiB free disk reserve')
        if not retention and time.monotonic() - last_capacity >= 15:
            capacity()
        available = next(x for x in Path('/proc/meminfo').read_text().splitlines()
                         if x.startswith('MemAvailable:'))
        require(int(available.split()[1]) * 1024 >= 512 * 1024**2, 'RAM reserve')

    def run(args, label, limit=90, cwd=None):
        tick()
        args = list(map(str, args))
        if args[0] == 'git':
            args[1:1] = ['-c', 'safe.directory=' + str(cwd or w)]
        command_start = time.monotonic()
        row = {'label': label, 'argv': args, 'exit': None}
        if label == 'package-current':
            # A failed packager may stop before or after its native probes.
            # Unknown is more accurate than claiming they did not run.
            result['product_execution_started'] = None
            result['product_execution_state'] = 'CURRENT_PACKAGER_PROBES_MAY_RUN'
        result['commands'].append(row)
        save()
        path = out / (label + '.log')
        child = None
        with path.open('wb') as log:
            child = subprocess.Popen(args, cwd=cwd or w, env=env, stdout=subprocess.PIPE,
                                     stderr=subprocess.STDOUT, start_new_session=True)
            selector = selectors.DefaultSelector()
            selector.register(child.stdout, selectors.EVENT_READ)
            try:
                while selector.get_map():
                    tick()
                    require(time.monotonic() - command_start <= limit, label + ' timeout')
                    for key, mask in selector.select(timeout=0.25):
                        block = os.read(key.fileobj.fileno(), 65536)
                        if block:
                            log.write(block)
                            log.flush()
                            sys.stdout.buffer.write(block)
                            sys.stdout.buffer.flush()
                        else:
                            selector.unregister(key.fileobj)
                child.wait(timeout=5)
            except BaseException:
                if child.poll() is None:
                    os.killpg(child.pid, signal.SIGTERM)
                    try:
                        child.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        os.killpg(child.pid, signal.SIGKILL)
                        child.wait()
                raise
            finally:
                selector.close()
                row.update(exit=child.returncode, seconds=time.monotonic() - command_start)
                save()
        require(child.returncode == 0, label + ' failed')
        if label == 'package-current':
            result['product_execution_started'] = True
            result['product_execution_state'] = 'CURRENT_NATIVE_PACKAGER_GATES_SUCCEEDED'
            save()
        return path.read_text(errors='replace')

    def interrupted(signum, frame):
        raise RuntimeError('Interrupted: ' + str(signum))
    signal.signal(signal.SIGTERM, interrupted)
    signal.signal(signal.SIGINT, interrupted)
    save()
    try:
        inputs = json.loads((w / 'control/inputs.json').read_text())
        for key, value in [('workspace', WORKSPACE), ('source', SOURCE),
                           ('expected_plan_actions', 3555),
                           ('maximum_actions', 4000)]:
            require(inputs[key] == value, 'Input identity drift: ' + key)
        require(tuple(inputs['targets']) == TARGETS, 'Target list drift')
        expected_limits = {'compile_seconds': 4200, 'package_seconds': 900,
                           'retention_seconds': 420, 'prepare_seconds': 300,
                           'owned_live_bytes': MAX_BYTES, 'reserve_bytes': RESERVE}
        require(all(inputs['limits'].get(key) == value for key, value in expected_limits.items()),
                'Limit drift')
        resume = inputs.get('checkpoint_resume', False)
        require(type(resume) is bool, 'Checkpoint resume selector')
        if not resume:
            for key, value in [('checkpoint_inner_sha256', INNER), ('checkpoint_manifest_sha256', MANIFEST),
                               ('checkpoint_artifact', 14310615150), ('checkpoint_run', 44042241925),
                               ('checkpoint_live_bytes', 193304843)]:
                require(inputs[key] == value, 'Pinned initial preflight drift: ' + key)
        inner_pin, manifest_pin = inputs['checkpoint_inner_sha256'], inputs['checkpoint_manifest_sha256']
        memory = dict(x.split(':', 1) for x in Path('/proc/meminfo').read_text().splitlines())
        require(int(memory['MemTotal'].split()[0]) * 1024 >= 7 * 1024**3, '7 GiB RAM admission')
        saved = w / 'saved-checkpoint'
        manifest_file, archive = saved / 'manifest.json', saved / 'build-state.tar.gz'
        require(manifest_file.stat().st_size <= 8 * 1024**2 and sha(manifest_file) == manifest_pin,
                'Pinned checkpoint manifest')
        require(archive.stat().st_size <= 1024**3, 'Compressed checkpoint size')
        manifest = json.loads(manifest_file.read_text())
        require(manifest['workspace'] == WORKSPACE and manifest['identity']['source'] == SOURCE
                and type(manifest['identity']['compile_pass']) is bool, 'Checkpoint source identity')
        require(manifest['archive_sha256'] == inner_pin, 'Pinned checkpoint inner digest')
        require(sum(row.get('bytes', 0) for row in manifest['rows'].values()) == inputs['checkpoint_live_bytes'],
                'Pinned checkpoint regular bytes')
        if not resume:
            require(len(manifest['rows']) == 17213 and manifest['identity']['compile_pass'] is False,
                    'Pinned preflight entry count/compile state')
        old_objects = [n for n, r in manifest['rows'].items()
                       if r['kind'] == 'file' and n.endswith(('.o', '.obj'))]
        require(resume or not old_objects, 'Initial preflight unexpectedly contains objects')
        capacity()
        restore(w, archive, manifest, tick)
        restored = True
        result.update(restored=True, objects_restored=len(old_objects), objects_discarded=0,
                      cache_policy='Preserve verified generated state; refresh CMake, no timestamp manipulation')
        src, build, accepted = w / 'product', w / ROOTS[1], w / 'accepted-source'
        require(run(['git', 'rev-parse', 'HEAD'], 'accepted-head', cwd=accepted).strip() == SOURCE,
                'Independent accepted source HEAD')
        require(not run(['git', 'status', '--porcelain', '--untracked-files=all'],
                        'accepted-clean', cwd=accepted).strip(), 'Accepted source is dirty')
        tracked = list(filter(None, run(['git', 'ls-files', '-z'], 'accepted-files', cwd=accepted).split('\0')))
        require(tracked, 'Missing accepted tracked files')
        for name in tracked:
            from checkpoint import name_ok
            name_ok('product/' + name)
            a, b = accepted / name, src / name
            require(a.is_symlink() == b.is_symlink(), 'Source link type differs: ' + name)
            if a.is_symlink():
                require(os.readlink(a) == os.readlink(b), 'Source link text differs: ' + name)
            else:
                require(a.is_file() and b.is_file() and sha(a) == sha(b), 'Source bytes differ: ' + name)
                require((a.stat().st_mode & 0o111) == (b.stat().st_mode & 0o111), 'Source mode differs: ' + name)
        # Checkpoint excludes Git metadata by contract. Attach only independently
        # checked metadata; never infer tracked-byte identity from restored labels.
        require((accepted / '.git').is_dir() and not (src / '.git').exists(), 'Independent Git metadata required')
        shutil.copytree(accepted / '.git', src / '.git', symlinks=True)
        require(not run(['git', 'status', '--porcelain'], 'restored-source-clean', cwd=src).strip(),
                'Restored source tracked/untracked drift')
        result['source_identity_verified'] = True
        historical = w / 'historical'
        previous = json.loads((historical / 'result.json').read_text())
        require(previous['source'] == SOURCE and previous['verdict'] == 'PREFLIGHT_PASS'
                and previous['planned_action_count'] == 3555, 'Verified preflight result identity')
        receipt_path = w / 'control/dependencies/receipt.json'
        dependency = json.loads(receipt_path.read_text())
        baseline_dependency = json.loads((historical / 'dependencies-receipt.json').read_text())
        # Records locations are provenance, not a toolchain input. Every other
        # observed dependency field (including complete apt closure) must agree.
        comparable = lambda d: {k: v for k, v in d.items() if k != 'records'}
        require(comparable(dependency) == comparable(baseline_dependency), 'External dependency receipt drift')
        require(dependency['status'] == 'READY', 'Dependencies not admitted')
        result['dependency_receipt_sha256'] = sha(receipt_path)
        dependency_identity = hashlib.sha256(json.dumps(comparable(dependency), sort_keys=True).encode()).hexdigest()
        result['dependency_identity_sha256'] = dependency_identity
        if resume:
            require(manifest['identity'].get('source_identity_verified') is True
                    and manifest['identity'].get('dependency_identity_sha256') == dependency_identity
                    and manifest['identity'].get('profile') == {'targets': list(TARGETS), 'on': list(ON), 'off': list(OFF)},
                    'Resumed objects lack exact source/profile/external dependency identity')
        development = dependency['python_development']
        require(set(development['sha256']) == {development[k] for k in ('header', 'config_header', 'library')},
                'Incomplete selected Python Development identities')
        require(all(development[k] is True for k in ('shared', 'elf_amd64', 'ldd_resolved')), 'Python ABI receipt')
        for path, digest in development['sha256'].items():
            require(Path(path).is_absolute() and sha(path) == digest, 'Python Development byte drift')
        gl = dependency['opengl_development']
        require(gl['owner_verified'] and sha(gl['header']) == gl['header_sha256'], 'OpenGL header drift')
        tools, python = dependency['tools'], dependency['python']
        gcc = tools.get('gcc', dependency['environment']['CC'])
        env.update(dependency.get('environment', {}))
        env.update(NINJA_STATUS='[%f/%t %es] ', CMAKE_BUILD_PARALLEL_LEVEL='2')
        for executable in [python, gcc, *(tools[k] for k in ('cmake', 'ninja', 'gxx', 'qtpaths'))]:
            require(Path(executable).is_absolute() and Path(executable).is_file(), 'Missing selected tool')
        # The historical top-level graph includes rules.ninja from this build
        # directory. Preserve its verified restored bytes before CMake can change
        # them, so old/current command comparison cannot mask rule drift.
        rules = build / 'CMakeFiles/rules.ninja'
        require(rules.is_file() and not rules.is_symlink(), 'Missing verified restored Ninja rules')
        rules_digest = sha(rules)
        shutil.copyfile(rules, out / 'restored-rules.ninja')
        result['restored_ninja_rules_sha256'] = rules_digest
        cmake = [tools['cmake'], '-S', src, '-B', build, '-G', 'Ninja',
                 '-DCMAKE_BUILD_TYPE=Release', '-DCMAKE_EXPORT_COMPILE_COMMANDS=ON',
                 '-DCMAKE_MAKE_PROGRAM=' + tools['ninja'], '-DCMAKE_CXX_COMPILER=' + tools['gxx'],
                 '-DCMAKE_C_COMPILER=' + gcc, '-DPython3_EXECUTABLE=' + python,
                 '-DPython3_ROOT_DIR=' + str(Path(python).parent.parent),
                 '-DPython3_INCLUDE_DIR=' + development['include'], '-DPython3_LIBRARY=' + development['library'],
                 '-DWITH_QT_VERSION=6', '-DOPENSSL_ROOT_DIR=' + str(w / ROOTS[2]), '-DOPENSSL_USE_STATIC_LIBS=ON']
        cmake += ['-D' + n + '=ON' for n in ON] + ['-D' + n + '=OFF' for n in OFF]
        run(cmake, 'configure-refresh', limit=180)
        require(sha(rules) == rules_digest, 'Ninja command rule drift after configure')
        cache = (build / 'CMakeCache.txt').read_text()
        for name in ON + OFF:
            require(re.search(r'^' + re.escape(name) + r':(?:BOOL|INTERNAL)='
                              + ('ON' if name in ON else 'OFF') + r'$', cache, re.MULTILINE), 'Profile drift: ' + name)
        require('WITH_QT_VERSION:STRING=6' in cache and 'CMAKE_BUILD_TYPE:STRING=Release' in cache, 'Release Qt 6 profile')
        for key, selected in [('INCLUDE_DIR', development['include']), ('LIBRARY_RELEASE', development['library'])]:
            found = re.search(r'^_Python3_' + key + r':INTERNAL=(.+)$', cache, re.MULTILINE)
            require(found and Path(found.group(1)).resolve() == Path(selected).resolve(), 'Selected Python artifact drift')
        for key, filename in [('OPENSSL_CRYPTO_LIBRARY', 'libcrypto.a'), ('OPENSSL_SSL_LIBRARY', 'libssl.a')]:
            require(key + ':FILEPATH=' + str(w / ROOTS[2] / 'lib' / filename) in cache, 'Private static OpenSSL selection')
        require(json.loads((build / 'compile_commands.json').read_text()) ==
                json.loads((historical / 'compile_commands.json').read_text()), 'Compile command/profile drift')
        glob = build / 'CMakeFiles/VerifyGlobs.cmake'
        if glob.exists():
            run([tools['cmake'], '-P', glob], 'verify-globs', cwd=build)
        # Freeze the measured top-level graph after explicit regeneration.
        observed = out / 'observed.ninja'
        shutil.copyfile(build / 'build.ninja', observed)
        old_commands = run([tools['ninja'], '-C', build, '-f', historical / 'build.ninja', '-t', 'commands', *TARGETS],
                           'historical-target-commands')
        new_commands = run([tools['ninja'], '-C', build, '-f', observed, '-t', 'commands', *TARGETS], 'target-commands')
        require(old_commands == new_commands, 'Generated/link command drift')
        dry = run([tools['ninja'], '-C', build, '-f', observed, '-n', '-d', 'explain', *TARGETS], 'dry-plan')
        require('Re-running CMake' not in dry and 'Re-checking globbed' not in dry, 'Incomplete target plan')
        actions = re.findall(r'^\[\d+/\d+(?: [^\]]*)?\].*$', dry, re.MULTILINE)
        require(actions and len(actions) <= 4000, 'Measured full-plan action ceiling')
        result.update(planned_action_count=len(actions), baseline_action_count=3555,
                      plan_action_deviation=len(actions) - 3555,
                      plan_deviation_policy='Disclosed count; identical compile/link commands and profile required')
        for name in ('CMakeCache.txt', 'compile_commands.json', 'build.ninja'):
            shutil.copyfile(build / name, out / name)
        capacity()
        # The small icon dependency gate belongs to the 70-minute compile budget.
        phase_end = min(time.monotonic() + 4200, hard_end - 900 - 420)
        result['product_compile_started'] = True
        run([tools['ninja'], '-C', build, '-j', '2', 'generate_ico'], 'generated-ico', limit=90)
        run([tools['ninja'], '-C', build, '-j', '2', *TARGETS], 'compile', limit=4200)
        compile_pass = True
        result['compile_pass'] = True
        capacity()
        phase_end = min(time.monotonic() + 900, hard_end - 420)
        sys.path.insert(0, str(w / 'control/packaging'))
        import package_candidate
        result['package'] = package_candidate.package(w, inputs, python, run, out, tick=tick)
        require(result['package'].get('verdict') == 'PACKAGE_STATIC_GATES_PASS_RUNTIME_QUALIFICATION_PENDING', 'Packaging helper did not pass')
        capacity()
    except BaseException as error:
        result['error'] = repr(error)
    finally:
        if restored:
            retention = True
            phase_end = min(time.monotonic() + 420, hard_end)
            try:
                result['retention_started'] = True
                save()
                updated = create(w, out / 'updated-checkpoint',
                                 {'source': SOURCE, 'compile_pass': compile_pass,
                                  'source_identity_verified': bool(result.get('source_identity_verified')),
                                  'dependency_receipt_sha256': result.get('dependency_receipt_sha256'),
                                  'dependency_identity_sha256': result.get('dependency_identity_sha256'),
                                  'profile': {'targets': TARGETS, 'on': ON, 'off': OFF}}, tick,
                                 diagnostics=out / 'checkpoint-links.json')
                require(all(updated['rows'].get(n) == row for n, row in manifest['rows'].items()
                            if n == ROOTS[2] or n.startswith(ROOTS[2] + '/')), 'Private OpenSSL changed')
                require(sha(archive) == inner_pin and sha(manifest_file) == manifest_pin, 'Immutable input checkpoint changed')
                result.update(checkpoint_verified=True, checkpoint_inner_sha256=updated['archive_sha256'],
                              checkpoint_manifest_sha256=sha(out / 'updated-checkpoint/manifest.json'))
            except BaseException as error:
                result['retention_error'] = repr(error)
        if compile_pass and result.get('package', {}).get('verdict') == 'PACKAGE_STATIC_GATES_PASS_RUNTIME_QUALIFICATION_PENDING' and result['checkpoint_verified'] \
                and not result.get('error') and not result.get('retention_error'):
            result['verdict'] = 'BUILD_PACKAGE_PASS'
        save()
    return 0 if result['verdict'] == 'BUILD_PACKAGE_PASS' else 1


if __name__ == '__main__':
    sys.exit(main())
