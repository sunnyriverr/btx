#!/usr/bin/env python3
"""PR393 native Windows component check. Prepared, not Windows-executed.

Run in an x64 VS developer shell with clang-cl, lld-link and llvm-lib.
No downloads or node access. Reuses exact published inputs and behavioral driver.
"""
import argparse
import ast
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys

BASE = 'cbf65894e6d61084527cd93e913a00c6794418dd'
CODE = 'd1ee21e828df480d6a3b9605a0d08a21fce8c6ef'
EVIDENCE = 'eca826d8040ff222feb5595c18c75193e336c7c4'
PREFIX = 'contrib/review-evidence/backend-stub-ownership/'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--repo', required=True, type=Path)
    p.add_argument('--out', required=True, type=Path, help='New directory only')
    a = p.parse_args()
    if sys.platform != 'win32' or platform.machine().lower() not in ('amd64', 'x86_64'):
        p.error('Native x64 Windows required; no macro-emulation fallback')
    if any(os.environ.get(k) for k in ('CL', '_CL_', 'LINK')):
        p.error('CL, _CL_ and LINK must be unset')
    names = ('git', 'clang-cl', 'lld-link', 'llvm-lib', 'llvm-readobj')
    tools = {k: shutil.which(k) for k in names}
    if not all(tools.values()):
        p.error('Missing tool: ' + ', '.join(k for k, v in tools.items() if not v))
    repo, out = a.repo.resolve(), a.out.resolve()
    if out.exists():
        p.error('--out must not exist')
    if not out.parent.is_dir() or shutil.disk_usage(out.parent).free < 1442177280:
        p.error('Existing parent and 1.25 GiB plus 100 MB free required')

    def blob(rev, name):
        return subprocess.check_output([tools['git'], '-C', str(repo), 'show', rev + ':' + name])

    ids = json.loads(blob(EVIDENCE, PREFIX + 'identities.json'))
    recipe = blob(EVIDENCE, PREFIX + 'run_checks.py')
    if ids['base'] != BASE or sha(recipe) != ids['harness_sha256']:
        raise RuntimeError('Published input identity mismatch')
    assignments = [n for n in ast.parse(recipe).body if isinstance(n, ast.Assign)
                   and any(isinstance(t, ast.Name) and t.id == 'DRIVER' for t in n.targets)]
    if len(assignments) != 1:
        raise RuntimeError('Expected one published DRIVER')
    driver = ast.literal_eval(assignments[0].value)
    out.mkdir()
    rows = []
    receipt = {'status': 'RUNNING', 'scope': 'native clang-cl/COFF component only',
               'platform': platform.platform(), 'base': BASE, 'code': CODE,
               'evidence': EVIDENCE, 'tools': tools,
               'tool_sha256': {k: sha(Path(v).read_bytes()) for k, v in tools.items()},
               'driver_sha256': sha(driver.encode()),
               'runner_sha256': sha(Path(__file__).read_bytes()), 'commands': rows,
               'sdk': {k: os.environ.get(k) for k in ('WindowsSDKVersion', 'VCToolsVersion')}}

    def save():
        (out / 'result.json').write_text(json.dumps(receipt, indent=2) + '\n', encoding='utf-8')

    def run(label, command, duplicates=False):
        if shutil.disk_usage(out).free < 1342177280:
            raise RuntimeError('Free disk below reserve')
        q = subprocess.run(list(map(str, command)), cwd=out, capture_output=True,
                           text=True, errors='replace', timeout=120)
        log = q.stdout + q.stderr
        (out / (label + '.log')).write_text(log, encoding='utf-8')
        rows.append({'label': label, 'command': list(map(str, command)), 'exit': q.returncode})
        save()
        if duplicates:
            definitions = [s for s in log.splitlines() if 'duplicate symbol:' in s]
            if q.returncode == 0 or len(definitions) != 9:
                raise RuntimeError(label + ': expected exactly nine duplicate symbols')
            for vendor in ('cuda', 'metal', 'hip'):
                for fn in ('ComputeDigestAccel', 'ComputeDigestsBatchedAccel', 'ComputeDigestsBMX4CAccel'):
                    if not any(vendor + '::' + fn + '(' in s for s in definitions):
                        raise RuntimeError(label + ': missing duplicate ' + vendor + '::' + fn)
        elif q.returncode:
            raise RuntimeError(label + ': failed; see log')
        return log

    try:
        # llvm-lib is lib.exe-compatible and need not implement --version.
        # Its exact binary hash is recorded above instead.
        for tool in ('clang-cl', 'lld-link', 'llvm-readobj'):
            run(tool + '-version', [tools[tool], '--version'])
        (out / 'driver.cpp').write_text(driver, encoding='utf-8')
        for variant, rev in [('source', BASE), ('candidate', CODE)]:
            root = out / variant
            for name, digest in ids[variant + '_tree_files'].items():
                data = blob(rev, name)
                if sha(data) != digest:
                    raise RuntimeError('Source mismatch: ' + variant + '/' + name)
                f = root / name
                f.parent.mkdir(parents=True, exist_ok=True)
                f.write_bytes(data)
            inc = root / 'src'
            units = ['matmul/accel_v4_stub.cpp'] + [v + '/matmul_v4' + s + '_stub.cpp'
                     for v in ('cuda', 'metal', 'hip') for s in ('_accel', '_bmx4_accel')]
            objects = []
            for i, name in enumerate(units + ['DRIVER']):
                obj = root / ('unit-' + str(i) + '.obj')
                src = out / 'driver.cpp' if name == 'DRIVER' else inc / name
                run(variant + '-compile-' + str(i), [tools['clang-cl'], '/nologo', '/std:c++20',
                    '/EHsc', '/MD', '/Od', '/I' + str(inc), '/c', src, '/Fo' + str(obj)])
                headers = run(variant + '-coff-' + str(i), [tools['llvm-readobj'], '--file-headers', obj])
                if 'COFF-x86-64' not in headers:
                    raise RuntimeError('Expected native x64 COFF object')
                objects.append(obj)
            library = root / 'backends.lib'
            run(variant + '-archive', [tools['llvm-lib'], '/nologo', '/out:' + str(library), *objects[:-1]])
            modes = ('direct', 'whole') if variant == 'source' else ('direct', 'whole', 'ordinary')
            for mode in modes:
                exe = root / (mode + '.exe')
                inputs = objects[:-1] if mode == 'direct' else [library]
                # Invoke the recorded linker directly. CRT libraries come from
                # clang-cl's native object directives and the developer shell LIB.
                cmd = [tools['lld-link'], '/nologo', '/SUBSYSTEM:CONSOLE', '/MACHINE:X64',
                       '/OUT:' + str(exe), '/INCREMENTAL:NO', objects[-1], *inputs]
                if mode == 'whole':
                    cmd.append('/WHOLEARCHIVE:' + str(library))
                label = variant + '-' + mode
                run(label + '-link', cmd, duplicates=variant == 'source')
                if variant == 'candidate':
                    result = run(label + '-run', [exe])
                    if 'PASS: all 12 dispatcher entry points' not in result:
                        raise RuntimeError(label + ': success marker absent')
                    receipt.setdefault('executables', {})[mode] = sha(exe.read_bytes())
        receipt['status'] = 'PASS'
        save()
        print('PASS: COFF component only; full node and enabled GPU builds unverified')
    except BaseException as e:
        receipt.update(status='FAILED_OR_BLOCKED', error=str(e))
        save()
        raise


if __name__ == '__main__':
    main()
