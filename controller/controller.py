"""Future isolated hosted configure/plan controller. No BTX compilation or launch."""
from pathlib import Path
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import time
from checkpoint import ROOTS, RESERVE, create, require, restore, sha, snapshot

WORKSPACE = '/home/runner/work/btx/btx'
SOURCE = '074dac167c26c1e091198f691ed5727817dba88a'
SEED = 'dac9aee53520bd49ed320ec7a49b9072fc7d88d9'
INNER = '90391b49487f57e3c820200f28142e6873b0fecbb2a2d4b82091e48050437176'
MANIFEST = '4d9c6e3d6b357ae5cfd07ff3aeb52bb9c75049c1614eb0fd6f84ae76c5974480'
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
    require(str(w) == WORKSPACE, 'Requires the recorded isolated absolute workspace')
    out = w / 'preflight-records'
    out.mkdir(exist_ok=True)
    require(not (out / 'result.json').exists(), 'Prior controller result exists')
    result = {'source': SOURCE, 'stage': 'configure-and-plan-only', 'verdict': 'INCOMPLETE',
              'product_compile_started': False, 'product_execution_started': False,
              'commands': [], 'checkpoint_verified': False}
    start = time.monotonic()
    # Work stops before retention begins. The enclosing workflow reserves upload time separately.
    work_end = start + 300
    hard_end = work_end + 180
    restored = False
    mutated = False
    env = os.environ.copy()
    def save():
        result['elapsed_seconds'] = time.monotonic() - start
        temporary = out / 'result.json.tmp'
        temporary.write_text(json.dumps(result, indent=2) + '\n')
        temporary.replace(out / 'result.json')
    save()
    def tick(retention=False):
        require(time.monotonic() < (hard_end if retention else work_end), 'Controller deadline')
        free = shutil.disk_usage(w).free
        result['minimum_free_bytes'] = min(result.get('minimum_free_bytes', free), free)
        require(free >= RESERVE, 'Disk reserve')
        available = next(line for line in Path('/proc/meminfo').read_text().splitlines() if line.startswith('MemAvailable:'))
        require(int(available.split()[1]) * 1024 >= 512 * 1024**2, 'Available RAM reserve')
        # Avoid walking/hashing the tree every subprocess poll. Disk reserve is continuous;
        # exact owned-byte checks are performed at state transitions below.
    def capacity():
        total = 0
        for root in ROOTS:
            if not (w / root).exists():
                continue
            for directory, dirs, files in os.walk(w / root, followlinks=False):
                for name in files:
                    p = Path(directory) / name
                    if not p.is_symlink():
                        total += p.stat().st_size
        result['owned_live_bytes'] = total
        require(total <= 4 * 1024**3, 'Owned source/build cap')
        require(shutil.disk_usage(w).free >= total + RESERVE + 512 * 1024**2, 'Retention headroom')
        tick()
    def run(args, label, limit=90, cwd=None):
        tick()
        args = list(args)
        if args[0] == 'git':
            args[1:1] = ['-c', 'safe.directory=' + str(cwd or w)]
        command_start = time.monotonic()
        row = {'label': label, 'argv': list(map(str, args)), 'exit': None}
        result['commands'].append(row)
        save()
        with (out / (label + '.log')).open('wb') as log:
            child = subprocess.Popen(row['argv'], cwd=cwd or w, env=env,
                                     stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
            try:
                while child.poll() is None:
                    tick()
                    require(time.monotonic() - command_start <= limit, label + ' timeout')
                    time.sleep(0.25)
            except BaseException:
                os.killpg(child.pid, signal.SIGTERM)
                try:
                    child.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    os.killpg(child.pid, signal.SIGKILL)
                    child.wait()
                raise
            finally:
                row.update(exit=child.returncode, seconds=time.monotonic() - command_start)
                save()
        require(child.returncode == 0, label + ' failed')
        return (out / (label + '.log')).read_text(errors='replace')
    # Interruptions still enter finally while the enclosing step is alive.
    def interrupted(signum, frame):
        raise RuntimeError('Controller interrupted: ' + str(signum))
    signal.signal(signal.SIGTERM, interrupted)
    signal.signal(signal.SIGINT, interrupted)
    try:
        inputs = json.loads((w / 'control/inputs.json').read_text())
        for key, value in [('workspace', WORKSPACE), ('source', SOURCE), ('seed_source', SEED),
                           ('seed_inner_sha256', INNER), ('seed_manifest_sha256', MANIFEST)]:
            require(inputs[key] == value, 'Input identity mismatch: ' + key)
        require(tuple(inputs['targets']) == TARGETS, 'Target list drift')
        # Fetch performs the initial 16 GiB admission before dependencies consume
        # disk. Here reserve enough for full restore plus uncompressed retention.
        require(shutil.disk_usage(w).free >= 2 * 715403164 + RESERVE + 512 * 1024**2,
                'Restore and retention headroom')
        memory = dict(line.split(':', 1) for line in Path('/proc/meminfo').read_text().splitlines())
        require(int(memory['MemTotal'].split()[0]) * 1024 >= 7 * 1024**3, '7 GiB RAM admission')
        result['memory_total_bytes'] = int(memory['MemTotal'].split()[0]) * 1024
        receipt_path = w / 'control/dependencies/receipt.json'
        dependency = json.loads(receipt_path.read_text())
        require(dependency['status'] == 'READY', 'Dependencies not admitted')
        require(dependency['invalidate_all_old_cpp'] is True,
                'Dependency receipt must require conservative C++ invalidation')
        result['dependency_receipt_sha256'] = sha(receipt_path)
        tools = dependency['tools']
        python = dependency['python']
        gcc = tools.get('gcc', dependency['environment']['CC'])
        for executable in [python, gcc, *(tools[k] for k in ('cmake', 'ninja', 'gxx', 'qtpaths'))]:
            require(Path(executable).is_absolute() and Path(executable).is_file(), 'Missing dependency executable')
        env.update(dependency.get('environment', {}))
        env['NINJA_STATUS'] = '[%f/%t] '
        development = dependency['python_development']
        require(all(development[key] is True for key in ('shared', 'elf_amd64', 'ldd_resolved')),
                'Python Development ABI evidence')
        for path, digest in development['sha256'].items():
            require(Path(path).is_absolute() and sha(path) == digest, 'Python Development bytes changed')
        require(set(development['sha256']) == {development[key] for key in ('header', 'config_header', 'library')},
                'Incomplete Python Development identity')
        opengl = dependency['opengl_development']
        require(opengl['header'] == '/usr/include/GL/gl.h'
                and opengl['package'] == 'libgl-dev:amd64' and opengl['owner_verified'] is True,
                'OpenGL header prerequisite identity')
        require(sha(opengl['header']) == opengl['header_sha256'], 'OpenGL header bytes changed')
        accepted = w / 'accepted-source'
        require(run(['git', 'rev-parse', 'HEAD'], 'accepted-head', cwd=accepted).strip() == SOURCE, 'Accepted HEAD')
        require(not run(['git', 'status', '--porcelain'], 'accepted-clean', cwd=accepted).strip(), 'Dirty accepted source')
        saved = w / 'saved-checkpoint'
        manifest_file = saved / 'manifest.json'
        require(manifest_file.stat().st_size <= 8 * 1024**2, 'Manifest byte bound')
        require(sha(manifest_file) == MANIFEST, 'Pinned manifest digest')
        manifest = json.loads(manifest_file.read_text())
        require(manifest['workspace'] == WORKSPACE and manifest['identity']['source'] == SEED, 'Seed identity')
        require(manifest['archive_sha256'] == INNER, 'Pinned inner identity')
        archive = saved / 'build-state.tar.gz'
        require(archive.stat().st_size <= 1024**3, 'Compressed archive bound')
        restore(w, archive, manifest, tick)
        restored = True
        result['seed_verified'] = True
        result['seed_regular_bytes'] = sum(row.get('bytes', 0) for row in manifest['rows'].values())
        old_objects = [name for name, row in manifest['rows'].items()
                       if row['kind'] == 'file' and name.endswith(('.o', '.obj'))]
        (out / 'discarded-object-paths.json').write_text(json.dumps(old_objects, indent=2) + '\n')
        result['objects_restored'] = len(old_objects)
        capacity()
        # No complete prior external-header byte baseline exists. Discard the whole mutable
        # CMake tree, not merely objects suggested by compiler/dependency version strings.
        build = w / 'gui-pilot-runtime/qtbuild'
        mutated = True
        shutil.rmtree(build)
        build.mkdir()
        result.update(objects_discarded=len(old_objects), objects_reused=0,
                      cache_policy='ALL C++ objects and generated build state invalidated: external-header baseline unavailable')
        src = w / 'product'
        shutil.rmtree(src)
        src.mkdir()
        names = run(['git', 'ls-files', '-z'], 'accepted-files', cwd=accepted).split('\x00')
        epoch = time.time_ns()
        for name in filter(None, names):
            tick()
            from checkpoint import name_ok, link_destination
            name_ok('product/' + name)
            a, b = accepted / name, src / name
            b.parent.mkdir(parents=True, exist_ok=True)
            if a.is_symlink():
                link_destination('product/' + name, os.readlink(a))
                b.symlink_to(os.readlink(a))
            else:
                require(a.is_file(), 'Unsupported accepted source entry')
                shutil.copyfile(a, b)
                shutil.copymode(a, b)
            os.utime(b, ns=(epoch, epoch), follow_symlinks=False)
        require((accepted / '.git').is_dir(), 'Accepted checkout must have independent git metadata')
        shutil.copytree(accepted / '.git', src / '.git', symlinks=True)
        require(run(['git', 'rev-parse', 'HEAD'], 'source-head', cwd=src).strip() == SOURCE, 'Updated source HEAD')
        require(not run(['git', 'status', '--porcelain'], 'source-clean', cwd=src).strip(), 'Updated source differs')
        result['source_updated'] = True
        result['source_file_mtime_ns'] = epoch
        capacity()
        cmake = [tools['cmake'], '-S', src, '-B', build, '-G', 'Ninja',
                 '-DCMAKE_BUILD_TYPE=Release', '-DCMAKE_EXPORT_COMPILE_COMMANDS=ON',
                 '-DCMAKE_MAKE_PROGRAM=' + tools['ninja'], '-DCMAKE_CXX_COMPILER=' + tools['gxx'],
                 '-DCMAKE_C_COMPILER=' + gcc,
                 '-DPython3_EXECUTABLE=' + python, '-DPython3_ROOT_DIR=' + str(Path(python).parent.parent),
                 '-DPython3_INCLUDE_DIR=' + development['include'],
                 '-DPython3_LIBRARY=' + development['library'],
                 '-DWITH_QT_VERSION=6', '-DOPENSSL_ROOT_DIR=' + str(w / 'gui-pilot-runtime/openssl'),
                 '-DOPENSSL_USE_STATIC_LIBS=ON']
        cmake += ['-D' + name + '=ON' for name in ON] + ['-D' + name + '=OFF' for name in OFF]
        configured = run(cmake, 'configure', limit=150)
        require('found components: Interpreter Development' in configured, 'Python Interpreter and Development discovery')
        cache = (build / 'CMakeCache.txt').read_text()
        for name in ON + OFF:
            # cmake_dependent_option writes disabled GUI tests as INTERNAL.
            require(re.search(r'^' + re.escape(name) + r':(?:BOOL|INTERNAL)='
                              + ('ON' if name in ON else 'OFF') + r'$', cache, re.MULTILINE),
                    'Configuration flag: ' + name)
        require('WITH_QT_VERSION:STRING=6' in cache, 'Qt 6 cache identity')
        for artifact, selected in [('INCLUDE_DIR', development['include']), ('LIBRARY_RELEASE', development['library'])]:
            found = re.search(r'^_Python3_' + artifact + r':INTERNAL=(.+)$', cache, re.MULTILINE)
            require(found and Path(found.group(1)).resolve() == Path(selected).resolve(),
                    'CMake selected different Python Development artifact: ' + artifact)
        for name, filename in [('OPENSSL_CRYPTO_LIBRARY', 'libcrypto.a'), ('OPENSSL_SSL_LIBRARY', 'libssl.a')]:
            require(name + ':FILEPATH=' + str(w / 'gui-pilot-runtime/openssl/lib' / filename) in cache,
                    'Private static OpenSSL selection')
        result['configured'] = True
        # CMake regeneration occurs explicitly; the captured Ninja file cannot invoke
        # regeneration and hide the actual full target plan behind a single step.
        glob = build / 'CMakeFiles/VerifyGlobs.cmake'
        if glob.exists():
            run([tools['cmake'], '-P', glob], 'verify-globs', cwd=build)
        observed = out / 'observed.ninja'
        shutil.copyfile(build / 'build.ninja', observed)
        dry = run([tools['ninja'], '-C', build, '-f', observed, '-n', '-d', 'explain', *TARGETS], 'dry-plan', limit=90)
        require('Re-running CMake' not in dry and 'Re-checking globbed' not in dry, 'Incomplete regeneration plan')
        actions = re.findall(r'^\[\d+/\d+\].*$', dry, re.MULTILINE)
        require(actions, 'No measured target actions')
        result['planned_action_count'] = len(actions)
        result['planned_action_lines'] = actions
        require(len(actions) <= 4000, 'Measured action admission ceiling exceeded')
        result['plan_captured'] = True
        for name in ('CMakeCache.txt', 'compile_commands.json', 'build.ninja'):
            shutil.copyfile(build / name, out / name)
        objects = list(build.rglob('*.o')) + list(build.rglob('*.obj'))
        probes = [p for p in objects if any(part in ('CMakeScratch', 'CMakeTmp') for part in p.relative_to(build).parts)]
        result['configure_probe_object_paths'] = [p.relative_to(build).as_posix() for p in probes]
        require(len(objects) == len(probes), 'Unexpected product object compilation')
        capacity()
    except BaseException as error:
        result['error'] = repr(error)
    finally:
        if restored and mutated:
            try:
                result['retention_started'] = True
                save()
                updated = create(w, out / 'updated-checkpoint',
                                 {'source': SOURCE if result.get('source_updated') else 'PARTIAL_SOURCE_UPDATE',
                                  'seed_source': SEED, 'compile_pass': False,
                                  'preflight_complete': bool(result.get('plan_captured'))},
                                 lambda: tick(retention=True), diagnostics=out / 'checkpoint-links.json')
                result['checkpoint_verified'] = True
                result['checkpoint_inner_sha256'] = updated['archive_sha256']
                result['checkpoint_manifest_sha256'] = sha(out / 'updated-checkpoint/manifest.json')
                result['openssl_preserved'] = all(updated['rows'].get(name) == row for name, row in manifest['rows'].items()
                    if name == ROOTS[2] or name.startswith(ROOTS[2] + '/'))
                require(result['openssl_preserved'], 'Private OpenSSL changed')
                require(sha(archive) == INNER and sha(manifest_file) == MANIFEST, 'Immutable seed changed')
            except BaseException as error:
                result['retention_error'] = repr(error)
        if not result.get('error') and not result.get('retention_error') and result.get('plan_captured') and result['checkpoint_verified']:
            result['verdict'] = 'PREFLIGHT_PASS'
        save()
    return 0 if result['verdict'] == 'PREFLIGHT_PASS' else 1

if __name__ == '__main__':
    sys.exit(main())
