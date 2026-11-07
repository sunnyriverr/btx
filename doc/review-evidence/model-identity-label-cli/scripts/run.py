"""Build normal current-source CLI targets; pair one maintained case and real workflow."""
from pathlib import Path
import configparser
import hashlib
import json
import os
import platform
import re
import shutil
import signal
import subprocess
import sys
import tarfile
import time
import urllib.request
import xml.etree.ElementTree as ET

BASE = '0ac06fd23b4a62038963fb29f1c77ab26d7a1346'
ASSET_SHA = '58657765b5ac41252c44913f56c61247b781149fd21ed79374aedade67805ba1'
W = Path(os.environ['GITHUB_WORKSPACE'])
P = W / 'p2mr-parent-product'
H = W / 'contrib/devtools/identity-label-repair'
TASK = W / 'p2mr-parent-native'
BUILD = TASK / 'build'
OWN = TASK / 'identity-label-repair'
O = W / 'identity-label-repair-results'
R = W / 'identity-label-pair'
PACKAGE_DIR = W / 'identity-label-package'
O.mkdir(exist_ok=True)
STATEFILE = O / 'state.json'
STATE = json.loads(STATEFILE.read_text()) if STATEFILE.exists() else {'commands': [], 'phases': {}, 'errors': []}
I = json.loads((H / 'code-identity.json').read_text())
E = json.loads((H / 'expected-cache.json').read_text())
ENV = dict(os.environ, CC='gcc-13', CXX='g++-13', PYTHONDONTWRITEBYTECODE='1',
           PYTHONPATH=str(P / 'test/functional'), PKG_CONFIG_PATH=str(TASK / 'openssl/lib/pkgconfig'),
           CCACHE_DIR=str(TASK / 'ccache'), CCACHE_BASEDIR=str(W),
           CCACHE_COMPILERCHECK='content', CCACHE_MAXSIZE='700M')


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save():
    STATEFILE.write_text(json.dumps(STATE, indent=2) + '\n')


def package():
    return Path(STATE['package_root']) if STATE.get('package_root') else None


def command(args, label, timeout=120, allowed=(0,), cwd=None):
    print('START', label, flush=True)
    start = time.monotonic()
    with (O / (label + '.log')).open('wb') as log:
        proc = subprocess.Popen([str(x) for x in args], cwd=cwd, env=ENV,
                                stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
        last = start
        while proc.poll() is None:
            if time.monotonic() - start > timeout or shutil.disk_usage(O).free < 2 * 1024**3:
                os.killpg(proc.pid, signal.SIGTERM)
                try:
                    proc.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    os.killpg(proc.pid, signal.SIGKILL)
                    proc.wait()
                raise RuntimeError(label + ': time/storage limit')
            if time.monotonic() - last > 20:
                log.flush()
                lines = (O / (label + '.log')).read_text(errors='replace').splitlines()
                print(label, lines[-1] if lines else 'running', flush=True)
                last = time.monotonic()
            time.sleep(1)
    STATE['commands'].append({'label': label, 'args': [str(x) for x in args], 'cwd': str(cwd),
                              'exit': proc.returncode, 'seconds': round(time.monotonic() - start, 2)})
    save()
    assert proc.returncode in allowed, (label, proc.returncode)
    print('END', label, proc.returncode, flush=True)
    return (O / (label + '.log')).read_text(errors='replace')


def candidate(name):
    data = (H / 'candidate' / name).read_bytes()
    assert hashlib.sha256(data).hexdigest() == I['files'][name]['sha256']
    return data


def audit(label, variant):
    assert subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=P, text=True).strip() == BASE
    rows = {}
    for item in subprocess.check_output(['git', 'ls-tree', '-r', '-z', BASE], cwd=P).split(b'\0'):
        if not item:
            continue
        meta, raw_name = item.split(b'\t', 1)
        mode, kind, blob = meta.decode().split()
        assert kind == 'blob'
        name = os.fsdecode(raw_name)
        path = P / name
        data = os.fsencode(os.readlink(path)) if mode == '120000' else path.read_bytes()
        wanted = candidate(name) if name == 'src/test/rpc_tests.cpp' or (variant == 'candidate' and name == 'src/rpc/client.cpp') else None
        actual = hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()
        assert data == wanted if wanted is not None else actual == blob, name
        actual_mode = '120000' if path.is_symlink() else ('100755' if path.stat().st_mode & 0o111 else '100644')
        assert actual_mode == mode, name
        rows[name] = actual
    dest = O / ('source-' + label + '.json')
    dest.write_text(json.dumps(rows, sort_keys=True) + '\n')
    STATE.setdefault('source_audits', {})[label] = {'variant': variant, 'files': len(rows), 'sha256': sha(dest)}
    save()


