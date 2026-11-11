"""Restore verified Linux build objects, rebuild the CLI and run the paired matrix."""
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
OUT = WORK / 'records'
BASE = 'dac9aee53520bd49ed320ec7a49b9072fc7d88d9'
ARCHIVE = 'c4b58e4ef14e93f8b257c18bc855a7d9e4079a4659c9e3266fd25acad50d66df'
TREE = 'ed72649dc18f4eaf55c9a6d1a2b171e587b482dd'
STOCK_CLI = '921c54e5f0c92745b42bd63711bf404f9e50b7be3d39e2d82916d0439b9633c8'
STOCK_DAEMON = 'ffd6c2dc95df0111a8152b5d5f82244190cad2323981376ffed7c21a1cfd9fc6'
SOURCE = 'src/bitcoin-cli.cpp'
SOURCE_SHA = '543feda26418c893af7ad54dafa1462b50eaf02e9ae9c6ac3c83d7d6f6dc888e'
RESULT = {'commands': [], 'pass': False}


def run(argv, label, cwd=WORK, timeout=90):
    print('START', label, flush=True)
    begin = time.monotonic()
    log = OUT / (label + '.log')
    with log.open('wb') as f:
        p = subprocess.run(list(map(str, argv)), cwd=cwd, stdout=f, stderr=subprocess.STDOUT, timeout=timeout)
    RESULT['commands'].append({'label': label, 'exit': p.returncode, 'seconds': time.monotonic() - begin})
    data = log.read_text(errors='replace')
    if p.returncode:
        print(data[-4000:], flush=True)
        raise RuntimeError(label)
    print('END', label, flush=True)
    return data


def build(candidate):
    assert shutil.disk_usage(WORK).free > 8 * (1 << 30)
    checkpoint = WORK / 'checkpoint-input'
    manifest = json.loads((checkpoint / 'manifest.json').read_text())
    archive = checkpoint / 'build-state.tar.gz'
    assert sha(archive) == manifest['archive_sha256'] == ARCHIVE
    assert manifest['identity']['base'] == BASE and manifest['identity']['integration_tree'] == TREE
    assert Path(manifest['workspace']) == WORK
    with tarfile.open(archive) as f:
        f.extractall(WORK, filter='data')
    restore_timestamps(WORK, manifest)
    verify_restored(WORK, manifest)
    RESULT.update(base=BASE, checkpoint_tree=TREE, checkpoint_sha256=ARCHIVE, checkpoint_verified=True)
    source, cache = WORK / 'product', WORK / 'gui-pilot-runtime/qtbuild'
    assert sha(source / SOURCE) == SOURCE_SHA
    assert run(['g++', '-dumpfullversion'], 'compiler').strip() == '11.4.0'
    commands = run(['ninja', '-C', cache, '-t', 'commands', 'btx-cli'], 'cached-commands').splitlines()
    matches = [shlex.split(line) for line in commands if line.rstrip().endswith('-c ' + str(source / SOURCE))]
    assert len(matches) == 1
    cmd = matches[0]
    assert cmd[0] == '/usr/bin/g++'
    obj = WORK / 'candidate-cli.o'
    flags = iter(cmd[1:])
    kept = []
    for flag in flags:
        if flag in ('-MT', '-MF', '-o', '-c'):
            next(flags)
        elif flag != '-MD':
            kept.append(flag)
    compile_cmd = [cmd[0], *kept, '-o', str(obj), '-c', str(source / SOURCE)]
    link_cmd = shlex.split(commands[-1])[2:-2]
    assert link_cmd[0] == '/usr/bin/g++'
    link_cmd = [arg for arg in link_cmd if arg != '-Wl,--unresolved-symbols=ignore-in-shared-libs']
    original_objects = [i for i, arg in enumerate(link_cmd) if arg.endswith('/bitcoin-cli.cpp.o')]
    assert len(original_objects) == 1
    link_cmd[original_objects[0]] = str(obj)
    link_cmd[link_cmd.index('-o') + 1] = str(candidate)
    (OUT / 'admitted-plan.json').write_text(json.dumps([compile_cmd, link_cmd], indent=2)+'\n')
    patch = WORK / 'product.patch'
    run(['git', 'apply', '--check', patch], 'patch-check', source)
    run(['git', 'apply', patch], 'patch', source)
    RESULT.update(source_before=SOURCE_SHA, source_after=sha(source / SOURCE), patch_sha256=sha(patch))
    run(compile_cmd, 'cli-compile', cache, timeout=240)
    run(link_cmd, 'cli-link', cache, timeout=90)
    assert sha(archive) == ARCHIVE


def qualify(candidate):
    stock = WORK / 'saved-bin'
    assert sha(stock / 'btx-cli') == STOCK_CLI and sha(stock / 'btxd') == STOCK_DAEMON
    candidate.parent.mkdir(exist_ok=True)
    (candidate.parent / 'btxd').symlink_to(stock / 'btxd')
    candidate_sha = sha(candidate)
    RESULT['candidate_sha256'] = candidate_sha
    required = ('backup_named_archive_stdin', 'backup_named_wallet_stdin', 'backup_named_both_stdin', 'restore_named_stdin')
    for name, directory, cli_sha, expected_rc in (
            ('baseline', stock, STOCK_CLI, 8), ('candidate', candidate.parent, candidate_sha, 0)):
        for binary in ('btxd', 'btx-cli'):
            assert 'not found' not in run(['ldd', directory / binary], f'{name}-{binary}-loader')
        case_output = OUT / name
        run(['python3', '-u', WORK / 'native_fixture.py', '--binaries', directory,
             '--expected-cli', cli_sha, '--records', case_output], f'{name}-native', timeout=130)
        data = json.loads((case_output / 'result.json').read_text())
        assert data['status'] == 'observed_controls_passed' and data['runtime_removed'] and data['clean_shutdown']
        cases = data['cases']
        for case in required:
            row = cases[case]
            assert row['returncode'] == expected_rc, (name, case, row)
            if expected_rc:
                arg = 'wallet_name' if case.startswith('restore') else 'destination_archive'
                assert f'Parameter {arg} specified twice' in row['stderr']
            elif case.startswith('restore'):
                assert row['after_reload']['ownership_and_label_match']
            else:
                assert row['integrity_ok'] and cases['restore_' + case]['after_reload']['ownership_and_label_match']
        for case, arg in (('backup_duplicate_archive_passphrase', 'archive_passphrase'),
                          ('backup_duplicate_wallet_passphrase', 'wallet_passphrase')):
            assert not cases[case]['archive_created'] and cases[case]['returncode']
            if name == 'candidate':
                assert arg + ' was supplied both explicitly and through a stdin passphrase option' in cases[case]['stderr']
        if name == 'candidate':
            assert cases['backup_named_equals_stdin']['returncode'] == 0
            assert cases['restore_backup_named_equals_stdin']['after_reload']['ownership_and_label_match']
        RESULT[name] = {k: cases[k]['returncode'] for k in required}
    RESULT.update(fixture_sha256=sha(WORK / 'native_fixture.py'), verdict='FAIL_BEFORE_PASS_AFTER', **{'pass': True})


def main():
    OUT.mkdir(exist_ok=True)
    candidate = WORK / 'candidate-bin/btx-cli'
    candidate.parent.mkdir(exist_ok=True)
    try:
        build(candidate)
        qualify(candidate)
    except Exception as exc:
        RESULT['error'] = repr(exc)
        print(repr(exc), flush=True)
    finally:
        (OUT / 'qualification.json').write_text(json.dumps(RESULT, indent=2)+'\n')
    return 0 if RESULT['pass'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
