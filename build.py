"""Relink only helper.cpp from the pinned #505 head on the verified release cache."""
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import tarfile

from checkpoint import restore_timestamps, sha, verify_restored
from native_fixture import exercise

WORK = Path(os.environ['GITHUB_WORKSPACE']).resolve()
OUT = WORK / 'repair-records'
BIN = WORK / 'repair-binaries'
BASE = 'dac9aee53520bd49ed320ec7a49b9072fc7d88d9'
AUTHOR = '149ebe08e9f724754ba68b69e6d7fa71148647f3'
ARCHIVE = '90391b49487f57e3c820200f28142e6873b0fecbb2a2d4b82091e48050437176'
SOURCE = 'src/modelnet/helper.cpp'
AUTHOR_BLOBS = {
    SOURCE: 'd84e996f915060df8af9634279e458fb7f3c7ac6',
    'src/test/CMakeLists.txt': '19a0b565fe83d0329bbf26b284a1ab7eab7774ed',
    'src/test/modelnet_identity_secret_tests.cpp': 'efd169b523abd6e6416d09ee1eac6b5be43e1697',
}
SOURCE_SHA = {
    'baseline': 'f7f66ff9205e50f89c4d135daced699b99ba354b6c31a117e79038229becf105',
    'candidate': '2be5ac8d8185c8a34d3b6cd55992be626aa125ffd263fe4421ebf9eea0fc5eca',
}
PATCH = '11fcce9e6fbb6723296919e97cedda469396abfd1be5b438461b07c40647a1dd'


def run(args, name, cwd=WORK, timeout=90):
    print(name, flush=True)
    log = OUT / (name + '.log')
    with log.open('wb') as stream:
        result = subprocess.run(list(map(str, args)), cwd=cwd, stdout=stream,
                                stderr=subprocess.STDOUT, timeout=timeout)
    if result.returncode:
        print(log.read_text(errors='replace')[-6000:], flush=True)
        raise RuntimeError(f'{name} exited {result.returncode}')
    return log.read_text(errors='replace')


def qualify(receipt):
    assert shutil.disk_usage(WORK).free > 10 * 1024**3
    saved = WORK / 'saved-checkpoint'
    manifest = json.loads((saved / 'manifest.json').read_text())
    archive = saved / 'build-state.tar.gz'
    assert sha(archive) == manifest['archive_sha256'] == ARCHIVE
    assert manifest['identity']['source'] == BASE and Path(manifest['workspace']) == WORK
    source = WORK / 'product'
    cache = WORK / 'gui-pilot-runtime/qtbuild'
    assert not source.exists() and not cache.parent.exists()
    with tarfile.open(archive) as contents:
        contents.extractall(WORK, filter='data')
    restore_timestamps(WORK, manifest)
    verify_restored(WORK, manifest)
    receipt.update(checkpoint_sha256=ARCHIVE, restore_verified=True)

    accepted = WORK / 'accepted-source'
    assert run(['git', 'rev-parse', 'HEAD'], 'author-head', accepted).strip() == AUTHOR
    receipt['author_tree'] = run(['git', 'rev-parse', 'HEAD^{tree}'], 'author-tree', accepted).strip()
    assert not run(['git', 'status', '--porcelain'], 'author-clean', accepted).strip()
    assert set(run(['git', 'diff', '--name-only', BASE, AUTHOR],
                   'author-delta', accepted).splitlines()) == set(AUTHOR_BLOBS)
    for name, blob in AUTHOR_BLOBS.items():
        assert run(['git', 'hash-object', name], name.replace('/', '_'), accepted).strip() == blob
    for name in AUTHOR_BLOBS:
        if name != SOURCE:
            assert name.startswith('src/test/'), name

    assert run(['g++', '-dumpfullversion'], 'compiler').strip() == '11.4.0'
    commands = run(['ninja', '-C', cache, '-t', 'commands', 'btx-modeld'],
                   'retained-commands').splitlines()
    compile_rows = [line for line in commands if line.rstrip().endswith('-c ' + str(source / SOURCE))]
    assert len(compile_rows) == 1
    compile_args = shlex.split(compile_rows[0])
    assert compile_args[0] == '/usr/bin/g++' and compile_args.count('-O2') == 1
    compile_args[compile_args.index('-O2')] = '-O0'
    obj = BIN / 'helper.o'
    compile_args[compile_args.index('-o')+1] = str(obj)
    compile_args[compile_args.index('-MF')+1] = str(obj) + '.d'
    link = shlex.split(commands[-1])
    assert link[:2] == [':', '&&'] and link[-2:] == ['&&', ':']
    link = [arg for arg in link[2:-2] if arg != '-Wl,--unresolved-symbols=ignore-in-shared-libs']
    assert link[0] == '/usr/bin/g++'
    link.insert(link.index('src/modelnet/CMakeFiles/btx-modeld.dir/__/modeld.cpp.o'), str(obj))
    (OUT / 'paired-plan.json').write_text(json.dumps([compile_args, link], indent=2)+'\n')
    patch = WORK / 'identity-repair.patch'
    assert sha(patch) == PATCH
    receipt['patch_sha256'] = PATCH
    run(['git', 'apply', '--check', '--whitespace=error', patch], 'patch-preflight', accepted)
    shutil.copyfile(accepted / SOURCE, source / SOURCE)
    receipt['fixture_sha256'] = sha(WORK / 'native_fixture.py')
    for variant in ('baseline', 'candidate'):
        if variant == 'candidate':
            run(['git', 'apply', '--whitespace=error', patch], 'patch-apply', accepted)
            run(['git', 'add', SOURCE], 'patch-stage', accepted)
            receipt['candidate_tree'] = run(['git', 'write-tree'], 'candidate-tree', accepted).strip()
            shutil.copyfile(accepted / SOURCE, source / SOURCE)
        assert sha(source / SOURCE) == SOURCE_SHA[variant]
        binary = BIN / variant
        link[link.index('-o') + 1] = str(binary)
        run(compile_args, variant + '-compile', cache, timeout=540)
        run(link, variant + '-link', cache, timeout=120)
        assert 'not found' not in run(['ldd', binary], variant + '-ldd')
        receipt[variant] = {'source_sha256': SOURCE_SHA[variant], 'binary_sha256': sha(binary)}
        print(variant + '-native', flush=True)
        receipt[variant]['observations'] = exercise(binary, OUT / variant, variant == 'candidate')
    assert receipt['baseline']['binary_sha256'] != receipt['candidate']['binary_sha256']
    receipt['pass'] = True


OUT.mkdir()
BIN.mkdir()
receipt = {'pass': False, 'base': BASE, 'author_head': AUTHOR}
try:
    qualify(receipt)
finally:
    (OUT / 'result.json').write_text(json.dumps(receipt, indent=2)+'\n')
