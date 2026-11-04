#!/usr/bin/env python3
"""Build only the extracted fixture; preserve exact commands, output and tool ID."""
import argparse, hashlib, json, os, pathlib, shlex, subprocess, time
HERE = pathlib.Path(__file__).resolve().parent
REPAIR = HERE.parent
P = argparse.ArgumentParser()
P.add_argument('--variant', choices=['baseline','candidate'], required=True)
P.add_argument('--compiler', default='cl' if os.name == 'nt' else 'clang++')
P.add_argument('--output', type=pathlib.Path, required=True)
args = P.parse_args()
args.output = args.output.resolve(); args.output.mkdir(parents=True, exist_ok=True)
src = REPAIR/'source/src'
unit = HERE/f'{args.variant}-controls.cpp'
uv = [src/'univalue/lib'/name for name in ('univalue.cpp','univalue_get.cpp','univalue_read.cpp','univalue_write.cpp')]
binary = args.output / ('controls.exe' if os.name == 'nt' else 'controls')
if binary.exists(): binary.unlink()
inc = [HERE, src, src/'univalue/include']
if os.name == 'nt':
    cmd = [args.compiler, '/nologo', '/std:c++20', '/EHsc', '/DWIN32'] + [f'/I{p}' for p in inc]
    cmd += [str(unit)] + [str(p) for p in uv] + [f'/Fe{binary}', f'/Fo{args.output}'+os.sep]
    version_cmd = [args.compiler] if pathlib.Path(args.compiler).stem.lower() == 'cl' else [args.compiler,'--version']
else:
    cmd = [args.compiler, '-std=c++20', '-O0', '-g0'] + [f'-I{p}' for p in inc]
    deps = [src/p for p in ('util/subprocess.cpp','crypto/sha256.cpp','crypto/hex_base.cpp','support/cleanse.cpp')]
    cmd += [str(unit)] + [str(p) for p in uv+deps] + ['-o',str(binary)]
    version_cmd = [args.compiler,'--version']
t = time.monotonic()
version = subprocess.run(version_cmd, text=True, capture_output=True)
proc = subprocess.run(cmd, cwd=args.output, text=True, capture_output=True)
receipt = {'variant':args.variant,'platform':os.name,'command':cmd,'cwd':str(args.output),
           'compiler_identity':version.stdout+version.stderr,'returncode':proc.returncode,
           'seconds':round(time.monotonic()-t,3),'source_sha256':hashlib.sha256(unit.read_bytes()).hexdigest(),
           'binary':str(binary),'binary_sha256':hashlib.sha256(binary.read_bytes()).hexdigest() if binary.exists() else None}
(args.output/'build.json').write_text(json.dumps(receipt,indent=2)+'\n')
(args.output/'build.log').write_text(proc.stdout+proc.stderr)
print(json.dumps(receipt,indent=2))
raise SystemExit(proc.returncode)
