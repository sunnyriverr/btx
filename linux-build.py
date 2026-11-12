from pathlib import Path
import os
import shutil
import subprocess
import sys
import tempfile

root = Path('/dev/shm/btx-pr577')
work = root / 'shared-repair'
os.chdir(work)
os.environ['TMPDIR'] = str(root)
old = root / 'hydration-resume/source/src'
config = root / 'hydration-resume/config'
sources = [
    'random.cpp', 'randomenv.cpp', 'logging.cpp', 'sync.cpp',
    'crypto/sha256.cpp', 'crypto/chacha20.cpp', 'crypto/siphash.cpp',
    'support/cleanse.cpp', 'support/lockedpool.cpp',
    'util/time.cpp', 'util/syserror.cpp', 'util/threadnames.cpp',
]
common = ['-std=c++20', '-O1', '-pthread', '-ffunction-sections', '-fdata-sections',
          f'-I{config}', '-Isource/src', f'-I{old}', f'-I{old}/univalue/include']
shared = [old / f'{f}.cpp' for f in ('crypto/sha384', 'crypto/sha512', 'crypto/hex_base',
          'util/fs', 'util/fs_helpers', 'util/check', 'modelnet/store', 'modelnet/qualification',
          'modelnet/types', 'modelnet/crypto', 'util/strencodings')]
shared += [work / 'source/src' / f for f in sources]
shared += sorted((old / 'univalue/lib').glob('univalue*.cpp'))
shared += [work/'hydration.cpp', work/'bundle.cpp']
objects = work/'objects'
objects.mkdir(exist_ok=True)

def compile_unit(path, label):
    target = objects / f'{label}.o'
    if target.is_file() and target.stat().st_mtime_ns >= path.stat().st_mtime_ns:
        return target
    subprocess.run(['g++', *common, '-c', path, '-o', target], check=True)
    return target

compiled = {p.stem: compile_unit(p, p.stem) for p in shared}
with tempfile.TemporaryDirectory(dir='/tmp', prefix='btx-pr577-bin-') as dest:
    executable = Path(dest)
    for variant, units in (
        ('baseline', (old/'modelnet/file_stream.cpp', root/'lab-bundle/source/src/modelnet/realm_channel.cpp', old/'util/readwritefile.cpp')),
        ('candidate', tuple(work/'source/src'/f for f in ('modelnet/file_stream.cpp','modelnet/realm_channel.cpp','util/readwritefile.cpp'))),
    ):
        changed = [compile_unit(p, f'{variant}-{p.stem}') for p in units]
        for case in ('hydration','bundle'):
            inputs = [obj for name,obj in compiled.items() if name not in ('hydration','bundle') or name == case]
            subprocess.run(['g++','-pthread','-Wl,--gc-sections',*inputs,*changed,'-o',executable/f'{case}-{variant}'], check=True)
    shutil.copy2(work/'run.py', executable)
    subprocess.run([sys.executable, executable/'run.py'], check=True)
