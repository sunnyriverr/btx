"""Isolated native adapter qualification; complete maintained test translation units.

The CMake test executable source list is scoped by a recorded build fixture.
No test body/assertion is extracted, disabled or rewritten. No RPC actor is
called by metadata collection; no node/helper process is started by this runner.
"""
from pathlib import Path
import hashlib
import json
import os
import platform
import re
import shlex
import shutil
import signal
import subprocess
import sys
import time

BASE = '666673a3153225ba264c7870e0e82e354df86765'
WORK = Path(os.environ['GITHUB_WORKSPACE'])
HERE = WORK / 'contrib/devtools/rpc-native-adapter'
PRODUCT = WORK / 'p2mr-parent-product'
TASK = WORK / 'p2mr-parent-native'
BUILD = TASK / 'build'
OUT = WORK / 'rpc-native-adapter-results'
OUT.mkdir(exist_ok=True)
STATEFILE = OUT / 'state.json'
STATE = json.loads(STATEFILE.read_text()) if STATEFILE.exists() else {'commands': [], 'phases': {}}
IDENTITY = json.loads((HERE / 'code-identity.json').read_text())
EXPECTED = json.loads((HERE / 'expected-cache.json').read_text())
ENV = dict(os.environ, CC='gcc-13', CXX='g++-13',
           CCACHE_DIR=str(TASK / 'ccache'), CCACHE_BASEDIR=str(WORK),
           CCACHE_COMPILERCHECK='content', CCACHE_MAXSIZE='700M',
           BTX_OPENSSL=str(TASK / 'openssl/bin/openssl'),
           PKG_CONFIG_PATH=str(TASK / 'openssl/lib/pkgconfig'))
FILES = list(IDENTITY['files'])
TEST_SOURCES = ['src/test/main.cpp', 'src/test/rpc_tests.cpp',
                'src/wallet/test/wallet_rpc_tests.cpp', 'src/wallet/test/wallet_test_fixture.cpp']
SCOPE = '\n# Isolated qualification fixture: complete maintained test TUs only.\n'
SCOPE += 'get_target_property(_rpc_original test_btx SOURCES)\n'
SCOPE += 'file(WRITE "${CMAKE_BINARY_DIR}/rpc-original-test-sources.txt" "${_rpc_original}")\n'
SCOPE += 'set_property(TARGET test_btx PROPERTY SOURCES\n' + ''.join(
    '  "${PROJECT_SOURCE_DIR}/' + name + '"\n' for name in TEST_SOURCES) + ')\n'
SCOPE += 'get_target_property(_rpc_selected test_btx SOURCES)\n'
SCOPE += 'file(WRITE "${CMAKE_BINARY_DIR}/rpc-selected-test-sources.txt" "${_rpc_selected}")\n'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save():
    STATEFILE.write_text(json.dumps(STATE, indent=2) + '\n')


def write_changed(path, data):
    if path.read_bytes() != data:
        path.write_bytes(data)


def command(args, label, timeout=120, allowed=(0,), cwd=None):
    print('START', label, flush=True)
    start = time.monotonic()
    with (OUT / (label + '.log')).open('wb') as log:
        proc = subprocess.Popen([str(x) for x in args], cwd=cwd, env=ENV,
                                stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
        last = start
        while proc.poll() is None:
            if time.monotonic() - start > timeout or shutil.disk_usage(OUT).free < 2 * 1024**3:
                os.killpg(proc.pid, signal.SIGTERM)
                try:
                    proc.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    os.killpg(proc.pid, signal.SIGKILL)
                    proc.wait()
                raise RuntimeError(label + ': time/storage limit')
            if time.monotonic() - last > 20:
                log.flush()
                lines = (OUT / (label + '.log')).read_text(errors='replace').splitlines()
                print(label, lines[-1] if lines else 'running', flush=True)
                last = time.monotonic()
            time.sleep(1)
    row = {'label': label, 'args': [str(x) for x in args], 'cwd': str(cwd),
           'exit': proc.returncode, 'seconds': round(time.monotonic() - start, 2)}
    STATE['commands'].append(row)
    save()
    print('END', label, proc.returncode, flush=True)
    if proc.returncode not in allowed:
        raise RuntimeError(label + ': unexpected exit ' + str(proc.returncode))
    return (OUT / (label + '.log')).read_text(errors='replace')


def audit(label, variant='candidate', configured=True):
    assert subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=PRODUCT, text=True).strip() == BASE
    tree = subprocess.check_output(['git', 'ls-tree', '-r', '-z', BASE], cwd=PRODUCT)
    rows = {}
    for item in tree.split(b'\0'):
        if not item:
            continue
        metadata, raw_name = item.split(b'\t', 1)
        mode, kind, blob = metadata.decode().split()
        name = os.fsdecode(raw_name)
        path = PRODUCT / name
        data = os.fsencode(os.readlink(path)) if mode == '120000' else path.read_bytes()
        if name in FILES:
            expected = candidate_bytes(name, variant)
        elif configured and name == 'CMakeLists.txt':
            expected = subprocess.check_output(['git', 'show', BASE + ':' + name], cwd=PRODUCT) + SCOPE.encode()
        else:
            expected = None
        actual = hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()
        assert data == expected if expected is not None else actual == blob, name
        actual_mode = '120000' if path.is_symlink() else ('100755' if path.stat().st_mode & 0o111 else '100644')
        assert actual_mode == mode, (name, actual_mode, mode)
        rows[name] = actual
    dest = OUT / ('source-' + label + '.json')
    dest.write_text(json.dumps(rows, sort_keys=True) + '\n')
    STATE.setdefault('source_audits', {})[label] = {'variant': variant, 'files': len(rows), 'sha256': sha(dest)}
    save()


