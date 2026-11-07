"""Same unchanged ELF package, before/after the production Linux staging fix."""
from pathlib import Path
import hashlib
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tarfile
import time
import traceback
import urllib.request

W = Path(os.environ['GITHUB_WORKSPACE'])
SOURCE = W / 'product'
HERE = Path(__file__).parent
OUT = W / 'guard-package-repair-results'
OUT.mkdir()
BASE = '0ac06fd23b4a62038963fb29f1c77ab26d7a1346'
EXPECTED = '58657765b5ac41252c44913f56c61247b781149fd21ed79374aedade67805ba1'
state = {'source': BASE, 'fixture': os.environ['GITHUB_SHA'], 'commands': [],
         'phases': {}, 'qualified': False, 'cache_used': False, 'source_build': False}
env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1')


def sha(p):
    h = hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda: f.read(1024 * 1024), b''):
            h.update(b)
    return h.hexdigest()


def save():
    (OUT / 'result.json').write_text(json.dumps(state, indent=2) + '\n')


def run(args, label, expected, timeout=120):
    start = time.monotonic()
    with (OUT / (label + '.log')).open('wb') as log:
        proc = subprocess.run([str(a) for a in args], cwd=SOURCE, env=env,
                              stdout=log, stderr=subprocess.STDOUT, timeout=timeout)
    state['commands'].append({'label': label, 'args': [str(a) for a in args],
                              'returncode': proc.returncode, 'seconds': time.monotonic() - start})
    save()
    assert proc.returncode == expected, (label, proc.returncode, expected)


def phase(name, expected):
    run([sys.executable, HERE / 'case.py', package, OUT / name, name], name, expected, timeout=180)
    s = json.loads((OUT / name / 'result.json').read_text())
    assert len(s['boots']) == 2 and all(len(b['health']) == 10 for b in s['boots'])
    assert all(all(x['pass'] for x in b['health']) for b in s['boots'])
    assert not s['cleanup_before'] and not s['cleanup_remaining'] and not s['cleanup_signals']
    assert s['runtime_removed'] and s['source_before'] == s['source_after']
    assert s['package_files_before'] == s['package_files_after']
    failed = [x['name'] for x in s['checks'] if not x['pass']]
    if expected == 1:
        assert failed == ['packaged guard actually answers on both boots and throughout health polls'], failed
        assert s['guard_contract_pass'] is False and s['passed'] is False
        assert all(not b['guard']['ready'] and 'SEC_GUARD_NOT_READY' in b['guard']['error'] for b in s['boots'])
        assert all('GUARD_EXECUTABLE_ABSENT' in (OUT / name / ('boot' + str(i) + '-console.log')).read_text() for i in [1, 2])
    else:
        assert not failed and s['guard_contract_pass'] is True and s['passed'] is True
        assert s['boots'][0]['guard']['reply']['guard_boot'] != s['boots'][1]['guard']['reply']['guard_boot']
        for b in s['boots']:
            g = b['guard']['processes'][0]
            assert g['ppid'] == b['node']['pid'] and g['exe'] == str(package / 'libexec/btx-guardd')
            assert all(x['ready'] for x in b['guard_health'])
    state['phases'][name] = {'returncode': expected, 'checks': len(s['checks']),
                              'failed_checks': failed, 'boot_count': 2, 'health_polls': 20,
                              'guard_ready': s['guard_contract_pass'], 'cleanup_pass': True}
    save()


