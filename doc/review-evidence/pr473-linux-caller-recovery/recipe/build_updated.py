"""Restore the owned immutable checkpoint and compile the updated helper only."""
from pathlib import Path
import json
import os
import re
import shutil
import subprocess
import tarfile
from checkpoint import create, restore_timestamps, sha, verify_restored

BASE = 'dac9aee53520bd49ed320ec7a49b9072fc7d88d9'
HEAD = '07c588fe22545dff59a4744701ae9e01c7854cf9'
OLD_ARCHIVE = 'c4b58e4ef14e93f8b257c18bc855a7d9e4079a4659c9e3266fd25acad50d66df'
w = Path(os.environ['GITHUB_WORKSPACE']).resolve()
out = w / 'updated-build-records'
out.mkdir()
state = {'source': HEAD, 'base': BASE, 'compiled': False, 'complete': False}

def run(args, name, cwd=None, timeout=120):
    with (out / (name + '.log')).open('wb') as log:
        subprocess.run(list(map(str, args)), cwd=cwd, stdout=log,
                       stderr=subprocess.STDOUT, timeout=timeout, check=True)
    return (out / (name + '.log')).read_text()

try:
    archive = w / 'saved-checkpoint/build-state.tar.gz'
    manifest = json.loads((w / 'saved-checkpoint/manifest.json').read_text())
    prior = json.loads((w / 'prior-build/result.json').read_text())
    assert prior['pass'] and prior['integration_tree'] == 'ed72649dc18f4eaf55c9a6d1a2b171e587b482dd'
    assert sha(archive) == manifest['archive_sha256'] == prior['new_state_sha256'] == OLD_ARCHIVE
    assert Path(manifest['workspace']) == w
    assert shutil.disk_usage(w).free > 10 * 1024**3
    assert not (w / 'product').exists()
    with tarfile.open(archive) as tar:
        tar.extractall(w, filter='data')
    restore_timestamps(w, manifest)
    verify_restored(w, manifest)
    state['restore_verified'] = True
    src = w / 'product'
    accepted = w / 'accepted-source'
    build = w / 'gui-pilot-runtime/qtbuild'
    assert sha(build / 'bin/btx-modeld') == prior['binaries']['candidate']
    assert run(['git', 'rev-parse', 'HEAD'], 'accepted-head', accepted).strip() == HEAD
    tracked = run(['git', 'ls-files'], 'accepted-files', accepted).splitlines()
    changed = []
    for name in tracked:
        if (accepted / name).is_file():
            assert (src / name).is_file(), name
            if sha(src / name) != sha(accepted / name):
                changed.append(name)
    assert sorted(changed) == ['src/modelnet/helper.cpp', 'src/test/modelnet_release_store_tests.cpp'], changed
    state['source_delta'] = changed
    for name in changed:
        shutil.copyfile(accepted / name, src / name)
    assert all(sha(src / name) == sha(accepted / name) for name in tracked if (accepted / name).is_file())
    shutil.copytree(accepted / '.git', src / '.git')
    assert not run(['git', 'status', '--porcelain', '--untracked-files=no'], 'source-clean', src).strip()
    state['source_tree'] = run(['git', 'rev-parse', 'HEAD^{tree}'], 'source-tree', src).strip()
    assert run(['g++', '-dumpfullversion'], 'compiler').strip() == '11.4.0'
    assert 'OpenSSL 3.5.9' in run([w / 'gui-pilot-runtime/openssl/bin/openssl', 'version'], 'openssl')
    run(['cmake', '-S', src, '-B', build], 'configure')
    cache = (build / 'CMakeCache.txt').read_text()
    assert 'WITH_MODELNET:BOOL=ON' in cache
    assert str(w / 'gui-pilot-runtime/openssl/lib/libcrypto.a') in cache
    run(['cmake', '-P', build / 'CMakeFiles/VerifyGlobs.cmake'], 'globs', build)
    observed = out / 'observed.ninja'
    shutil.copy2(build / 'build.ninja', observed)
    plan = run(['ninja', '-C', build, '-f', observed, '-n', 'btx-modeld'], 'plan')
    steps = [re.sub(r'^\[\d+/\d+\] ', '', line) for line in plan.splitlines() if line.startswith('[')]
    allowed = {
        'Generating bitcoin-build-info.h',
        'Building CXX object src/CMakeFiles/bitcoin_clientversion.dir/clientversion.cpp.o',
        'Building CXX object src/CMakeFiles/bitcoin_common.dir/matmul/matmul_v4_rc_production_canary.cpp.o',
        'Building CXX object src/CMakeFiles/bitcoin_common.dir/matmul/matmul_v4_rc_production_golden_manifest.cpp.o',
        'Building CXX object src/modelnet/CMakeFiles/bitcoin_modelnet.dir/helper.cpp.o',
        'Building CXX object src/modelnet/CMakeFiles/btx-modeld.dir/__/modeld.cpp.o',
        'Linking CXX static library lib/libbitcoin_clientversion.a',
        'Linking CXX static library lib/libbitcoin_common.a',
        'Linking CXX static library lib/libbitcoin_modelnet.a',
        'Linking CXX executable bin/btx-modeld',
    }
    assert steps and set(steps) <= allowed and len(steps) <= 12, steps
    assert any('helper.cpp.o' in step for step in steps)
    state['steps'] = steps
    state['compile_started'] = True
    run(['cmake', '--build', build, '--target', 'btx-modeld', '--parallel', '1'], 'compile', timeout=900)
    assert not run(['git', 'status', '--porcelain', '--untracked-files=no'], 'final-source-clean', src).strip()
    binaries = w / 'updated-helper-binaries'
    binaries.mkdir()
    shutil.copy2(build / 'bin/btx-modeld', binaries / 'candidate')
    state['binaries'] = {'candidate': sha(binaries / 'candidate')}
    assert state['binaries']['candidate'] != prior['binaries']['candidate']
    assert 'not found' not in run(['ldd', binaries / 'candidate'], 'ldd')
    assert sha(archive) == OLD_ARCHIVE
    state.update(compiled=True, complete=True, archive_unchanged=True)
except Exception as exc:
    state['error'] = repr(exc)
    raise
finally:
    if state.get('compile_started'):
        try:
            checkpoint = create(w, w / 'updated-build-state', {'source': HEAD, 'binaries': state.get('binaries', {})})
            state['checkpoint_sha256'] = checkpoint['archive_sha256']
        except Exception as exc:
            state['checkpoint_error'] = repr(exc)
    (out / 'result.json').write_text(json.dumps(state, indent=2) + '\n')