def candidate_bytes(name, variant='candidate'):
    data = (HERE / 'candidate' / name).read_bytes()
    assert hashlib.sha256(data).hexdigest() == IDENTITY['files'][name]['sha256']
    if variant == 'wallet_omission' and name == 'src/wallet/interfaces.cpp':
        old = b'            m_rpc_commands.back().argument_factory = command.argument_factory;'
        assert data.count(old) == 1
        return data.replace(old, b'            // Controlled omission of wallet metadata propagation.')
    if variant == 'constructor_omission' and name == 'src/rpc/server.h':
        old = b'        argument_factory = fn;'
        assert data.count(old) == 1
        return data.replace(old, b'        // Controlled omission of constructor metadata propagation.')
    return data


def preflight():
    assert platform.system() == 'Linux' and platform.machine() == 'x86_64'
    assert shutil.disk_usage(OUT).free > 8 * 1024**3
    STATE['runner'] = {'platform': platform.platform(), 'run_id': os.environ['GITHUB_RUN_ID'],
                       'fixture': os.environ['GITHUB_SHA'], 'candidate': IDENTITY['commit']}
    for name in FILES:
        write_changed(PRODUCT / name, candidate_bytes(name))
    audit('candidate-before', configured=False)


def dependencies():
    command(['sudo', 'apt-get', '-o', 'Acquire::Retries=1', 'update'], 'apt-update', timeout=240)
    command(['sudo', 'apt-get', 'install', '-y', '--no-install-recommends',
             'g++-13', 'ninja-build', 'pkgconf', 'libevent-dev', 'libboost-dev',
             'libsqlite3-dev', 'libzmq3-dev', 'ccache'], 'apt-install', timeout=420)
    command(['g++-13', '--version'], 'compiler')


def configure():
    assert sha(BUILD / 'CMakeCache.txt') == EXPECTED['cmake_cache_sha256']
    for name, entry in EXPECTED['binaries'].items():
        assert sha(BUILD / 'bin' / name) == entry['sha256']
    for name, expected in EXPECTED['openssl']['files'].items():
        assert sha(TASK / 'openssl' / name) == expected
    root = PRODUCT / 'CMakeLists.txt'
    root.write_bytes(root.read_bytes() + SCOPE.encode())
    command(['cmake', '-S', PRODUCT, '-B', BUILD, '-DBUILD_TESTS=ON',
             '-DCMAKE_CXX_COMPILER_LAUNCHER=ccache', '-DCMAKE_C_COMPILER_LAUNCHER=ccache'],
            'configure-scoped-maintained-target', timeout=180)
    selected = (BUILD / 'rpc-selected-test-sources.txt').read_text().split(';')
    assert selected == [str(PRODUCT / name) for name in TEST_SOURCES]
    shutil.copyfile(BUILD / 'rpc-original-test-sources.txt', OUT / 'default-test-source-list.txt')
    shutil.copyfile(BUILD / 'rpc-selected-test-sources.txt', OUT / 'scoped-test-source-list.txt')
    shutil.copyfile(BUILD / 'CMakeCache.txt', OUT / 'CMakeCache.txt')
    STATE['build_scope'] = {'test_TUs': TEST_SOURCES, 'default_full_test_btx': False,
                            'source_fixture_sha256': hashlib.sha256(SCOPE.encode()).hexdigest(),
                            'expected_cache_id': EXPECTED['cache_id'], 'cache_save': False,
                            'actual_matched_cache_key': os.environ.get('CACHE_MATCHED_KEY'),
                            'cache_hit': os.environ.get('CACHE_HIT')}
    audit('configured')


