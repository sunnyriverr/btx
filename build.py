"""Restore verified Linux build objects, rebuild the CLI and run the paired matrix."""
import json
import os
from pathlib import Path
import re
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
    def profile():
        cache_text = (cache / 'CMakeCache.txt').read_text().splitlines()
        prefixes = ('CMAKE_BUILD_TYPE:', 'CMAKE_CXX_COMPILER:', 'CMAKE_C_COMPILER:',
                    'CMAKE_CXX_FLAGS:', 'CMAKE_CXX_FLAGS_RELEASE:', 'OPENSSL_CRYPTO_LIBRARY:',
                    'OPENSSL_SSL_LIBRARY:')
        return {line.split('=', 1)[0]: line.split('=', 1)[1] for line in cache_text
                if not line.startswith(('//', '#')) and (':BOOL=' in line or line.startswith(prefixes))}

    before = profile()
    assert before['BUILD_CLI:BOOL'] == 'OFF'
    run(['cmake', '-S', source, '-B', cache, '-DBUILD_CLI=ON'], 'configure-cli', timeout=210)
    before['BUILD_CLI:BOOL'] = 'ON'
    after = profile()
    assert all(after.get(k) == v for k, v in before.items()), {
        k: (v, after.get(k)) for k, v in before.items() if after.get(k) != v
    }
    RESULT['cli_profile'] = after
    run(['cmake', '-P', cache / 'CMakeFiles/VerifyGlobs.cmake'], 'verify-globs', cache)
    ninja_file = OUT / 'configured.ninja'
    shutil.copy2(cache / 'build.ninja', ninja_file)
    ninja = ['ninja', '-C', cache, '-f', ninja_file]

    def build_cli(label, output, max_steps):
        plan = run([*ninja, '-n', 'btx-cli'], label + '-plan')
        actions = [m[1] for line in plan.splitlines() if (m := re.match(r'\[\d+/\d+\] (.*)', line))]
        assert 'Re-running CMake' not in plan and 'Re-checking globbed' not in plan
        assert 0 < len(actions) <= max_steps and any('bitcoin-cli.cpp.o' in x for x in actions), actions
        assert any('Linking CXX executable bin/btx-cli' in x for x in actions), actions
        if label == 'candidate':
            assert all('bitcoin-cli.cpp.o' in x or 'Linking CXX executable bin/btx-cli' in x for x in actions), actions
        RESULT[label + '_actions'] = actions
        run([*ninja, '-j2', 'btx-cli'], label + '-build', timeout=260)
        output.parent.mkdir(exist_ok=True)
        shutil.copy2(cache / 'bin/btx-cli', output)

    baseline = WORK / 'baseline-bin/btx-cli'
    build_cli('baseline', baseline, 25)
    assert sha(source / SOURCE) == SOURCE_SHA
    patch = WORK / 'product.patch'
    run(['git', 'apply', '--check', patch], 'patch-check', source)
    run(['git', 'apply', patch], 'patch', source)
    RESULT.update(source_before=SOURCE_SHA, source_after=sha(source / SOURCE), patch_sha256=sha(patch))
    build_cli('candidate', candidate, 2)
    assert sha(archive) == ARCHIVE
    return baseline


def qualify(baseline, candidate):
    stock = WORK / 'saved-bin'
    assert sha(stock / 'btx-cli') == STOCK_CLI and sha(stock / 'btxd') == STOCK_DAEMON
    for binary in (baseline, candidate):
        (binary.parent / 'btxd').symlink_to(stock / 'btxd')
    candidate_sha = sha(candidate)
    baseline_sha = sha(baseline)
    assert candidate_sha != baseline_sha
    RESULT.update(candidate_sha256=candidate_sha, baseline_sha256=baseline_sha, daemon_sha256=STOCK_DAEMON)
    required = ('backup_named_archive_stdin', 'backup_named_wallet_stdin', 'backup_named_both_stdin', 'restore_named_stdin')
    for name, directory, cli_sha, expected_rc in (
            ('baseline', baseline.parent, baseline_sha, 8), ('candidate', candidate.parent, candidate_sha, 0)):
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
        baseline = build(candidate)
        qualify(baseline, candidate)
    except Exception as exc:
        RESULT['error'] = repr(exc)
        print(repr(exc), flush=True)
    finally:
        (OUT / 'qualification.json').write_text(json.dumps(RESULT, indent=2)+'\n')
    return 0 if RESULT['pass'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
