"""FUTURE AUTHORIZED EXECUTION ONLY: packaging from verified compiled state.

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
from checkpoint import ROOTS, RESERVE, MAX_BYTES, create, require, restore, sha, snapshot, name_ok

WORKSPACE = '/home/runner/work/btx/btx'
SOURCE = '074dac167c26c1e091198f691ed5727817dba88a'
INNER = 'bbd94e974883ddde5f959a2c7347a7abff9cb5fa7440efcbb5a23a9509bba67e'
MANIFEST = 'ac9302cc81c3f85d4253b77c8af43741eb4522bd6ee8063e512c7cefac1aeefb'
SONAME = 'libpython3.12.so.1.0'
DEPENDENCY = 'db6922a90d638ca0027a2c6ac96d3e34b2db5870c87089f38c142111a0268687'
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
    # Dependency setup/fetch precede this 27-minute controller budget.
    hard_end = start + 1620
    phase_end = min(start + 300, hard_end - 420)
    retention = False
    restored = False
    compile_pass = False
    result = {'source': SOURCE, 'verdict': 'INCOMPLETE', 'commands': [],
              'compile_pass': False, 'compile_result_origin': 'NOT_YET_RESTORED',
              'cpp_rebuild': False, 'checkpoint_verified': False,
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
        require(Path(args[0]).name not in ('cmake', 'ninja', 'make', 'gcc', 'g++',
                                         'gcc-11', 'g++-11', 'cc', 'c++', 'clang', 'clang++'),
                'Build/configuration commands forbidden in packaging-only continuation')
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
                           ('checkpoint_artifact', 14313303910),
                           ('checkpoint_run', 44047285383),
                           ('checkpoint_fixture', '42a4eab0b19f07fe9355060194dc1346bfc96abc'),
                           ('checkpoint_inner_sha256', INNER),
                           ('checkpoint_manifest_sha256', MANIFEST),
                           ('checkpoint_live_bytes', 942035712)]:
            require(inputs[key] == value, 'Input identity drift: ' + key)
        require(tuple(inputs['targets']) == TARGETS, 'Target list drift')
        require(inputs.get('cpp_rebuild') is False, 'C++ rebuild must be explicitly false')
        require(inputs.get('checkpoint_compile_pass') is True, 'Compiled checkpoint selector')
        expected_limits = {'prepare_seconds': 300, 'package_seconds': 900,
                           'retention_seconds': 420, 'hard_seconds': 1620,
                           'owned_live_bytes': MAX_BYTES, 'reserve_bytes': RESERVE}
        require(all(inputs['limits'].get(k) == v for k, v in expected_limits.items()), 'Limit drift')
        require('LD_LIBRARY_PATH' not in env and 'LD_PRELOAD' not in env,
                'Loader environment overrides forbidden')
        saved = w / 'saved-checkpoint'
        manifest_file, archive = saved / 'manifest.json', saved / 'build-state.tar.gz'
        require(manifest_file.is_file() and not manifest_file.is_symlink()
                and manifest_file.stat().st_size <= 8 * 1024**2 and sha(manifest_file) == MANIFEST,
                'Pinned manifest')
        require(archive.is_file() and not archive.is_symlink()
                and archive.stat().st_size == 313947224, 'Pinned inner size')
        manifest = json.loads(manifest_file.read_text())
        profile = {'targets': list(TARGETS), 'on': list(ON), 'off': list(OFF)}
        identity = manifest['identity']
        require(manifest['workspace'] == WORKSPACE and manifest['archive_sha256'] == INNER
                and identity['source'] == SOURCE and identity['compile_pass'] is True
                and identity['source_identity_verified'] is True
                and identity['dependency_identity_sha256'] == DEPENDENCY
                and identity['profile'] == profile, 'Compiled checkpoint identity/profile')
        require(len(manifest['rows']) == 20941 and
                sum(r.get('bytes', 0) for r in manifest['rows'].values()) == 942035712,
                'Compiled checkpoint size/entry count')
        objects = {n: r for n, r in manifest['rows'].items()
                   if r['kind'] == 'file' and n.endswith(('.o', '.obj'))}
        require(len(objects) == 3368, 'Compiled object count')
        capacity()
        restore(w, archive, manifest, tick)
        restored = True
        compile_pass = True
        result.update(restored=True, compile_pass=True, original_compile_pass=True,
                      compile_result_origin='restored compile result',
                      objects_restored=len(objects), objects_discarded=0,
                      original_compile_run=44047285383, original_compile_artifact=14313303910,
                      cache_policy='No build or configuration commands; preserve all compiled bytes')
        src, build, accepted = w / 'product', w / ROOTS[1], w / 'accepted-source'
        binaries = {}
        for name in TARGETS:
            key = ROOTS[1] + '/bin/' + name
            row = manifest['rows'].get(key, {})
            path = w / key
            require(row.get('kind') == 'file' and row['mode'] & 0o111 and
                    path.is_file() and not path.is_symlink() and sha(path) == row['sha256'],
                    'Compiled binary identity: ' + name)
            require(inputs['compiled_binary_sha256'].get(name) == row['sha256'],
                    'Independently pinned binary digest: ' + name)
            with path.open('rb') as stream:
                header = stream.read(20)
            require(header[:6] == b'\x7fELF\x02\x01' and header[18:20] == b'\x3e\x00',
                    'Compiled ELF64 amd64: ' + name)
            binaries[key] = row
        result['restored_binaries'] = binaries
        require(set(inputs['compiled_binary_sha256']) == set(TARGETS), 'Exact 17 binary pins required')
        require(run(['git', 'rev-parse', 'HEAD'], 'accepted-head', cwd=accepted).strip() == SOURCE,
                'Independent accepted source HEAD')
        require(not run(['git', 'status', '--porcelain', '--untracked-files=all'],
                        'accepted-clean', cwd=accepted).strip(), 'Accepted source dirty')
        tracked = list(filter(None, run(['git', 'ls-files', '-z'], 'accepted-files', cwd=accepted).split('\0')))
        require(tracked, 'Missing independently accepted files')
        for name in tracked:
            tick()
            name_ok('product/' + name)
            a, b = accepted / name, src / name
            require(a.is_symlink() == b.is_symlink(), 'Source link type: ' + name)
            if a.is_symlink():
                require(os.readlink(a) == os.readlink(b), 'Source link text: ' + name)
            else:
                require(a.is_file() and b.is_file() and sha(a) == sha(b)
                        and (a.stat().st_mode & 0o111) == (b.stat().st_mode & 0o111),
                        'Independent source bytes/mode: ' + name)
        require((accepted / '.git').is_dir() and not (src / '.git').exists(), 'Independent Git metadata')
        shutil.copytree(accepted / '.git', src / '.git', symlinks=True)
        require(not run(['git', 'status', '--porcelain', '--untracked-files=all'],
                        'restored-source-clean', cwd=src).strip(), 'Restored source drift')
        result['source_identity_verified'] = True
        historical = w / 'historical'
        previous = json.loads((historical / 'result.json').read_text())
        require(previous['source'] == SOURCE and previous['compile_pass'] is True
                and previous['checkpoint_verified'] is True
                and previous['checkpoint_inner_sha256'] == INNER
                and previous['checkpoint_manifest_sha256'] == MANIFEST,
                'Original compiled-result receipt')
        receipt_path = w / 'control/dependencies/receipt.json'
        dependency = json.loads(receipt_path.read_text())
        baseline_path = historical / 'dependencies-receipt.json'
        baseline = json.loads(baseline_path.read_text())
        comparable = lambda d: {k: v for k, v in d.items() if k != 'records'}
        require(sha(baseline_path) == identity['dependency_receipt_sha256'] ==
                previous['dependency_receipt_sha256'], 'Immutable original dependency receipt hash')
        dependency_identity = hashlib.sha256(json.dumps(comparable(baseline), sort_keys=True).encode()).hexdigest()
        require(dependency_identity == DEPENDENCY, 'Compiled dependency baseline mismatch')
        require(dependency['schema'] == 2 and dependency['status'] == 'READY'
                and dependency['scope'] == 'package-only' and dependency['cpp_rebuild'] is False
                and type(dependency['build_tool_invocations']) is int
                and dependency['build_tool_invocations'] == 0, 'Package-only dependency receipt contract')
        observed_fields = ('python', 'python_development', 'opengl_development', 'imports',
                           'installed_packages_sha256')
        for key in observed_fields:
            require(dependency[key] == baseline[key], 'Current observed dependency drift: ' + key)
        permitted_environment = ('BUILDER_PYTHON', 'Python3_ROOT_DIR', 'Python3_EXECUTABLE')
        require(dependency['environment'] == {k: baseline['environment'][k] for k in permitted_environment},
                'Package-only environment must select Python only')
        require(dependency['tools'] == {'qtpaths': baseline['tools']['qtpaths']},
                'Package-only tools select qtpaths without build-tool probes')
        require(set(dependency['inputs']) == {'wheels.lock', 'input-manifest.json', 'setup.sh'},
                'Current dependency input receipt completeness')
        for name, digest in dependency['inputs'].items():
            require(sha(w / 'control/dependencies' / name) == digest, 'Current dependency input bytes: ' + name)
        require(dependency['inputs']['wheels.lock'] == baseline['inputs']['wheels.lock'],
                'Original locked wheel inputs changed')
        current_records = Path(dependency['records'])
        require(current_records.is_absolute() and current_records.resolve().is_relative_to(w)
                and sha(current_records / 'installed-packages.log') == dependency['installed_packages_sha256'],
                'Current complete installed-package evidence')
        result.update(dependency_receipt_sha256=sha(baseline_path),
                      dependency_identity_sha256=dependency_identity,
                      current_package_dependency_receipt_sha256=sha(receipt_path),
                      dependency_comparison_fields=list(observed_fields),
                      historical_tool_execution_claim='Original receipt only; build tools not re-executed')
        development = dependency['python_development']
        require(set(development['sha256']) == {development[k] for k in ('header', 'config_header', 'library')}
                and all(development[k] is True for k in ('shared', 'elf_amd64', 'ldd_resolved')),
                'Python Development receipt incomplete')
        for path, digest in development['sha256'].items():
            require(Path(path).is_absolute() and sha(path) == digest, 'Selected Python byte drift')
        gl = dependency['opengl_development']
        require(gl['owner_verified'] and sha(gl['header']) == gl['header_sha256'], 'OpenGL header drift')
        cache = (build / 'CMakeCache.txt').read_text()
        for name in ON + OFF:
            require(re.search(r'^' + re.escape(name) + r':(?:BOOL|INTERNAL)='
                              + ('ON' if name in ON else 'OFF') + r'$', cache, re.MULTILINE),
                    'Restored cache profile: ' + name)
        require('WITH_QT_VERSION:STRING=6' in cache and 'CMAKE_BUILD_TYPE:STRING=Release' in cache,
                'Restored Qt6 release profile')
        for key, chosen in [('INCLUDE_DIR', development['include']), ('LIBRARY_RELEASE', development['library'])]:
            found = re.search(r'^_Python3_' + key + r':INTERNAL=(.+)$', cache, re.MULTILINE)
            require(found and Path(found.group(1)).resolve() == Path(chosen).resolve(), 'Restored Python selection')
        python = dependency['python']
        env.update(dependency.get('environment', {}))
        require('LD_LIBRARY_PATH' not in env and 'LD_PRELOAD' not in env, 'Dependency loader override')
        selected = Path(development['library']).resolve(strict=True)
        require(selected.is_file() and not selected.is_symlink() and selected.stat().st_nlink == 1
                and selected.parent == Path(development['library']).parent.resolve()
                and sha(selected) == development['sha256'][development['library']],
                'Real selected Python library byte binding')
        dynamic = run(['readelf', '-d', build / 'bin/btxd'], 'btxd-dynamic', limit=15)
        needed = re.findall(r'\(NEEDED\).*\[([^\]]+)\]', dynamic)
        paths = re.findall(r'\(RUNPATH\).*\[([^\]]*)\]', dynamic)
        require(SONAME in needed and len(paths) == 1 and paths[0] == '$ORIGIN/../lib',
                'Expected unmodified btxd Python NEEDED/RUNPATH')
        py_dynamic = run(['readelf', '-d', selected], 'selected-python-dynamic', limit=15)
        require(re.findall(r'\(SONAME\).*\[([^\]]+)\]', py_dynamic) == [SONAME], 'Selected Python SONAME')
        libdir = build / 'lib'
        require(libdir.is_dir() and not libdir.is_symlink(), 'Regular build library directory')
        destination = libdir / SONAME
        require(not os.path.lexists(destination), 'Refuse existing loader prerequisite')
        with selected.open('rb') as source, destination.open('xb') as output:
            for block in iter(lambda: source.read(1024**2), b''):
                tick()
                output.write(block)
        destination.chmod(selected.stat().st_mode & 0o777)
        require(destination.is_file() and not destination.is_symlink()
                and destination.stat().st_nlink == 1 and sha(destination) == sha(selected),
                'Staged Python loader prerequisite digest')
        result['loader_prerequisite'] = {'selected_real_file': str(selected), 'destination': str(destination),
                                         'sha256': sha(destination), 'soname': SONAME,
                                         'policy': 'Copy only; no loader environment, system cache or ELF patch'}
        capacity()
        phase_end = min(time.monotonic() + 900, hard_end - 420)
        sys.path.insert(0, str(w / 'control/packaging'))
        import package_candidate
        result['package'] = package_candidate.package(w, inputs, python, run, out, tick=tick)
        require(result['package'].get('verdict') == 'PACKAGE_STATIC_GATES_PASS_RUNTIME_QUALIFICATION_PENDING',
                'Packaging helper did not pass')
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
                # Retain even on package/probe failure. Any object/binary/source
                # mutation fails integrity; compile_pass remains attributed only
                # to the original producer and cannot admit this package.
                current = snapshot(w, tick)
                protected = {n: r for n, r in manifest['rows'].items()
                             if r['kind'] != 'directory'}
                for n, row in protected.items():
                    require(current.get(n) == row, 'Restored input changed: ' + n)
                allowed_additions = []
                for n, row in current.items():
                    if n in manifest['rows']:
                        continue
                    allowed = (n == ROOTS[1] + '/lib/' + SONAME or
                               (n.startswith('product/') and '__pycache__' in Path(n).parts and
                                (row['kind'] == 'directory' or n.endswith('.pyc'))))
                    require(allowed, 'Unexpected checkpoint addition: ' + n)
                    allowed_additions.append(n)
                result['compiled_objects_and_binaries_preserved'] = True
                result['checkpoint_additions'] = allowed_additions
            except BaseException as error:
                result['integrity_error'] = repr(error)
            # A changed object/binary/source may be retained for diagnosis, but
            # that new checkpoint must never advertise a usable compile pass.
            compile_pass = bool(result.get('compiled_objects_and_binaries_preserved'))
            result['compile_pass'] = compile_pass
            try:
                updated = create(w, out / 'updated-checkpoint',
                                 {'source': SOURCE, 'compile_pass': compile_pass,
                                  'compile_result_origin': 'restored compile result',
                                  'original_compile_pass': True,
                                  'cpp_rebuild': False,
                                  'source_identity_verified': bool(result.get('source_identity_verified')),
                                  'dependency_receipt_sha256': result.get('dependency_receipt_sha256'),
                                  'dependency_identity_sha256': result.get('dependency_identity_sha256'),
                                  'current_package_dependency_receipt_sha256': result.get('current_package_dependency_receipt_sha256'),
                                  'profile': {'targets': TARGETS, 'on': ON, 'off': OFF},
                                  'original_compile_run': 44047285383,
                                  'integrity_verified': bool(result.get('compiled_objects_and_binaries_preserved'))},
                                 tick, diagnostics=out / 'checkpoint-links.json')
                require(sha(archive) == INNER and sha(manifest_file) == MANIFEST, 'Immutable checkpoint changed')
                result.update(checkpoint_verified=True, checkpoint_inner_sha256=updated['archive_sha256'],
                              checkpoint_manifest_sha256=sha(out / 'updated-checkpoint/manifest.json'))
            except BaseException as error:
                result['retention_error'] = repr(error)
        if (compile_pass and result.get('package', {}).get('verdict') ==
                'PACKAGE_STATIC_GATES_PASS_RUNTIME_QUALIFICATION_PENDING' and result['checkpoint_verified']
                and not any(result.get(k) for k in ('error', 'retention_error', 'integrity_error'))):
            result['verdict'] = 'PACKAGE_ONLY_PASS_RESTORED_COMPILE_RESULT'
        save()
    return 0 if result['verdict'] == 'PACKAGE_ONLY_PASS_RESTORED_COMPILE_RESULT' else 1


if __name__ == '__main__':
    sys.exit(main())
