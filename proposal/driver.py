"""Dedicated build controller. Preparation only; invoked by an authorized future CI job."""
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import sys
import tarfile
import time
import urllib.request

ROOT = Path('/home/runner/work/btx/btx')
PIN = '371013d61dc124a363521df5b94e97f64d2464f2'
BASE = '1e2f8b5f12295002334d3390c12cac0bb4ae2aff'
RECORDS = ROOT / 'records'
OPTIONS = {
    'BUILD_DAEMON': 'ON', 'BUILD_CLI': 'ON', 'ENABLE_WALLET': 'ON',
    'WITH_SQLITE': 'ON', 'WITH_MODELNET': 'OFF', 'BUILD_GUI': 'OFF',
    'BUILD_TESTS': 'OFF', 'BUILD_BENCH': 'OFF', 'BUILD_FOR_FUZZING': 'OFF',
    'BUILD_FUZZ_BINARY': 'OFF', 'BUILD_TX': 'OFF', 'BUILD_UTIL': 'OFF',
    'BUILD_WALLET_TOOL': 'OFF', 'WITH_CCACHE': 'OFF',
    'CMAKE_BUILD_TYPE': 'Release', 'CMAKE_GENERATOR': 'Ninja',
}


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for data in iter(lambda: stream.read(2**20), b''):
            digest.update(data)
    return digest.hexdigest()


def read(argv, timeout=120):
    return subprocess.check_output(argv, text=True, timeout=timeout)


def save(name, value):
    (RECORDS / name).write_text(json.dumps(value, indent=2) + '\n')


def memory_available():
    return int(re.search(r'^MemAvailable:\s+(\d+)',
                        Path('/proc/meminfo').read_text(), re.M)[1]) * 1024


def cache_options():
    text = (ROOT / 'build/CMakeCache.txt').read_text()
    actual = dict(re.findall(r'^([^#/\n][^:\n]*):[^=\n]+=(.*)$', text, re.M))
    for key, value in OPTIONS.items():
        assert actual.get(key) == value, (key, actual.get(key), value)
    assert actual['CMAKE_HOME_DIRECTORY'] == str(ROOT / 'source')
    return actual


def head_check():
    request = urllib.request.Request(
        'https://api.github.com/repos/btxchain/btx/git/ref/heads/release-0.34.17',
        headers={'Authorization': 'Bearer ' + os.environ['GH_TOKEN'],
                 'Accept': 'application/vnd.github+json', 'User-Agent': 'BTX-wallet-build'})
    with urllib.request.urlopen(request, timeout=45) as response:
        head = json.load(response)
    assert head['object']['sha'] == PIN, 'Head changed: stop and reassess; do not retarget automatically'
    save('head-check.json', head)


