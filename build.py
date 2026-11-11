"""Relink just the changed helper object against the verified Linux checkpoint."""
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import tarfile
import time

from checkpoint import restore_timestamps, sha, verify_restored

WORK = Path(os.environ['GITHUB_WORKSPACE'])
OUT = WORK / 'repair-records'
BIN = WORK / 'repair-binaries'
BASE = 'dac9aee53520bd49ed320ec7a49b9072fc7d88d9'
ARCHIVE = 'c4b58e4ef14e93f8b257c18bc855a7d9e4079a4659c9e3266fd25acad50d66df'
TREE = 'ed72649dc18f4eaf55c9a6d1a2b171e587b482dd'
SOURCE_SHA = '37367435ef429d0fede4b9b867849616c290ee7228a7c8de4f29499651a0b433'
MATCHED_SHA = '46cad5ba2317b73b9cd9008292fbc22a7b3a249f21628e131a1fe705a61294b3'
STOCK_SHA = '0412b4d3d09ecd40e954f031ba4d2487e089a078084669af9ec598b041ba1a6c'
SOURCE = 'src/modelnet/helper.cpp'
receipt = {'commands': [], 'pass': False}


def run(args, label, cwd=WORK, timeout=90):
    print('START', label, flush=True)
    begin = time.monotonic()
    log = OUT / (label + '.log')
    with log.open('wb') as output:
        code = subprocess.run(list(map(str, args)), cwd=cwd, stdout=output,
                              stderr=subprocess.STDOUT, timeout=timeout).returncode
    receipt['commands'].append({'label': label, 'exit': code, 'seconds': time.monotonic() - begin})
    print('END', label, code, flush=True)
    if code:
        print(log.read_text(errors='replace')[-5000:], flush=True)
        raise RuntimeError(label)
    return log.read_text(errors='replace')


def build_and_qualify():
    assert shutil.disk_usage(WORK).free > 8 * (1 << 30)
    checkpoint = WORK / 'checkpoint-input'
    manifest = json.loads((checkpoint / 'manifest.json').read_text())
    archive = checkpoint / 'build-state.tar.gz'
    assert sha(archive) == manifest['archive_sha256'] == ARCHIVE
    assert manifest['identity']['base'] == BASE
    assert manifest['identity']['integration_tree'] == TREE
    assert Path(manifest['workspace']) == WORK
    with tarfile.open(archive) as contents:
        contents.extractall(WORK, filter='data')
    restore_timestamps(WORK, manifest)
    verify_restored(WORK, manifest)
    receipt.update(base=BASE, checkpoint_tree=TREE, checkpoint_sha256=ARCHIVE, restore_verified=True)
    source = WORK / 'product'
    cache = WORK / 'gui-pilot-runtime/qtbuild'
    assert run(['g++', '-dumpfullversion'], 'compiler').strip() == '11.4.0'
    commands = run(['ninja', '-C', cache, '-t', 'commands', 'btx-modeld'], 'cached-commands').splitlines()
    assert sha(source / SOURCE) == SOURCE_SHA
    for name in ('pr517.patch', 'pr519.patch'):
        run(['git', 'apply', '--check', WORK / name], name + '-check', source)
        run(['git', 'apply', WORK / name], name + '-apply', source)
    paths = (SOURCE, 'src/modelnet/catalog.cpp', 'src/modelnet/catalog.h')
    receipt['combined_source'] = {name: sha(source / name) for name in paths}

    def compile_file(name, obj):
        rows = [shlex.split(line) for line in commands if line.rstrip().endswith('-c ' + str(source / name))]
        assert len(rows) == 1 and rows[0][0] == '/usr/bin/g++'
        args = rows[0]
        # Match both variants. Reduce optimization only for these two objects
        # to keep the two full helper compiles bounded on the CI runner.
        assert args.count('-O2') == 1
        args[args.index('-O2')] = '-O0'
        args[args.index('-o') + 1] = str(obj)
        args[args.index('-MF') + 1] = str(obj) + '.d'
        return args

    catalog_obj = BIN / 'catalog.o'
    helper_obj = BIN / 'helper.o'
    catalog_compile = compile_file('src/modelnet/catalog.cpp', catalog_obj)
    helper_compile = compile_file(SOURCE, helper_obj)
    link = shlex.split(commands[-1])[2:-2]
    assert link[0] == '/usr/bin/g++'
    link = [arg for arg in link if arg != '-Wl,--unresolved-symbols=ignore-in-shared-libs']
    pos = link.index('src/modelnet/CMakeFiles/btx-modeld.dir/__/modeld.cpp.o')
    link[pos:pos] = [str(catalog_obj), str(helper_obj)]
    (OUT / 'admitted-plan.json').write_text(json.dumps([catalog_compile, helper_compile, link], indent=2)+'\n')
    run(catalog_compile, 'catalog-compile', cache, timeout=240)

    for label, acceptable in (('combined-baseline', ('REDOWNLOADED_PIECES', 'QUOTA_REJECTED')),
                              ('candidate', ('REUSED_PIECES',))):
        if label == 'candidate':
            patch = WORK / 'product.patch'
            run(['git', 'apply', '--check', patch], 'product-patch-check', source)
            run(['git', 'apply', patch], 'product-patch', source)
            receipt['candidate_source'] = {name: sha(source / name) for name in paths}
        binary = BIN / label
        link[link.index('-o') + 1] = str(binary)
        run(helper_compile, label + '-compile', cache, timeout=720)
        run(link, label + '-link', cache, timeout=120)
        binary_sha = sha(binary)
        assert 'not found' not in run(['ldd', binary], label + '-ldd')
        output = OUT / label
        run(['python3', '-u', WORK / 'native_fixture.py', '--binary', binary,
             '--expected-sha256', binary_sha, '--output', output], label + '-native', timeout=360)
        observed = json.loads((output / 'observations.json').read_text())
        receipt[label] = {'sha256': binary_sha, 'result': observed['result']}
        if label == 'combined-baseline' and observed['result'] == 'REUSED_PIECES':
            receipt.update(verdict='BASELINE_ALREADY_PASSES', **{'pass': True})
            return
        assert observed['result'] in acceptable, (label, observed['result'])
    receipt.update(verdict='FAIL_BEFORE_PASS_AFTER', **{'pass': True})

def main():
    OUT.mkdir()
    BIN.mkdir()
    try:
        build_and_qualify()
    except Exception as exc:
        receipt['error'] = repr(exc)
        print(repr(exc), flush=True)
    finally:
        for generated in (*BIN.glob('*.o'), *BIN.glob('*.d')):
            generated.unlink()
        for name in ('product.patch', 'native_fixture.py', 'relay.py', 'helpers.py'):
            shutil.copy2(WORK / name, OUT / name)
        (OUT / 'result.json').write_text(json.dumps(receipt, indent=2)+'\n')
    return 0 if receipt['pass'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