def build(label):
    plan = command(['ninja', '-C', BUILD, '-n', 'test_btx'], 'plan-' + label, timeout=60)
    # A dry run can stop at CMake's mandatory glob/regeneration edge. Inspect
    # the generated transitive graph too; do not mistake that edge for a full
    # compilation plan or disable source-roster verification.
    graph = command(['ninja', '-C', BUILD, '-t', 'commands', 'test_btx'],
                    'command-graph-' + label, timeout=60)
    lines = graph.splitlines()
    assert len(lines) <= 1200, 'Unexpectedly broad native command graph'
    for name in TEST_SOURCES:
        matches = [line for line in lines if str(PRODUCT / name) in line
                   and 'test_btx.dir' in line and ' -c ' in line]
        assert len(matches) == 1, (name, 'Missing or duplicated maintained translation unit')
    command(['cmake', '--build', BUILD, '--target', 'test_btx', '-j2'], 'build-' + label, timeout=1500)
    STATE.setdefault('binaries', {})[label] = {'sha256': sha(BUILD / 'bin/test_btx')}
    save()


def test_object_hashes():
    entries = json.loads((BUILD / 'compile_commands.json').read_text())
    hashes = {}
    for name in ['src/test/rpc_tests.cpp', 'src/wallet/test/wallet_rpc_tests.cpp']:
        selected = [entry for entry in entries if Path(entry['file']) == PRODUCT / name
                    and 'test_btx.dir' in entry['command']]
        assert len(selected) == 1
        args = shlex.split(selected[0]['command'])
        obj = Path(args[args.index('-o') + 1])
        if not obj.is_absolute():
            obj = Path(selected[0]['directory']) / obj
        hashes[name] = sha(obj)
    return hashes


def run_case(label, selector, negative=False):
    text = command([BUILD / 'bin/test_btx', '--run_test=' + selector,
                    '--report_level=detailed', '--log_level=test_suite'], label,
                   timeout=180, allowed=(201,) if negative else (0,))
    assert 'No errors detected' in text if not negative else 'AVAILABLE' in text
    STATE.setdefault('case_results', {})[label] = {'selector': selector,
        'exit': STATE['commands'][-1]['exit'], 'binary_sha256': sha(BUILD / 'bin/test_btx')}
    save()


def test():
    core = 'rpc_tests/rpc_argument_metadata_*'
    wallet = 'wallet_rpc_tests/wallet_rpc_argument_metadata_registration'
    build('candidate')
    run_case('candidate-core', core)
    run_case('candidate-wallet', wallet)
    run_case('existing-converter-formats', 'rpc_tests/rpc_convert_values_modelnet_methods')
    initial_objects = test_object_hashes()
    STATE['candidate_test_objects'] = initial_objects
    save()
    for variant, selector in [('wallet_omission', wallet), ('constructor_omission', core)]:
        for name in FILES:
            write_changed(PRODUCT / name, candidate_bytes(name, variant))
        audit(variant + '-before', variant)
        build(variant)
        if variant == 'wallet_omission':
            assert test_object_hashes() == initial_objects, 'Wallet control must reuse exact same test objects'
        run_case(variant + '-negative', selector, negative=True)
    for name in FILES:
        write_changed(PRODUCT / name, candidate_bytes(name))
    audit('restored-before-build')
    build('restored')
    run_case('restored-core', core)
    run_case('restored-wallet', wallet)
    STATE['restored_test_objects'] = test_object_hashes()
    assert STATE['restored_test_objects'] == initial_objects
    audit('final')
    STATE['qualified'] = True
    STATE['full_rpc_help_test_green'] = False
    STATE['full_default_suite_run'] = False
    save()


def finalize():
    # Runner and restored cache are disposable; never save changed objects to
    # the original cache key. Preserve failures and restore only owned source.
    for name in FILES:
        write_changed(PRODUCT / name, candidate_bytes(name))
    STATE['cleanup'] = {'candidate_sources_restored': True, 'node_helper_started': False,
                        'original_remote_cache_saved': False}
    (OUT / 'result.json').write_text(json.dumps(STATE, indent=2) + '\n')


phase = sys.argv[1]
try:
    globals()[phase]()
    STATE['phases'][phase] = 'pass'
    save()
except Exception as error:
    STATE['phases'][phase] = 'fail'
    STATE.setdefault('errors', []).append(phase + ': ' + repr(error))
    save()
    raise
