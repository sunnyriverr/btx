from pathlib import Path
import json,shlex,subprocess
r=Path(__file__).resolve().parent
rows=json.loads((r/'build/compile_commands.json').read_text())
def entry(p):return next(x for x in rows if x['file']==str(r/'source'/p))
def obj(p):
 x=entry(p);a=shlex.split(x['command']);return str(Path(x['directory'])/a[a.index('-o')+1])
for p in ['src/shielded/note.cpp','src/uint256.cpp','src/shielded/lattice/polyvec.cpp']:
 x=entry(p);subprocess.run(shlex.split(x['command']),cwd=x['directory'],check=True,timeout=180)
a=['/usr/bin/c++','-std=c++20','-O2','-Wl,-dead_strip','-I'+str(r/'source/src'),'-I'+str(r/'build/src'),str(r/'caller_runtime.cpp')]
a += [obj(p) for p in ['src/shielded/bundle.cpp','src/shielded/note_encryption.cpp','src/shielded/note.cpp']]
a += [str(r/'build/lib'/('lib'+n+'.a')) for n in ['bitcoin_crypto','bitcoin_util','bitcoin_clientversion']]
a += [obj(p) for p in ['src/uint256.cpp','src/shielded/lattice/polyvec.cpp']]
a += ['-framework','CoreFoundation','-framework','Security','-o',str(r/'caller-runtime')]
(r/'caller-link-command-current.json').write_text(json.dumps(a,indent=2)+'\n')
