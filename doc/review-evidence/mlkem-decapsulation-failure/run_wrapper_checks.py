import subprocess,json,hashlib,resource,os,shlex
from pathlib import Path
r=Path(__file__).resolve().parent;source=r/'source';out=r/'baseline-inputs';(out/'crypto').mkdir(parents=True,exist_ok=True)
base='ecd9310a8b35dbf1260d1a64e0ff39bb50e7a629'
for p in ['src/crypto/ml_kem.h','src/crypto/ml_kem.cpp']:
 (out/'crypto'/Path(p).name).write_bytes(subprocess.check_output(['git','-C',str(source),'show',base+':'+p]))
common=['/usr/bin/c++','-std=c++20','-O2','-I'+str(r/'build/src'),'-I'+str(source/'src')]
commands=[]
def build(a,label):
 commands.append({'label':label,'argv':a})
 with (r/(label+'.log')).open('w') as f:subprocess.run(a,stdout=f,stderr=subprocess.STDOUT,check=True)
row=next(x for x in json.loads((r/'build/compile_commands.json').read_text()) if x['file']==str(source/'src/crypto/ml_kem.cpp'))
a=shlex.split(row['command']);a.insert(1,'-I'+str(out));a[a.index('-o')+1]=str(r/'wrapper-baseline.o');a[a.index('-c')+1]=str(out/'crypto/ml_kem.cpp')
build(a,'compile-baseline-wrapper')
libs=[str(r/'build/lib'/('lib'+n+'.a')) for n in ['bitcoin_crypto','bitcoin_util','bitcoin_clientversion']]
build(common[:3]+['-I'+str(out)]+common[3:]+[str(r/'wrapper_checks.cpp'),str(r/'wrapper-baseline.o')]+libs+['-framework','CoreFoundation','-framework','Security','-o',str(r/'wrapper-baseline')],'link-baseline-wrapper')
build(common+[str(r/'wrapper_checks.cpp')]+libs+['-framework','CoreFoundation','-framework','Security','-o',str(r/'wrapper-candidate')],'link-candidate-wrapper')
results=[]
def limit_core():resource.setrlimit(resource.RLIMIT_CORE,(0,0))
for variant in ['baseline','candidate']:
 for mode in ['valid','wrong','altered','empty','short','long']:
  a=[str(r/('wrapper-'+variant)),mode];q=subprocess.run(a,cwd=r,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,timeout=15,preexec_fn=limit_core)
  log=r/(variant+'-'+mode+'.log');log.write_text(q.stdout+q.stderr)
  expected= q.returncode==0 if variant=='candidate' or mode in ['valid','wrong','altered'] else q.returncode==1
  results.append(dict(variant=variant,case=mode,returncode=q.returncode,expected=expected,log=log.name))
(r/'wrapper-results.json').write_text(json.dumps(dict(base=base,scope='Actual wrapper and primitive; baseline wrapper/header plus common freshly-built current libraries; same native local component harness. No caller integration runtime.',commands=commands,results=results,sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in [r/'wrapper_checks.cpp',r/'wrapper-baseline',r/'wrapper-candidate',r/'wrapper-baseline.o']}),indent=2)+'\n')
print(json.dumps(results,indent=2));assert all(x['expected'] for x in results)
