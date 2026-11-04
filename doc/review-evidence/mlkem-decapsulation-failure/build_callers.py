import json,shlex,subprocess,time,shutil
from pathlib import Path
r=Path(__file__).resolve().parent
rows=json.loads((r/'build/compile_commands.json').read_text())
paths=['src/net.cpp','src/shielded/bundle.cpp','src/shielded/note_encryption.cpp','src/wallet/shielded_rpc.cpp','src/wallet/shielded_wallet.cpp','src/test/ml_kem_tests.cpp','src/bench/ml_kem_bench.cpp','src/test/note_encryption_tests.cpp','src/test/shielded_transaction_tests.cpp']
results=[]
for p in paths:
 assert shutil.disk_usage(r).free>int(1.25*1024**3)
 x=next(x for x in rows if x['file']==str(r/'source'/p));a=shlex.split(x['command']);t=time.monotonic();log=r/('object-'+p.replace('/','_')+'.log')
 with log.open('w') as f:q=subprocess.run(a,cwd=x['directory'],stdout=f,stderr=subprocess.STDOUT,timeout=300)
 obj=Path(x['directory'])/a[a.index('-o')+1]
 results.append(dict(path=p,command=a,returncode=q.returncode,seconds=time.monotonic()-t,log=log.name,object=str(obj),bytes=obj.stat().st_size if obj.exists() else None))
 (r/'caller-objects.json').write_text(json.dumps(results,indent=2)+'\n');print(p,q.returncode,flush=True)
 if q.returncode:break
assert len(results)==len(paths) and all(x['returncode']==0 for x in results)
