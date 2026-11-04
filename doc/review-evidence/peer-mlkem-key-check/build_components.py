import json,subprocess,shlex,time,shutil
from pathlib import Path
r=Path(__file__).resolve().parent;rows=json.loads((r/'build/compile_commands.json').read_text());results=[]
paths=['src/net.cpp','src/test/net_tests.cpp','src/test/ml_kem_tests.cpp','src/common/args.cpp','src/common/settings.cpp','src/chainparams.cpp','src/chainparamsbase.cpp','src/kernel/chainparams.cpp','src/key.cpp','src/pubkey.cpp','src/protocol.cpp','src/uint256.cpp','src/primitives/block.cpp','src/primitives/transaction.cpp','src/hash.cpp','src/script/script.cpp']
for p in paths:
 assert shutil.disk_usage(r).free>int(1.25*1024**3)
 x=next(x for x in rows if x['file']==str(r/'source'/p));a=shlex.split(x['command']);start=time.monotonic();log=r/('object-'+p.replace('/','_')+'.log')
 with log.open('w') as f:q=subprocess.run(a,cwd=x['directory'],stdout=f,stderr=subprocess.STDOUT,timeout=240)
 obj=Path(x['directory'])/a[a.index('-o')+1];results.append(dict(path=p,command=a,returncode=q.returncode,seconds=time.monotonic()-start,object=str(obj),log=log.name));(r/'component-builds.json').write_text(json.dumps(results,indent=2)+'\n');print(p,q.returncode,flush=True)
 if q.returncode:break
assert len(results)==len(paths) and all(x['returncode']==0 for x in results)