try:
    assert subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=SOURCE, text=True).strip() == BASE
    assert not subprocess.check_output(['git', 'status', '--porcelain'], cwd=SOURCE)
    assert shutil.disk_usage(W).free > 3 * 1024**3
    identity = json.loads((HERE / 'code-identity.json').read_text())
    state['candidate'] = identity
    for relative, digest in identity['files'].items():
        assert sha(HERE / 'payload' / relative) == digest
    production = 'scripts/release/package_release_archive.py'
    test = 'test/util/package_release_archive_test.py'
    state['baseline_packager_sha256'] = sha(SOURCE / production)
    shutil.copyfile(HERE / 'payload' / test, SOURCE / test)
    run([sys.executable, SOURCE / test], 'maintained-before', 1)
    log = (OUT / 'maintained-before.log').read_text()
    assert 'Ran 17 tests' in log and 'FAILED (failures=1)' in log
    assert 'FAIL: test_linux_guard_remains_a_regular_daemon_sibling_after_extraction' in log
    archive = W / 'guard-package-original.tar.gz'
    with urllib.request.urlopen('https://github.com/btxchain/btx/releases/download/v0.34.16/btx-0.34.16-x86_64-linux-gnu.tar.gz', timeout=60) as r, archive.open('wb') as f:
        shutil.copyfileobj(r, f)
    assert sha(archive) == EXPECTED and archive.stat().st_size == 158893635
    state['archive'] = {'sha256': EXPECTED, 'asset_id': 720210208, 'bytes': archive.stat().st_size}
    install = W / 'guard-package-installation'
    install.mkdir()
    with tarfile.open(archive) as tar:
        assert sum(m.size for m in tar.getmembers()) < 2 * 1024**3
        tar.extractall(install, filter='data')
    archive.unlink()
    nodes = list(install.rglob('bin/btxd'))
    assert len(nodes) == 1
    package = nodes[0].parent.parent.resolve()
    original = {str(f.relative_to(package)): sha(f) for f in package.rglob('*') if f.is_file()}
    assert len(original) == 127
    assert 'libexec/btx-guardd' not in original
    state['original_package_files'] = original
    state['case_sha256'] = sha(HERE / 'case.py')
    phase('before', 1)
    shutil.copyfile(HERE / 'payload' / production, SOURCE / production)
    run([sys.executable, SOURCE / test], 'maintained-after', 0)
    assert 'Ran 17 tests' in (OUT / 'maintained-after.log').read_text()
    # Exercise actual production stage_release_tree using unchanged real ELF inputs.
    # Only the generated additional guard file is installed into the full archive.
    inputs_root = W / 'guard-stage-inputs'
    inputs = inputs_root / 'bin'
    inputs.mkdir(parents=True)
    os.symlink(package / 'lib', inputs_root / 'lib', target_is_directory=True)
    for name in ['btxd', 'btx-cli', 'btx-util', 'btx-guardd', 'btx-modeld']:
        os.link(package / 'libexec' / (name + '.real'), inputs / name)
    spec = importlib.util.spec_from_file_location('packager_candidate', SOURCE / production)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    # All real portability gates remain enabled. No synthetic ship-gate stubs here.
    start = time.monotonic()
    staged, included, skipped = module.stage_release_tree(
        version='0.34.16', platform_id='linux-x86_64', btxd_path=inputs / 'btxd',
        btx_cli_path=inputs / 'btx-cli', btx_util_path=inputs / 'btx-util',
        matmul_metallib_path=None, oracle_metallib_path=None, metal_lib_dir=None,
        source_root=SOURCE, temp_root=W / 'guard-production-stage')
    generated = staged / 'libexec/btx-guardd'
    assert generated.is_file() and not generated.is_symlink()
    assert generated.samefile(staged / 'libexec/btx-guardd.real')
    assert sha(generated) == original['libexec/btx-guardd.real']
    sibling = package / 'libexec/btx-guardd'
    os.link(generated, sibling)
    candidate = {str(f.relative_to(package)): sha(f) for f in package.rglob('*') if f.is_file()}
    assert set(candidate) - set(original) == {'libexec/btx-guardd'}
    assert all(candidate[k] == v for k, v in original.items())
    state['staging'] = {'seconds': time.monotonic() - start, 'included': included,
                        'skipped_optional_helpers': skipped, 'generated_guard_sha256': sha(generated),
                        'mode': oct(generated.stat().st_mode & 0o777),
                        'all_127_original_files_unchanged': len(original) == 127,
                        'one_added_regular_file': 'libexec/btx-guardd',
                        'production_stage_called': True, 'synthetic_ship_gates': False,
                        'scope': 'Selected real-input staging; overlay generated addition on full official archive, not an independent full release build'}
    phase('after', 0)
    sibling.unlink()
    os.symlink(package / 'libexec/btx-guardd.real', sibling)
    assert sibling.is_symlink()
    state['symlink_control'] = {'alias': str(sibling), 'target': os.readlink(sibling)}
    phase('symlink-refused', 1)
    sibling.unlink()
    os.link(generated, sibling)
    final = {str(f.relative_to(package)): sha(f) for f in package.rglob('*') if f.is_file()}
    assert final == candidate
    assert state['case_sha256'] == sha(HERE / 'case.py')
    assert sha(SOURCE / production) == identity['files'][production]
    assert sha(SOURCE / test) == identity['files'][test]
    state['final_package_files'] = final
    state['qualified'] = True
except Exception as error:
    state['error'] = repr(error)
    state['traceback'] = traceback.format_exc()
    raise
finally:
    save()
assert state['qualified']
