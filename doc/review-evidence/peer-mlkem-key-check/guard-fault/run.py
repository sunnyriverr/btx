from pathlib import Path
import subprocess,json,shlex,shutil,hashlib,time
f=Path(__file__).resolve().parent;r=f.parent
assert shutil.disk_usage(r).free>int(1.25*1024**3)
rows=json.loads((r/'build/compile_commands.json').read_text());commands=[]
def run(a,cwd=None,label='command'):
 commands.append({'label':label,'argv':a,'cwd':str(cwd or f)})
 with (f/(label+'.log')).open('w') as out:subprocess.run(a,cwd=cwd or f,stdout=out,stderr=subprocess.STDOUT,check=True,timeout=180)
x=next(x for x in rows if x['file']==str(r/'source/src/crypto/ml_kem.cpp'));a=shlex.split(x['command']);a[1:1]=['-DIsValidEncapsulationKey=UnitRealKeyCheck','-DEncaps=UnitRealEncaps'];a[a.index('-o')+1]=str(f/'real/ml_kem.cpp.o');run(a,x['directory'],'instrument-wrapper')
lib=f/'libunit_crypto.a';shutil.copy2(r/'build/lib/libbitcoin_crypto.a',lib);run(['/usr/bin/ar','d',str(lib),'ml_kem.cpp.o'],label='remove-wrapper');run(['/usr/bin/ar','rcs',str(lib),str(f/'real/ml_kem.cpp.o')],label='insert-instrumented-wrapper')
x=next(x for x in rows if x['file']==str(r/'source/src/net.cpp'));a=shlex.split(x['command']);a[a.index('-c')+1]=str(f/'unit.cpp');a[a.index('-o')+1]=str(f/'unit.o');run(a,x['directory'],'compile-unit')
original=json.loads((r/'positive-link-command.json').read_text());results=[]
for variant in ['baseline','candidate']:
 a=original.copy();a[a.index(str(r/'runtime/positive-transport.o'))]=str(f/'unit.o');a[a.index(str(r/'build/lib/libbitcoin_crypto.a'))]=str(lib)
 if variant=='baseline':
  x=next(x for x in rows if x['file']==str(r/'source/src/net.cpp'));v=shlex.split(x['command']);a[a.index(str(Path(x['directory'])/v[v.index('-o')+1]))]=str(r/'baseline-net.o')
 binary=f/('unit-'+variant);a[a.index('-o')+1]=str(binary);run(a,label='link-'+variant)
 t=time.monotonic();q=subprocess.run([str(binary)],cwd=f,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,timeout=30);(f/('run-'+variant+'.log')).write_text(q.stdout+q.stderr)
 results.append({'variant':variant,'returncode':q.returncode,'seconds':time.monotonic()-t,'stdout':q.stdout,'stderr':q.stderr,'binary_sha256':hashlib.sha256(binary.read_bytes()).hexdigest()})
z={'scope':'Unit-only forced predicate result on valid production-generated keys and unmodified in-memory handshake bytes; no malformed-peer input or sockets. Actual baseline/candidate net objects unchanged. Test-only crypto wrapper symbols renamed; real algorithms delegated unchanged.','commands':commands,'results':results,'unit_sha256':hashlib.sha256((f/'unit.cpp').read_bytes()).hexdigest()};(f/'results.json').write_text(json.dumps(z,indent=2)+'\n');print(json.dumps(results,indent=2));assert results[0]['returncode']==1 and 'unit_guard_failures=2' in results[0]['stdout'];assert results[1]['returncode']==0 and 'unit_guard_failures=0' in results[1]['stdout']