def processes():
    rows = []
    for pid in Path('/proc').iterdir():
        if not pid.name.isdigit():
            continue
        try:
            exe = Path(os.readlink(pid / 'exe'))
            pkg = package()
            if (pkg is not None and exe.is_relative_to(pkg)) or exe.is_relative_to(OWN):
                rows.append({'pid': int(pid.name), 'exe': str(exe)})
        except OSError:
            pass
    return rows


def package_hashes():
    return {str(f.relative_to(package())): sha(f) for f in package().rglob('*') if f.is_file()}


def preflight():
    assert platform.system() == 'Linux' and platform.machine() == 'x86_64'
    assert shutil.disk_usage(W).free > 8 * 1024**3
    assert I['base'] == BASE
    original = subprocess.check_output(['git', 'show', BASE + ':src/rpc/client.cpp'], cwd=P)
    assert candidate('src/rpc/client.cpp') == original.replace(b'    { "createmodelidentity", 0, "label" },\n', b'', 1)
    regression = (H / 'regression.inc').read_bytes()
    assert hashlib.sha256(regression).hexdigest() == I['regression_sha256']
    assert candidate('src/test/rpc_tests.cpp').replace(regression, b'', 1) == subprocess.check_output(
        ['git', 'show', BASE + ':src/test/rpc_tests.cpp'], cwd=P)
    (P / 'src/test/rpc_tests.cpp').write_bytes(candidate('src/test/rpc_tests.cpp'))
    STATE['runner'] = {'platform': platform.platform(), 'run': os.environ['GITHUB_RUN_ID'],
                       'fixture': os.environ['GITHUB_SHA'], 'candidate': I['commit']}
    STATE['source'] = BASE
    STATE['case_sha256'] = sha(H / 'case.py')
    audit('baseline-before', 'baseline')


def dependencies():
    command(['sudo', 'apt-get', '-o', 'Acquire::Retries=1', 'update'], 'apt-update', timeout=240)
    command(['sudo', 'apt-get', 'install', '-y', '--no-install-recommends', 'g++-13', 'ninja-build',
             'pkgconf', 'libevent-dev', 'libboost-dev', 'libsqlite3-dev', 'libzmq3-dev', 'ccache'],
            'apt-install', timeout=420)
    command(['g++-13', '--version'], 'compiler')


def prepare():
    assert sha(BUILD / 'CMakeCache.txt') == E['cmake_cache_sha256']
    for name, expected in E['binaries'].items():
        assert sha(BUILD / 'bin' / name) == expected['sha256']
    for name, expected in E['openssl']['files'].items():
        assert sha(TASK / 'openssl' / name) == expected
    STATE['cache'] = {'id': E['cache_id'], 'save': False,
                      'matched_key': os.environ['CACHE_MATCHED_KEY'], 'hit': os.environ['CACHE_HIT']}
    assert STATE['cache']['hit'] == 'true'
    assert STATE['cache']['matched_key'] == 'btx-p2mr-external-parent-v1-666673a3-ubuntu24-gcc13-O1-walletON-modelnetON-ssl359'
    command(['cmake', '-S', P, '-B', BUILD, '-DBUILD_TESTS=ON',
             '-DCMAKE_CXX_COMPILER_LAUNCHER=ccache', '-DCMAKE_C_COMPILER_LAUNCHER=ccache'], 'configure-current', timeout=180)
    cache = (BUILD / 'CMakeCache.txt').read_text()
    for value in ['ENABLE_WALLET:BOOL=ON', 'WITH_MODELNET:BOOL=ON', 'CMAKE_CXX_FLAGS_RELEASE:STRING=-O1']:
        assert value in cache
    shutil.copyfile(BUILD / 'CMakeCache.txt', O / 'CMakeCache.txt')
    archive = W / 'identity-label-release.tar.gz'
    url = 'https://github.com/btxchain/btx/releases/download/v0.34.16/btx-0.34.16-x86_64-linux-gnu.tar.gz'
    with urllib.request.urlopen(url, timeout=60) as source, archive.open('wb') as dest:
        shutil.copyfileobj(source, dest)
    assert sha(archive) == ASSET_SHA and archive.stat().st_size == 158893635
    STATE['asset'] = {'id': 720210208, 'bytes': 158893635, 'sha256': ASSET_SHA,
                      'source_mapping': 'Numair published replacement for0ac; producerbuildnotindependentlyreproduced'}
    PACKAGE_DIR.mkdir()
    with tarfile.open(archive) as tar:
        assert sum(m.size for m in tar.getmembers()) < 2 * 1024**3
        tar.extractall(PACKAGE_DIR, filter='data')
    archive.unlink()
    nodes = list(PACKAGE_DIR.rglob('bin/btxd'))
    assert len(nodes) == 1
    STATE['package_root'] = str(nodes[0].parent.parent)
    STATE['package_files_before'] = package_hashes()
    command([package() / 'bin/btxd', '-version'], 'package-node-version')
    help_text = command([package() / 'bin/btxd', '-help-debug'], 'package-features')
    assert '-wallet=<path>' in help_text and '-modelrpcsocket=' in help_text
    config = configparser.ConfigParser()
    config['environment'] = {'CLIENT_NAME': 'BTX', 'CLIENT_BUGREPORT': 'https://github.com/btxchain/btx/issues',
                             'SRCDIR': str(P), 'BUILDDIR': str(package()), 'EXEEXT': '',
                             'RPCAUTH': str(P / 'share/rpcauth/rpcauth.py')}
    config['components'] = {'ENABLE_WALLET': 'true', 'ENABLE_MODELNET': 'true', 'ENABLE_CLI': 'true',
                            'ENABLE_BITCOIND': 'true', 'USE_SQLITE': 'true', 'USE_BDB': 'false',
                            'ENABLE_ZMQ': str('-zmqpubhashblock=' in help_text).lower(),
                            'ENABLE_EXTERNAL_SIGNER': str('-signer=<cmd>' in help_text).lower(),
                            'ENABLE_WALLET_TOOL': 'false', 'ENABLE_BITCOIN_UTIL': 'false', 'ENABLE_USDT_TRACEPOINTS': 'false'}
    with (O / 'functional-config.ini').open('w') as dest:
        config.write(dest)
    OWN.mkdir()
    R.mkdir(mode=0o700)
    save()


