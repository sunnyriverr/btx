"""Build the exact release helper and its export-preservation candidate."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import traceback

import prepare
from native_fixture import exercise

WORK = Path(os.environ['GITHUB_WORKSPACE']).resolve()
SOURCE = WORK / 'product'
BUILD = WORK / 'gui-pilot-runtime/qtbuild'
OUT = WORK / 'export-records'
PATCH = WORK / '494.patch'
BASE, TREE, CANDIDATE = (WORK / 'identities.txt').read_text().splitlines()
FILES = ['src/modelnet/helper.cpp', 'src/modelnet/helper_network02.cpp',
         'src/util/readwritefile.cpp', 'src/util/readwritefile.h']
receipt = {'base': BASE, 'candidate': CANDIDATE, 'candidate_tree': TREE,
           'checkpoint_sha256': prepare.TAR, 'variants': {}}


def sha(path):
    return hashlib.file_digest(path.open('rb'), 'sha256').hexdigest()


def run(args, label, limit=120):
    print(label, flush=True)
    log = OUT / f'{label}.log'
    with log.open('wb') as output:
        proc = subprocess.run(args, cwd=SOURCE, stdout=output,
                              stderr=subprocess.STDOUT, timeout=limit)
    if proc.returncode:
        print(log.read_text(errors='replace')[-5000:], flush=True)
        proc.check_returncode()
    return log.read_text(errors='replace').strip()


OUT.mkdir()
try:
    assert BASE == prepare.NEW
    assert sha(PATCH) == 'e375a7f70693ac025e82005ff57956ead0ec89ff6c676344be141c3082d21b01'
    receipt['patch_sha256'] = sha(PATCH)
    assert prepare.main() == 0, 'Checkpoint preparation failed'
    assert run(['git', 'rev-parse', 'HEAD'], 'release-head') == BASE
    assert not run(['git', 'status', '--porcelain', '--untracked-files=no'], 'release-clean')
    run(['git', 'apply', '--check', '--whitespace=error', PATCH], 'patch-check')
    for label in ('baseline', 'candidate'):
        if label == 'candidate':
            run(['git', 'apply', '--index', '--whitespace=error', PATCH], 'patch-apply')
            assert run(['git', 'write-tree'], 'candidate-tree') == TREE
            assert run(['git', 'diff', '--cached', '--name-only'], 'candidate-delta').splitlines() == FILES
            assert not run(['git', 'diff', '--name-only'], 'candidate-unstaged')
        assert shutil.disk_usage(BUILD).free >= 2 * 1024**3
        run(['cmake', '--build', BUILD, '--parallel', '2', '--target', 'btx-modeld'],
            f'{label}-build', 2100)
        # Keep separate executable paths for process-identity verification and cleanup.
        binary = Path(os.environ['RUNNER_TEMP']) / f'btx-modeld-494-{label}'
        shutil.copy2(BUILD / 'bin/btx-modeld', binary)
        assert 'not found' not in run(['ldd', binary], f'{label}-ldd')
        row = receipt['variants'][label] = {
            'binary_sha256': sha(binary), 'source_sha256': {name: sha(SOURCE / name) for name in FILES},
        }
        row['result'] = exercise('494', binary, OUT / label, label == 'candidate', None)
        binary.unlink()
    assert receipt['variants']['baseline']['binary_sha256'] != receipt['variants']['candidate']['binary_sha256']
    receipt['pass'] = True
except Exception:
    receipt['error'] = traceback.format_exc()
    print(receipt['error'], flush=True)
    raise
finally:
    (OUT / 'result.json').write_text(json.dumps(receipt, indent=2) + '\n')
