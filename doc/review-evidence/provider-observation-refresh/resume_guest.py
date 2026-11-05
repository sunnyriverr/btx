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
summary['retained_baseline_binary']=x['modeld_sha256'];summary['input_hashes']={f:sha(R/f) for f in ['helper.cpp','probe.cpp','component.cpp','integration.cpp']};save()
assert summary['runs']['baseline_regression_exit']==201
compile_file(helper,R/'helper.cpp',R/'helper.o','compile-candidate-helper')
linked(R/'component.o',R/'component','link-candidate-regression',candidate=True,boost=True)
env=dict(os.environ,BTX_PROVIDER_TEST_ROOT=str(R/'candidate-data'))
rc=run([str(R/'component'),'--log_level=test_suite','--report_level=detailed'],'candidate-regression',env=env);assert rc==0,rc;summary['runs']['candidate_regression_exit']=rc;save();(R/'component').unlink();shutil.rmtree(R/'candidate-data')
# Reuse the original reproduction unchanged, two fresh catalogs/processes.
compile_file(main,R/'probe.cpp',R/'probe.o','compile-original-probe')
linked(R/'probe.o',R/'probe','link-candidate-original-probe',candidate=True)
header=json.dumps({'weight':{'dtype':'F32','shape':[256],'data_offsets':[0,1024]}},separators=(',',':')).encode();header+=b' '*(-len(header)%8);(R/'model.safetensors').write_bytes(struct.pack('<Q',len(header))+header+b'\x01'*1024)
for initial in [True,False]:
 label='complete_to_partial' if initial else 'partial_to_complete';root=R/label;root.mkdir()
 rc=run([str(R/'probe'),str(root),str(R/'model.safetensors'),'1' if initial else '0'],label,45);assert rc==0,rc
 out=json.loads((R/(label+'.log')).read_text());assert out['accepted_new_record'] and out['rollback_refused'] and out['display_matches_latest'];summary['runs'][label]=out;save();shutil.rmtree(root)
(R/'probe').unlink();(R/'probe.o').unlink()
# Additional413 integration checks only, kept separate from standalone test.
compile_file(main,R/'integration.cpp',R/'integration.o','compile413-integration')
linked(R/'integration.o',R/'integration','link413-integration',candidate=True,boost=True)
env=dict(os.environ,BTX_PROVIDER_TEST_ROOT=str(R/'413-data'))
rc=run([str(R/'integration'),'--log_level=test_suite','--report_level=detailed'],'candidate413-integration',env=env);assert rc==0,rc;summary['runs']['candidate413_integration_exit']=rc;save();(R/'integration').unlink();shutil.rmtree(R/'413-data')
summary['retained_libraries_after']={k:sha(k) for k in x['libraries']};assert summary['retained_libraries_after']==x['libraries'];summary['retained_binary_after']=sha(B/'bin/btx-modeld');assert summary['retained_binary_after']==x['modeld_sha256'];summary['complete']=True;save();print('COMPLETE',flush=True)