def build_cli(label, timeout):
    command(['ninja', '-C', BUILD, '-n', 'btx-cli'], 'plan-' + label, timeout=60)
    graph = command(['ninja', '-C', BUILD, '-t', 'commands', 'btx-cli'], 'graph-' + label, timeout=60)
    own_compile = [line for line in graph.splitlines() if str(P / 'src/rpc/client.cpp') in line and ' -c ' in line]
    assert len(own_compile) == 1
    assert not any('test_btx.dir' in line for line in graph.splitlines())
    command(['cmake', '--build', BUILD, '--target', 'btx-cli', '-j2'], 'build-' + label, timeout=timeout)
    dest = OWN / label
    dest.mkdir()
    shutil.copy2(BUILD / 'bin/btx-cli', dest / 'btx-cli')
    data = subprocess.check_output(['ar', 'p', BUILD / 'lib/libbitcoin_cli.a', 'client.cpp.o'])
    (dest / 'client.cpp.o').write_bytes(data)
    STATE.setdefault('cli_pair', {})[label] = {'sha256': sha(dest / 'btx-cli'), 'client_object': sha(dest / 'client.cpp.o')}
    command([dest / 'btx-cli', '-version'], 'cli-version-' + label)
    dynamic = command(['ldd', dest / 'btx-cli'], 'cli-ldd-' + label)
    assert 'not found' not in dynamic
    save()


def unit(label):
    obj = OWN / 'unit.o'
    if not obj.exists():
        wrapper = OWN / 'unit.cpp'
        wrapper.write_text('#define BOOST_TEST_MODULE identity_label_conversion\n#include <vector>\n#include <string>\n'
                           '#include <boost/test/included/unit_test.hpp>\n#include <rpc/client.h>\n#include <univalue.h>\n'
                           'BOOST_AUTO_TEST_SUITE(rpc_tests)\n' + (H / 'regression.inc').read_text() + 'BOOST_AUTO_TEST_SUITE_END()\n')
        command(['g++-13', '-std=c++20', '-O0', '-I' + str(P / 'src'), '-I' + str(P / 'src/univalue/include'),
                 '-c', wrapper, '-o', obj], 'compile-maintained-unit-body', timeout=180)
        STATE['same_unit_object_sha256'] = sha(obj)
    assert sha(obj) == STATE['same_unit_object_sha256']
    libs = list(BUILD.rglob('libunivalue.a'))
    assert len(libs) == 1
    if label == 'baseline':
        STATE['same_univalue_archive_sha256'] = sha(libs[0])
    assert sha(libs[0]) == STATE['same_univalue_archive_sha256']
    binary = OWN / label / 'unit'
    command(['g++-13', obj, OWN / label / 'client.cpp.o', libs[0], '-pthread', '-o', binary], 'link-unit-' + label)
    report = O / ('unit-' + label + '.xml')
    command([binary, '--run_test=rpc_tests/rpc_convert_model_identity_labels_are_literal', '--color_output=no',
             '--log_level=message', '--report_level=detailed', '--report_format=XML', '--report_sink=' + str(report)],
            'unit-' + label, allowed=(201,) if label == 'baseline' else (0,))
    cases = list(ET.parse(report).getroot().iter('TestCase'))
    assert len(cases) == 1 and cases[0].attrib['name'] == 'rpc_convert_model_identity_labels_are_literal'
    assert cases[0].attrib['result'] == ('failed' if label == 'baseline' else 'passed')
    STATE.setdefault('unit_pair', {})[label] = {'exit': STATE['commands'][-1]['exit'], 'report': cases[0].attrib,
                                               'binary_sha256': sha(binary), 'same_unit_object_sha256': sha(obj)}
    save()