def prepare():
    head_check()
    verified = json.loads((RECORDS / 'verification-result.json').read_text())
    assert verified['status'] == 'RESTORE_AND_STATIC_DEPENDENCIES_PASS'
    assert verified['source_pin'] == BASE and verified['restored_objects'] == 725
    assert not verified['producer_extra_source_files']
    assert shutil.disk_usage(ROOT).free >= 15 * 2**30
    assert memory_available() >= 4 * 2**30
    assert max(p.stat().st_mtime for p in (ROOT / 'build').rglob('*.o')) < time.time(), 'Future-dated cache objects'
    original = cache_options()
    save('toolchain.json', {
        'cc': read(['cc', '--version']), 'cxx': read(['c++', '--version']),
        'cmake': read(['cmake', '--version']), 'ninja': read(['ninja', '--version']),
        'ld': read(['ld', '--version']),
        'packages': read(['dpkg-query', '-W', 'build-essential', 'libboost-dev', 'libevent-dev',
                          'libsqlite3-dev', 'libssl-dev', 'libstdc++6']),
    })
    compilers = {}
    for language, executable in [('C', 'cc'), ('CXX', 'c++')]:
        paths = list((ROOT / 'build/CMakeFiles').glob('*/CMake' + language + 'Compiler.cmake'))
        assert len(paths) == 1
        version = re.search(r'set\(CMAKE_' + language + r'_COMPILER_VERSION "([^"]+)"\)', paths[0].read_text())[1]
        active = read([executable, '-dumpfullversion']).strip()
        assert active == version, (language, active, version)
        assert Path(original['CMAKE_' + language + '_COMPILER']).resolve() == Path(shutil.which(executable)).resolve()
        compilers[language] = {'version': version, 'path': original['CMAKE_' + language + '_COMPILER']}
    candidate = ROOT / 'current-reference'
    assert (candidate / '.git').is_dir()
    assert read(['git', '-C', str(candidate), 'rev-parse', 'HEAD']).strip() == PIN
    assert not read(['git', '-C', str(candidate), 'status', '--porcelain', '--untracked-files=all']).strip()
    # This pinned repository has no submodules. A later pin introducing one needs review.
    assert not read(['git', '-C', str(candidate), 'submodule', 'status', '--recursive']).strip()
    stage = read(['git', '-C', str(candidate), 'ls-files', '--stage', '-z']).split('\0')
    names = []
    for entry in filter(None, stage):
        mode, _, rest = entry.split(' ', 2)
        stage_number, name = rest.split('\t', 1)
        assert stage_number == '0' and mode in ('100644', '100755', '120000'), entry
        names.append(name)
    old = ROOT / 'source'
    changed = []
    unchanged = 0
    for name in names:
        current, previous = candidate / name, old / name
        same = (current.is_symlink() and previous.is_symlink() and os.readlink(current) == os.readlink(previous))
        if not current.is_symlink() and not previous.is_symlink() and previous.is_file():
            same = sha(current) == sha(previous)
        if same:
            stat = previous.lstat()
            os.utime(current, ns=(stat.st_atime_ns, stat.st_mtime_ns), follow_symlinks=False)
            unchanged += 1
        else:
            # Changed inputs must be newer than restored object/dependency records.
            os.utime(current, None, follow_symlinks=False)
            changed.append(name)
    assert not (ROOT / 'baseline-source').exists()
    old.rename(ROOT / 'baseline-source')
    candidate.rename(old)
    assert read(['git', '-C', str(old), 'rev-parse', 'HEAD']).strip() == PIN
    assert not read(['git', '-C', str(old), 'status', '--porcelain', '--untracked-files=all']).strip()
    sources = {name: ('symlink:' + os.readlink(old / name) if (old / name).is_symlink() else sha(old / name))
               for name in names}
    save('source-transition.json', {'source': PIN, 'tree': read(['git', '-C', str(old), 'rev-parse', 'HEAD^{tree}']).strip(),
         'unchanged_mtimes_preserved': unchanged, 'changed_files': changed,
         'source_files_sha256': sources, 'compilers': compilers})
    # The old producer does not fingerprint external headers/toolchain binaries.
    # Matching version strings alone cannot prove old .o inputs match this host.
    # Discard object files; reuse source/configuration, never ambiguous compiled inputs.
    objects = sorted((ROOT / 'build').rglob('*.o'))
    invalidated = [str(path.relative_to(ROOT / 'build')) for path in objects]
    for path in objects:
        assert path.resolve().is_relative_to(ROOT / 'build')
        path.unlink()
    save('object-invalidation.json', {'reason': 'Baseline lacks external-header/toolchain-content fingerprint',
         'objects': invalidated, 'count': len(invalidated), 'retained_objects_reused': 0,
         'scope': 'Only requested daemon/CLI target dependencies may rebuild; no whole-project fallback'})
    artifacts = list((ROOT / 'build').rglob('*.a')) + list((ROOT / 'build').rglob('*.so*'))
    artifacts += [ROOT / 'build/bin/btxd', ROOT / 'build/bin/btx-cli']
    removed_outputs = []
    for path in artifacts:
        if path.is_file() or path.is_symlink():
            assert path.absolute().is_relative_to(ROOT / 'build')
            removed_outputs.append(str(path.relative_to(ROOT / 'build')))
            path.unlink()
    save('compiled-output-invalidation.json', {'removed': removed_outputs})
    # Keep the retained cache options; regenerate identity/build graph on actual current source.
    with (RECORDS / 'configure.log').open('w') as log:
        subprocess.run(['cmake', '-S', 'source', '-B', 'build', '-G', 'Ninja'],
                       stdout=log, stderr=subprocess.STDOUT, check=True, timeout=240)
    current_options = cache_options()
    for key in ('CMAKE_C_COMPILER', 'CMAKE_CXX_COMPILER', 'CMAKE_C_FLAGS', 'CMAKE_CXX_FLAGS',
                'CMAKE_C_FLAGS_RELEASE', 'CMAKE_CXX_FLAGS_RELEASE'):
        assert current_options.get(key) == original.get(key), key
    (RECORDS / 'current-CMakeCache.txt').write_bytes((ROOT / 'build/CMakeCache.txt').read_bytes())
    (RECORDS / 'current-config.ini').write_bytes((ROOT / 'build/test/config.ini').read_bytes())
    plan = read(['ninja', '-C', 'build', '-n', 'btxd', 'btx-cli'])
    (RECORDS / 'current-dry-run.log').write_text(plan)
    assert not re.search(r'\b(test_btx|test_bitcoin|btx-qt|btx-modeld|bench_btx|ctest)\b|/fuzz/', plan), plan[-1000:]
    save('preparation.json', {'status': 'PREPARED', 'source': PIN, 'targets': ['btxd', 'btx-cli'],
         'compilers': compilers, 'commands': plan.count('\n'),
         'tests_run': False, 'BTX_binaries_executed': False})


