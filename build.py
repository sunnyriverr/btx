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


def build():
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
    matches = [shlex.split(line) for line in commands if line.rstrip().endswith('-c ' + str(source / SOURCE))]
    assert len(matches) == 1
    compile_cmd = matches[0]
    assert compile_cmd[0] == '/usr/bin/g++'
    flags = iter(compile_cmd[1:])
    kept = []
    for flag in flags:
        if flag in ('-MT', '-MF', '-o', '-c'):
            next(flags)
        elif flag != '-MD':
            kept.append(flag)
    obj = BIN / 'helper.o'
    candidate = BIN / 'candidate'
    compile_cmd = [compile_cmd[0], *kept, '-o', str(obj), '-c', str(source / SOURCE)]
    link_cmd = shlex.split(commands[-1])[2:-2]
    assert link_cmd[0] == '/usr/bin/g++'
    link_cmd = [arg for arg in link_cmd if arg != '-Wl,--unresolved-symbols=ignore-in-shared-libs']
    pos = link_cmd.index('src/modelnet/CMakeFiles/btx-modeld.dir/__/modeld.cpp.o')
    link_cmd.insert(pos, str(obj))
    link_cmd[link_cmd.index('-o') + 1] = str(candidate)
    (OUT / 'admitted-plan.json').write_text(json.dumps([compile_cmd, link_cmd], indent=2)+'\n')
    assert sha(source / SOURCE) == SOURCE_SHA
    patch = WORK / 'product.patch'
    run(['git', 'apply', '--check', patch], 'patch-check', source)
    run(['git', 'apply', patch], 'patch', source)
    receipt.update(helper_source_before=SOURCE_SHA, helper_source_after=sha(source / SOURCE),
                   patch_sha256=sha(patch))
    run(compile_cmd, 'helper-compile', cache, timeout=1000)
    run(link_cmd, 'helper-link', cache, timeout=120)
    receipt['candidate_sha256'] = sha(candidate)
    return candidate


def qualify(candidate):
    for label, binary, expected_sha, expected_result in (
            ('matched-baseline', WORK / 'stock/candidate', MATCHED_SHA, 'STALLED'),
            ('candidate', candidate, receipt['candidate_sha256'], 'RECOVERED')):
        assert sha(binary) == expected_sha
        binary.chmod(0o755)
        assert 'not found' not in run(['ldd', binary], label + '-ldd')
        output = OUT / label
        command = ['python3', '-u', WORK / 'native_fixture.py',
                   '--binary', binary, '--expected-sha256', expected_sha, '--output', output]
        run(command, label + '-native', timeout=360)
        result = json.loads((output / 'observations.json').read_text())
        assert result['result'] == expected_result, (label, result['result'])
        receipt[label] = {'sha256': expected_sha, 'result': result['result']}
        output = OUT / (label + '-permanent')
        command[command.index('--output') + 1] = output
        run([*command, '--permanent-control'], label + '-permanent', timeout=130)
        control = json.loads((output / 'observations.json').read_text())
        assert control['result'] == 'PERMANENT_CONTROL_PASS'
        receipt[label]['permanent_control'] = control['result']
    assert sha(WORK / 'stock/base') == STOCK_SHA
    receipt['fixture_sha256'] = sha(WORK / 'native_fixture.py')
    receipt['verdict'] = 'FAIL_BEFORE_PASS_AFTER'
    receipt['pass'] = True


def main():
    OUT.mkdir()
    BIN.mkdir()
    try:
        qualify(build())
    except Exception as exc:
        receipt['error'] = repr(exc)
        print(repr(exc), flush=True)
    finally:
        if (BIN / 'helper.o').exists():
            (BIN / 'helper.o').unlink()
        for name in ('product.patch', 'native_fixture.py', 'relay.py', 'helpers.py'):
            shutil.copy2(WORK / name, OUT / name)
        (OUT / 'result.json').write_text(json.dumps(receipt, indent=2)+'\n')
    return 0 if receipt['pass'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