def workflow(label):
    root = R / label
    root.mkdir(mode=0o700)
    output = O / label
    output.mkdir()
    ENV.update(IDENTITY_RUNTIME=str(root), IDENTITY_RESULTS=str(output),
               IDENTITY_CLI_BINARY=str(OWN / label / 'btx-cli'))
    assert sha(H / 'case.py') == STATE['case_sha256']
    assert sha(OWN / label / 'btx-cli') == STATE['cli_pair'][label]['sha256'] and not processes()
    command(['python3', H / 'case.py', '--configfile=' + str(O / 'functional-config.ini'),
             '--tmpdir=' + str(root / 'node-test'), '--cachedir=' + str(root / 'chain-cache'),
             '--portseed=43418', '--nocleanup'], 'workflow-' + label, timeout=180,
            allowed=(1,) if label == 'baseline' else (0,))
    observed = json.loads((output / 'observations.json').read_text())
    assert observed['controls_complete'] and observed['node_rpc_shutdown_complete']
    assert all(row['passed'] for row in observed['controls'])
    assert observed['helper_returncode'] in (0, -15)
    assert len(observed['cli']) == 20 and len(observed['requirements']) == 20
    assert observed['acceptance_pass'] == (label == 'candidate')
    assert sum(not row['passed'] for row in observed['requirements']) == (18 if label == 'baseline' else 0)
    assert not processes() and sha(OWN / label / 'btx-cli') == STATE['cli_pair'][label]['sha256']
    STATE.setdefault('workflow_pair', {})[label] = {'exit': STATE['commands'][-1]['exit'],
        'case_sha256': sha(H / 'case.py'), 'acceptance_pass': observed['acceptance_pass'],
        'failed_requirements': sum(not row['passed'] for row in observed['requirements']),
        'controls_complete': True, 'cli_sha256': sha(OWN / label / 'btx-cli')}
    save()


def baseline():
    build_cli('baseline', 1500)
    unit('baseline')
    workflow('baseline')
    STATE['archives_before_candidate'] = {str(f.relative_to(BUILD)): sha(f) for f in BUILD.rglob('*.a')}
    audit('baseline-after', 'baseline')
    save()


def test():
    (P / 'src/rpc/client.cpp').write_bytes(candidate('src/rpc/client.cpp'))
    audit('candidate-before', 'candidate')
    build_cli('candidate', 240)
    after = {str(f.relative_to(BUILD)): sha(f) for f in BUILD.rglob('*.a')}
    before = STATE['archives_before_candidate']
    assert set(before) == set(after)
    changed = [n for n in before if before[n] != after[n]]
    assert set(changed).issubset({'lib/libbitcoin_cli.a', 'lib/libbitcoin_clientversion.a'})
    STATE['changed_archives_for_candidate'] = changed
    unit('candidate')
    workflow('candidate')
    assert package_hashes() == STATE['package_files_before']
    audit('candidate-after', 'candidate')
    STATE['paired_proof_pass'] = True
    STATE['full_test_btx_or_full_suite'] = False
    save()


def finalize():
    before = processes()
    for row in before:
        os.kill(row['pid'], signal.SIGTERM)
    for _ in range(100):
        if not processes():
            break
        time.sleep(.1)
    remaining = processes()
    if R.exists():
        for path in R.rglob('*'):
            if path.is_file() and path.name in ['debug.log', 'test_framework.log']:
                dest = O / 'functional-logs' / path.relative_to(R)
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(path, dest)
        if not remaining:
            shutil.rmtree(R)
    STATE['cleanup'] = {'before': before, 'remaining': remaining, 'runtime_removed': not R.exists(),
                        'original_remote_cache_saved': False}
    if (P / 'src/rpc/client.cpp').exists():
        (P / 'src/rpc/client.cpp').write_bytes(candidate('src/rpc/client.cpp'))
    STATE['qualified'] = bool(STATE.get('paired_proof_pass') and not STATE['errors'] and not before and not remaining and not R.exists())
    save()
    (O / 'result.json').write_text(json.dumps(STATE, indent=2) + '\n')
    assert STATE['qualified'], 'Incomplete paired proof or cleanup; inspect result'


phase = sys.argv[1]
try:
    globals()[phase]()
    STATE['phases'][phase] = 'pass'
    save()
except Exception as error:
    STATE['phases'][phase] = 'fail'
    STATE['errors'].append(phase + ': ' + repr(error))
    save()
    raise
