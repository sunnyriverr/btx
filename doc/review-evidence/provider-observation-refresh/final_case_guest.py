from pathlib import Path
import subprocess,json,shlex,hashlib,time,shutil,os,signal,struct
R=Path('/tmp/btx-session2-provider-refresh-fix'); B=Path('/tmp/btx-session2-helper-restart-current/build'); x=json.loads((R/'guest-preflight.json').read_text()); profile=json.loads((R/'native-build-profile.json').read_text())
summary=json.loads((R/'result.json').read_text())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(): (R/'result.json').write_text(json.dumps(summary,indent=2)+'\n')
def run(args,label,timeout=180,env=None):
 print('START',label,flush=True);start=time.monotonic();stop=None
 with (R/(label+'.log')).open('wb') as f:
  p=subprocess.Popen(args,cwd=B,stdout=f,stderr=subprocess.STDOUT,start_new_session=True,env=env)
  while p.poll() is None:
   if time.monotonic()-start>timeout:stop='phase timeout'
   elif shutil.disk_usage('/tmp').free<32*1024**2:stop='guest below32MiB'
   if stop:
    os.killpg(p.pid,signal.SIGTERM);p.wait(timeout=15);break
   time.sleep(.25)
 item={'label':label,'command':args,'exit':p.returncode,'stop':stop,'seconds':round(time.monotonic()-start,2),'free':shutil.disk_usage('/tmp').free};summary['commands'].append(item);save();print('END',label,p.returncode,item['seconds'],flush=True)
 if stop:raise RuntimeError(stop)
 return p.returncode
link=x['link'][5:-5];target='src/modelnet/CMakeFiles/btx-modeld.dir/__/modeld.cpp.o'; assert link.count(target)==1
main=x['compile'];helper=profile['helper']
def compile_file(entry,source,obj,label):
 args=shlex.split(entry['command']);args=[str(source) if a==entry['file'] else a for a in args];args[args.index('-o')+1]=str(obj)
 assert run(args,label,timeout=300)==0,label

def linked(obj,exe,label,candidate=False,boost=False):
 cmd=link.replace(target,shlex.quote(str(obj))+(' '+shlex.quote(str(R/'helper.o')) if candidate else '')).replace(' -o bin/btx-modeld ',' -o '+shlex.quote(str(exe))+' ',1)
 if boost:cmd+=' -lboost_unit_test_framework'
 assert run(['/bin/sh','-c',cmd+' -s'],label)==0,label
# Retained baseline identities must still match prior reproduction exactly.
assert {k:sha(k) for k in x['libraries']}==x['libraries'];assert sha(B/'bin/btx-modeld')==x['modeld_sha256']
assert summary['retained_baseline_binary']==x['modeld_sha256']
assert summary['complete']
summary['initial_component_sha256']=summary['input_hashes']['component.cpp']
summary['final_component_sha256']=sha(R/'component.cpp');save()
compile_file(main,R/'component.cpp',R/'component.o','compile-final-regression')
for candidate in [False,True]:
 label='final-candidate' if candidate else 'final-baseline'
 linked(R/'component.o',R/'component',label+'-link',candidate=candidate,boost=True)
 root=R/(label+'-data');env=dict(os.environ,BTX_PROVIDER_TEST_ROOT=str(root))
 rc=run([str(R/'component'),'--log_level=test_suite','--report_level=detailed'],label,env=env)
 assert rc==(0 if candidate else 201),rc
 summary['runs'][label+'_exit']=rc;save();(R/'component').unlink();shutil.rmtree(root)
summary['retained_libraries_after']={k:sha(k) for k in x['libraries']};assert summary['retained_libraries_after']==x['libraries'];assert sha(B/'bin/btx-modeld')==x['modeld_sha256'];summary['final_case_qualified']=True;save();print('FINAL_COMPLETE',flush=True)
