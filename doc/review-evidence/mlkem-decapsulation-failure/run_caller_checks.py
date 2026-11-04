from pathlib import Path
import json,shlex,subprocess,hashlib,time
r=Path(__file__).resolve().parent;rows=json.loads((r/'build/compile_commands.json').read_text());cmds=[];baseline=[]
for p in ['src/shielded/bundle.cpp','src/shielded/note_encryption.cpp']:
 f=r/'baseline-inputs'/Path(p).name;f.write_bytes(subprocess.check_output(['git','-C',str(r/'source'),'show','ecd9310a:'+p]));x=next(x for x in rows if x['file']==str(r/'source'/p));a=shlex.split(x['command']);a.insert(1,'-I'+str(r/'baseline-inputs'));a[a.index('-o')+1]=str(f)+'.o';a[a.index('-c')+1]=str(f);cmds.append(a)
 with (r/('baseline-object-'+f.name+'.log')).open('w') as out:subprocess.run(a,cwd=x['directory'],stdout=out,stderr=subprocess.STDOUT,check=True,timeout=180)
 baseline.append(str(f)+'.o')
link=json.loads((r/'caller-link-command-current.json').read_text());results=[]
for variant in ['baseline','candidate']:
 a=link.copy()
 if variant=='baseline':
  for p,new in zip(['src/shielded/bundle.cpp','src/shielded/note_encryption.cpp'],baseline):
   x=next(x for x in rows if x['file']==str(r/'source'/p));b=shlex.split(x['command']);a[a.index(str(Path(x['directory'])/b[b.index('-o')+1]))]=new
  a.insert(a.index('-framework'),str(r/'wrapper-baseline.o'))
 binary=r/('caller-'+variant);a[a.index('-o')+1]=str(binary);cmds.append(a)
 with (r/('caller-link-'+variant+'-final.log')).open('w') as out:subprocess.run(a,stdout=out,stderr=subprocess.STDOUT,check=True,timeout=60)
 q=subprocess.run([str(binary)],cwd=r,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,timeout=30)
 (r/('caller-'+variant+'-final.log')).write_text(q.stdout+q.stderr)
 results.append(dict(variant=variant,returncode=q.returncode,stdout=q.stdout,binary_sha256=hashlib.sha256(binary.read_bytes()).hexdigest()))
z=dict(scope='Same native local caller harness, actual original/current note and view-grant consumers; no mocks or node/wallet data',commands=cmds,results=results,harness_sha256=hashlib.sha256((r/'caller_runtime.cpp').read_bytes()).hexdigest());(r/'caller-final-results.json').write_text(json.dumps(z,indent=2)+'\n');print(results);assert results[0]['returncode']==1 and '9 failures' in results[0]['stdout'];assert results[1]['returncode']==0 and '0 failures' in results[1]['stdout']