def build():
    preparation = json.loads((RECORDS / 'preparation.json').read_text())
    assert preparation['status'] == 'PREPARED' and preparation['source'] == PIN
    head_check()
    assert memory_available() >= 4 * 2**30 and shutil.disk_usage(ROOT).free >= 15 * 2**30
    started = json.loads((RECORDS / 'job-start.json').read_text())['unix_seconds']
    # Leave ten minutes for checkpoint construction and two uploads within the50-minute job.
    compile_budget = min(1800, 40 * 60 - (time.time() - started))
    assert compile_budget >= 60, 'No useful compile budget left; preserve preflight, do not start'
    result = {'source': PIN, 'targets': ['btxd', 'btx-cli'], 'tests_run': False,
              'BTX_binaries_executed': False, 'samples': [], 'status': 'INCOMPLETE',
              'compile_budget_seconds': compile_budget}
    start = time.monotonic()
    process = None
    try:
        with (RECORDS / 'build.log').open('w') as log:
            # Persist ambiguity before spawn: interruption cannot leave NOT_STARTED for a live child.
            save('compile-process.json', {'state': 'STARTING'})
            process = subprocess.Popen(['cmake', '--build', 'build', '--target', 'btxd', 'btx-cli', '--parallel', '2'],
                                       stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
            save('compile-process.json', {'state': 'RUNNING', 'pgid': process.pid})
            while process.poll() is None:
                elapsed = time.monotonic() - start
                sample = {'seconds': round(elapsed, 1), 'free_disk': shutil.disk_usage(ROOT).free,
                          'available_RAM': memory_available()}
                result['samples'].append(sample)
                if elapsed >= compile_budget or sample['free_disk'] < 1.25 * 2**30 or sample['available_RAM'] < 1.5 * 2**30:
                    result['stop_reason'] = 'compile_budget' if elapsed >= compile_budget else 'resource_floor'
                    raise RuntimeError(result['stop_reason'])
                print('build progress', sample, flush=True)
                time.sleep(10)
            result['exit_code'] = process.returncode
            if process.returncode:
                result['stop_reason'] = 'compile_error'
            assert process.returncode == 0, 'Compile failed; preserve checkpoint, no retry'
            result['status'] = 'BUILD_PASS'
    finally:
        if process is not None and process.poll() is None:
            os.killpg(process.pid, signal.SIGTERM)
            try:
                process.wait(timeout=20)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                process.wait(timeout=10)
        if process is not None:
            # cmake may have exited while a descendant remains in its dedicated group.
            try:
                os.killpg(process.pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
            else:
                deadline = time.monotonic() + 10
                while time.monotonic() < deadline:
                    try:
                        os.killpg(process.pid, 0)
                    except ProcessLookupError:
                        break
                    time.sleep(0.2)
                else:
                    os.killpg(process.pid, signal.SIGKILL)
                    result['cleanup_incomplete'] = True
                    result['status'] = 'INCOMPLETE'
                    result['stop_reason'] = 'process_group_cleanup_unverified'
        result['elapsed_seconds'] = round(time.monotonic() - start, 2)
        save('compile-process.json', {'state': 'UNVERIFIED' if result.get('cleanup_incomplete') else 'QUIESCENT',
                                     'pgid': process.pid if process else None})
        save('build-result.json', result)
        try:
            plan = read(['ninja', '-C', 'build', '-n', 'btxd', 'btx-cli'], timeout=60)
            (RECORDS / 'remaining-dry-run.log').write_text(plan)
        except BaseException as error:
            save('remaining-plan-failure.json', {'error': str(error), 'build_status': result['status']})


def retain():
    # A failed source/preflight stage is not a resumable current build checkpoint.
    preparation_path = RECORDS / 'preparation.json'
    if not preparation_path.exists():
        save('retention.json', {'status': 'NO_CURRENT_CHECKPOINT', 'reason': 'preflight incomplete'})
        return
    preparation = json.loads(preparation_path.read_text())
    assert preparation['status'] == 'PREPARED' and preparation['source'] == PIN
    outcome_path = RECORDS / 'build-result.json'
    process_path = RECORDS / 'compile-process.json'
    assert process_path.exists(), 'No affirmative compiler state; preserve logs, do not archive a potentially live build'
    state = json.loads(process_path.read_text())['state']
    assert state in ('QUIESCENT', 'NOT_STARTED'), 'Compiler group cleanup unverified; do not package'
    assert state == 'NOT_STARTED' or outcome_path.exists(), 'Missing terminal build receipt'
    outcome = json.loads(outcome_path.read_text()) if outcome_path.exists() else {'status': 'INCOMPLETE', 'stop_reason': 'build_not_started'}
    assert not outcome.get('cleanup_incomplete'), 'Do not package a potentially live build'
    sources = json.loads((RECORDS / 'source-transition.json').read_text())
    assert read(['git', '-C', 'source', 'rev-parse', 'HEAD']).strip() == PIN
    # Recheck tracked bytes; generated build products stay outside the source tree.
    for name, expected in sources['source_files_sha256'].items():
        path = ROOT / 'source' / name
        assert ('symlink:' + os.readlink(path) if path.is_symlink() else sha(path)) == expected, name
    retained = ROOT / 'retained'
    retained.mkdir(exist_ok=False)
    producer = {'source_identity': PIN, 'status': 'BUILD_PASS_STATIC_INSPECTION_PENDING' if outcome['status'] == 'BUILD_PASS' else outcome['status'], 'root': str(ROOT),
                'source_transition': sources, 'build_result': outcome, 'tests_run': False,
                'BTX_binaries_executed': False, 'binary_sha256': {},
                'resume_contract': 'Same absolute root/compiler/options/verified source and object timestamps; incomplete outputs are unqualified'}
    producer['toolchain'] = json.loads((RECORDS / 'toolchain.json').read_text())
    producer['object_reuse'] = json.loads((RECORDS / 'object-invalidation.json').read_text())
    checkpoint = retained / 'checkpoint.tar.gz'
    partial = retained / 'checkpoint.partial.tar.gz'
    save('producer.json', producer)
    (retained / 'producer.json').write_bytes((RECORDS / 'producer.json').read_bytes())
    try:
        with tarfile.open(partial, 'w:gz', compresslevel=1, dereference=False) as archive:
            archive.add(ROOT / 'source', arcname='source', recursive=True,
                        filter=lambda member: None if member.name == 'source/.git' or member.name.startswith('source/.git/') else member)
            archive.add(ROOT / 'build', arcname='build', recursive=True)
        partial.rename(checkpoint)
        producer['checkpoint'] = {'sha256': sha(checkpoint), 'bytes': checkpoint.stat().st_size,
                                  'git_metadata_included': False, 'source': PIN}
    except BaseException as error:
        producer['qualification_before_checkpoint_error'] = producer['status']
        producer['status'] = 'CHECKPOINT_FAILED'
        producer['checkpoint_error'] = str(error)
        save('producer.json', producer)
        (retained / 'producer.json').write_bytes((RECORDS / 'producer.json').read_bytes())
        raise
    save('producer.json', producer)
    (retained / 'producer.json').write_bytes((RECORDS / 'producer.json').read_bytes())
    # Checkpoint and provisional producer are durable before optional ELF qualification.
    save('producer.json', producer)
    (retained / 'producer.json').write_bytes((RECORDS / 'producer.json').read_bytes())
    inspection_error = None
    if outcome['status'] == 'BUILD_PASS':
        try:
            from elf_static import inspect
            producer['ELF_dependencies'] = inspect([ROOT / 'build/bin/btxd', ROOT / 'build/bin/btx-cli'], RECORDS)
            for name in ('btxd', 'btx-cli'):
                shutil.copy2(ROOT / 'build/bin' / name, retained / name)
                producer['binary_sha256'][name] = sha(retained / name)
            producer['status'] = 'BUILD_AND_STATIC_INSPECTION_PASS'
        except BaseException as error:
            inspection_error = error
            producer['status'] = 'BUILD_PASS_STATIC_INSPECTION_FAILED'
            producer['inspection_error'] = str(error)
            # Do not expose partial standalone outputs as a qualified binary pair.
            producer['binary_sha256'] = {}
            for name in ('btxd', 'btx-cli'):
                (retained / name).unlink(missing_ok=True)
    save('producer.json', producer)
    (retained / 'producer.json').write_bytes((RECORDS / 'producer.json').read_bytes())
    save('retention.json', {'status': 'RETAINED', 'build_status': outcome['status'],
                            'checkpoint': producer['checkpoint'], 'binary_sha256': producer['binary_sha256']})
    if inspection_error is not None:
        raise RuntimeError('Checkpoint preserved; static binary qualification failed') from inspection_error


if __name__ == '__main__':
    assert Path.cwd() == ROOT and os.environ['GITHUB_REPOSITORY'] == 'sunnyriverr/btx'
    RECORDS.mkdir(exist_ok=True)
    assert sys.argv[1:] in [['head'], ['prepare'], ['build'], ['retain']]
    if not (RECORDS / 'job-start.json').exists():
        save('job-start.json', {'unix_seconds': time.time()})
    if sys.argv[1] == 'build':
        assert not (RECORDS / 'compile-process.json').exists(), 'No automatic second build attempt'
        save('compile-process.json', {'state': 'NOT_STARTED'})
    try:
        {'head': head_check, 'prepare': prepare, 'build': build, 'retain': retain}[sys.argv[1]]()
    except BaseException as error:
        save(sys.argv[1] + '-failure.json', {'error': str(error), 'tests_run': False, 'BTX_binaries_executed': False})
        raise
