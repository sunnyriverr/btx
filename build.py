"""Qualify separate patches with one read-only release checkpoint restore."""
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import tarfile
import traceback

from checkpoint import restore_timestamps, sha, verify_restored
from native_fixture import exercise

WORK = Path(os.environ['GITHUB_WORKSPACE']).resolve()
OUT = WORK / 'repair-records'
BIN = WORK / 'repair-binaries'
SOURCE = WORK / 'product'
CACHE = WORK / 'gui-pilot-runtime/qtbuild'
BASE = 'dac9aee53520bd49ed320ec7a49b9072fc7d88d9'
ARCHIVE = '90391b49487f57e3c820200f28142e6873b0fecbb2a2d4b82091e48050437176'
ENTRY = 'src/modelnet/CMakeFiles/btx-modeld.dir/__/modeld.cpp.o'
SCOPES = json.loads((WORK / 'scope.json').read_text())


def run(args, log, cwd=WORK, timeout=120):
    print(log.relative_to(OUT), flush=True)
    with log.open('wb') as stream:
        process = subprocess.run(list(map(str, args)), cwd=cwd, stdout=stream,
                                 stderr=subprocess.STDOUT, timeout=timeout)
    if process.returncode:
        print(log.read_text(errors='replace')[-6000:], flush=True)
        raise RuntimeError(f'{log.name} exited {process.returncode}')
    return log.read_text(errors='replace')


def restore():
    assert shutil.disk_usage(WORK).free > 10 * 1024**3
    checkpoint = WORK / 'saved-checkpoint'
    manifest = json.loads((checkpoint / 'manifest.json').read_text())
    archive = checkpoint / 'build-state.tar.gz'
    assert sha(archive) == manifest['archive_sha256'] == ARCHIVE
    assert manifest['identity']['source'] == BASE and Path(manifest['workspace']) == WORK
    assert not SOURCE.exists() and not CACHE.parent.exists()
    with tarfile.open(archive) as files:
        files.extractall(WORK, filter='data')
    restore_timestamps(WORK, manifest)
    verify_restored(WORK, manifest)


def compile_object(commands, source_path, output, log):
    suffix = '-c ' + str(SOURCE / source_path)
    rows = [shlex.split(row) for row in commands if row.rstrip().endswith(suffix)]
    assert len(rows) == 1, (source_path, len(rows))
    args = rows[0]
    assert args[0] == '/usr/bin/g++' and args.count('-O2') == 1
    args[args.index('-O2')] = '-O0'
    args[args.index('-o')+1] = str(output)
    args[args.index('-MF')+1] = str(output) + '.d'
    run(args, log, CACHE, timeout=600)


def qualify(number, row, pair, helper_commands, wallet_commands, gate):
    target = OUT / number
    target.mkdir()
    accepted = WORK / ('author-' + number)
    patch = WORK / (number + '.patch')
    assert sha(patch) == row['patch']
    assert run(['git','rev-parse','HEAD'], target/'head.log', accepted).strip() == row['head']
    assert not run(['git','status','--porcelain'], target/'clean.log', accepted).strip()
    pair.update(head=row['head'], patch_sha256=row['patch'],
                author_tree=run(['git','rev-parse','HEAD^{tree}'],target/'author-tree.log',accepted).strip())
    changed = set(run(['git','diff','--name-only',BASE,row['head']],
                      target/'author-delta.log',accepted).splitlines())
    assert all(name in row['changed'] or name.startswith(('src/test/', 'test/functional/')) for name in changed), changed
    run(['git','apply','--check','--whitespace=error',patch],target/'patch-check.log',accepted)
    originals = {name: (SOURCE/name).read_bytes() for name in row['changed']}
    try:
        for variant in ('baseline','candidate'):
            if variant == 'candidate':
                run(['git','apply','--whitespace=error',patch],target/'patch.log',accepted)
                run(['git','add','--',*row['changed']],target/'stage.log',accepted)
                pair['candidate_tree'] = run(['git','write-tree'],target/'candidate-tree.log',accepted).strip()
            for name in row['changed']:
                if variant == 'candidate':
                    assert sha(accepted/name) == row['changed'][name], name
                shutil.copyfile(accepted/name,SOURCE/name)
            items = {}
            for name in row['changed']:
                if name.endswith('.cpp'):
                    obj = BIN / (number+'-'+variant+'-'+Path(name).name+'.o')
                    compile_object(wallet_commands if number == '502' else helper_commands, name, obj,
                                   target / (variant+'-'+Path(name).name+'.log'))
                    items[name] = obj
            if number == '502':
                out = run([sys.executable,WORK/'rescan.py',accepted,variant],
                          target/(variant+'-rescan.log'),timeout=30)
                pair[variant] = {'compiled': list(items), 'rescan_status': out.splitlines()}
            else:
                binary = BIN / (number+'-'+variant)
                raw_link = shlex.split(helper_commands[-1])
                assert raw_link[:2] == [':','&&'] and raw_link[-2:] == ['&&',':']
                link = [arg for arg in raw_link[2:-2] if arg != '-Wl,--unresolved-symbols=ignore-in-shared-libs']
                i = link.index(ENTRY)
                link[i:i] = [str(obj) for obj in items.values()]
                link[link.index('-o')+1] = str(binary)
                missing = [arg for arg in link if arg.endswith(('.a','.o','.so')) and not (CACHE/arg).is_file()]
                assert not missing, missing
                run(link,target/(variant+'-link.log'),CACHE)
                assert 'not found' not in run(['ldd',binary],target/(variant+'-ldd.log'))
                pair[variant] = {'binary_sha256':sha(binary)}
                pair[variant]['result'] = exercise(number,binary,target/variant,variant == 'candidate',gate)
            for obj in items.values():
                obj.unlink()
    finally:
        for name,data in originals.items():
            (SOURCE/name).write_bytes(data)
    pair['pass'] = True


OUT.mkdir()
BIN.mkdir()
receipt = {'base':BASE,'checkpoint_sha256':ARCHIVE,'repairs':{}}
try:
    restore()
    receipt['restore_verified'] = True
    assert run(['g++','-dumpfullversion'],OUT/'compiler.log').strip() == '11.4.0'
    helper_commands = run(['ninja','-C',CACHE,'-t','commands','btx-modeld'],
                          OUT/'helper-commands.log').splitlines()
    wallet_commands = run(['ninja','-C',CACHE,'-t','commands','bitcoin_wallet'],
                           OUT/'wallet-commands.log').splitlines()
    if not (CACHE/ENTRY).exists():
        run(['ninja','-C',CACHE,'-j1',ENTRY],OUT/'shared-entry.log')
    gate = BIN/'identity-gate.so'
    run(['cc','-shared','-fPIC','-Wall','-Wextra','-Werror',WORK/'gate.c','-o',gate,'-ldl'],
        OUT/'gate-build.log')
    for number,row in SCOPES.items():
        pair = receipt['repairs'][number] = {'pass':False}
        try:
            qualify(number,row,pair,helper_commands,wallet_commands,gate)
        except Exception:
            pair['error'] = traceback.format_exc()
            print(pair['error'],flush=True)
finally:
    (OUT/'result.json').write_text(json.dumps(receipt,indent=2)+'\n')
    # The command graphs are lengthy and only the bounded build logs are needed.
    for log in (OUT/'helper-commands.log',OUT/'wallet-commands.log'):
        log.unlink(missing_ok=True)
sys.exit(0 if all(x['pass'] for x in receipt['repairs'].values()) else 1)
