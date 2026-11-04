from pathlib import Path
import json,shlex,subprocess
r=Path(__file__).resolve().parent;rows=json.loads((r/'build/compile_commands.json').read_text());results=json.loads((r/'component-builds.json').read_text())
x=next(x for x in rows if x['file']==str(r/'source/src/bip324.cpp'));a=shlex.split(x['command'])
with (r/'object-bip324.log').open('w') as f:subprocess.run(a,cwd=x['directory'],stdout=f,stderr=subprocess.STDOUT,check=True,timeout=180)
excluded={'src/chainparams.cpp','src/kernel/chainparams.cpp','src/primitives/block.cpp','src/primitives/transaction.cpp'}
objs=[z['object'] for z in results if not z['path'].startswith('src/test/') and z['path'] not in excluded];objs.append(str(Path(x['directory'])/a[a.index('-o')+1]))
x=next(x for x in rows if x['file']==str(r/'source/src/netaddress.cpp'));a=shlex.split(x['command'])
with (r/'object-netaddress.log').open('w') as f:subprocess.run(a,cwd=x['directory'],stdout=f,stderr=subprocess.STDOUT,check=True,timeout=180)
objs.append(str(Path(x['directory'])/a[a.index('-o')+1]))
x=next(x for x in rows if x['file']==str(r/'source/src/net.cpp'));a=shlex.split(x['command']);a[a.index('-o')+1]=str(r/'runtime/positive-transport.o');a[a.index('-c')+1]=str(r/'runtime/positive_transport.cpp')
with (r/'positive-compile.log').open('w') as f:subprocess.run(a,cwd=x['directory'],stdout=f,stderr=subprocess.STDOUT,check=True,timeout=180)
libs=[str(r/'build/lib'/('lib'+n+'.a')) for n in ['bitcoin_crypto','bitcoin_util','bitcoin_clientversion']]+[str(r/'build/src/secp256k1/lib/libsecp256k1.a'),str(r/'build/src/univalue/libunivalue.a')]
a=['/usr/bin/c++','-Wl,-dead_strip','-o',str(r/'runtime/positive-transport'),str(r/'runtime/positive-transport.o')]+objs+libs+['-framework','CoreFoundation','-framework','Security']
(r/'positive-link-command.json').write_text(json.dumps(a,indent=2)+'\n')
with (r/'positive-link.log').open('w') as f:q=subprocess.run(a,stdout=f,stderr=subprocess.STDOUT)
print('link',q.returncode)
