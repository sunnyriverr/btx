#!/usr/bin/env python3
"""Assemble exact recorded sources; optionally build and run the fixed profile."""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import shutil
import subprocess
import sys

PACKAGE = Path(__file__).resolve().parent

def sha(data):
    return hashlib.sha256(data).hexdigest()

def apply_patch(root, patch):
    """Apply only these exact unified text patches: no offsets, fuzz or Git writes."""
    lines = patch.read_text().splitlines(keepends=True)
    i = 0
    while i < len(lines):
        if not lines[i].startswith('--- a/'):
            raise ValueError('unexpected patch header: ' + lines[i])
        old = lines[i][6:].rstrip('\n'); i += 1
        if not lines[i].startswith('+++ b/'):
            raise ValueError('missing new-file header')
        new = lines[i][6:].rstrip('\n'); i += 1
        if old != new or PurePosixPath(new).is_absolute() or '..' in PurePosixPath(new).parts:
            raise ValueError('unsupported patch path')
        target = root / new
        source = target.read_text().splitlines(keepends=True)
        result = []; cursor = 0
        while i < len(lines) and not lines[i].startswith('--- a/'):
            match = re.fullmatch(r'@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@[^\n]*\n?', lines[i])
            if not match:
                raise ValueError('unsupported hunk: ' + lines[i])
            start, count, new_start, new_count = [int(v) if v is not None else 1 for v in match.groups()]
            position = start - 1 if count else start
            if position < cursor:
                raise ValueError('overlapping hunks')
            result.extend(source[cursor:position]); cursor = position; i += 1
            consumed = emitted = 0
            while i < len(lines) and not lines[i].startswith(('@@ ', '--- a/')):
                line = lines[i]; i += 1
                if line[:1] not in (' ', '-', '+'):
                    raise ValueError('unsupported patch body')
                text = line[1:]
                if line[0] in (' ', '-'):
                    if cursor >= len(source) or source[cursor] != text:
                        raise ValueError('context mismatch in ' + new)
                    cursor += 1; consumed += 1
                if line[0] in (' ', '+'):
                    result.append(text); emitted += 1
            if consumed != count or emitted != new_count:
                raise ValueError('hunk length mismatch')
        result.extend(source[cursor:]); target.write_text(''.join(result))

def assemble(source, work):
    manifest = json.loads((PACKAGE / 'manifest.json').read_text())
    if sha((PACKAGE / 'patches/candidate.patch').read_bytes()) != manifest['timing_product_patch_sha256']:
        raise ValueError('candidate patch identity mismatch')
    for name, expected in manifest['base_inputs_sha256'].items():
        if sha((source / name).read_bytes()) != expected:
            raise ValueError('base source differs from exact fd3a input: ' + name)
    if work.exists() and any(work.iterdir()):
        raise ValueError('work directory must be new or empty')
    work.mkdir(parents=True, exist_ok=True, mode=0o700); work.chmod(0o700)
    for name in manifest['product_paths']:
        target = work / 'product' / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((source / name).read_bytes())
    apply_patch(work / 'product', PACKAGE / 'patches/candidate.patch')
    common = work / 'test-source/common'
    shutil.copytree(work / 'product/src', common / 'src')
    for name in ('diagnostic.h', 'diagnostic.cpp'):
        shutil.copy2(PACKAGE / 'harness' / name, common / 'src/modelnet/security_v2' / name)
    apply_patch(common, PACKAGE / 'patches/common-diagnostic.patch')
    for variant in ('baseline', 'candidate'):
        target = work / 'test-source' / variant; target.mkdir()
        origin = source if variant == 'baseline' else work / 'product'
        for name in ('trust.cpp', 'evaluation.cpp', 'service.cpp'):
            shutil.copy2(origin / 'src/modelnet/security_v2' / name, target / name)
        apply_patch(target, PACKAGE / 'patches' / (variant + '-diagnostic.patch'))
    target = work / 'test-source/combined'; target.mkdir()
    shutil.copy2(work / 'product/src/modelnet/security_v2/service.cpp', target / 'service.cpp')
    apply_patch(target, PACKAGE / 'patches/381-service.patch')
    apply_patch(target, PACKAGE / 'patches/combined-diagnostic.patch')
    shutil.copytree(PACKAGE / 'harness', work / 'harness')
    checks = {}
    for name, expected in manifest['recorded_assembled_sources_sha256'].items():
        actual = sha((work / name).read_bytes())
        checks[name] = {'sha256': actual, 'matches_recorded': actual == expected}
    if not all(row['matches_recorded'] for row in checks.values()):
        raise ValueError('assembled sources differ from recorded tested inputs')
    shutil.copy2(PACKAGE / 'CMakeLists.txt', work / 'CMakeLists.txt')
    receipt = {'base_revision': manifest['base_revision'], 'validated_base_inputs': len(manifest['base_inputs_sha256']),
               'assembled_sources': checks, 'all_recorded_source_hashes_match': True,
               'scope': 'source equality; newly packaged CMake/driver not reexecuted by packaging task'}
    (work / 'source-assembly.json').write_text(json.dumps(receipt, indent=2) + '\n')
    return receipt

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True, help='clean exact fd3a checkout or source archive')
    parser.add_argument('--work', type=Path, required=True, help='new or empty private output directory')
    parser.add_argument('--assemble-only', action='store_true', help='validate/reconstruct only; no CMake, compiler or tests')
    args = parser.parse_args(); source = args.source.resolve(); work = args.work.resolve()
    if source == work or source in work.parents:
        parser.error("work directory must be outside the read-only source tree")
    receipt = assemble(source, work)
    print('Exact source assembly: %d inputs, %d reconstructed files match.' %
          (receipt['validated_base_inputs'], len(receipt['assembled_sources'])), flush=True)
    if args.assemble_only:
        return
    subprocess.run(['cmake', '-S', str(work), '-B', str(work / 'build'), '-DCMAKE_BUILD_TYPE=Release',
                    '-DCMAKE_EXPORT_COMPILE_COMMANDS=ON', '-DBTX_SOURCE_ROOT=' + str(source)], check=True)
    subprocess.run(['cmake', '--build', str(work / 'build'), '--parallel', '1'], check=True)
    subprocess.run([sys.executable, str(PACKAGE / 'run.py'), '--root', str(work)], check=True)

if __name__ == '__main__':
    main()
