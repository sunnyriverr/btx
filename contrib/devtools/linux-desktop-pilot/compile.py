from pathlib import Path
import os,json,subprocess,time,signal,shutil,sys,hashlib,resource
from checkpoint import create,sha
from abi_inspect import inspect_binary

def retain(w,state,writer=create):
 binary=w/'gui-pilot-runtime/qtbuild/bin/btx-qt';out=w/'compiled-binary';out.mkdir(exist_ok=True)
 if binary.is_file():
  shutil.copy2(binary,out/'btx-qt');state['retained_binary_sha256']=sha(out/'btx-qt')
 try:
  m=writer(w,w/'successor-checkpoint',{'source':state.get('verified_source','unknown'),'fixture':os.environ.get('GITHUB_SHA'),'compile_pass':state.get('compile_pass',False)})
  state['checkpoint_sha256']=m['archive_sha256'];state['checkpoint_entries']=len(m['rows']);state['checkpoint_pass']=True
 except Exception as e:state['checkpoint_error']=repr(e)

def main():
 w=Path(os.environ['GITHUB_WORKSPACE']).resolve();out=w/'compile-records';out.mkdir();s={'source':'dac9aee53520bd49ed320ec7a49b9072fc7d88d9','compile_pass':False,'commands':[]}
 def save():(out/'result.json').write_text(json.dumps(s,indent=2)+'\n')
 def run(args,label,cwd=None,env=None,limit=120):
  start=time.monotonic();last=0;peak=0;stop=None
  with (out/(label+'.log')).open('wb') as f:
   proc=subprocess.Popen(list(map(str,args)),stdout=f,stderr=subprocess.STDOUT,start_new_session=True,cwd=cwd,env=env)
   while proc.poll() is None:
    elapsed=time.monotonic()-start
    if elapsed>limit:stop='timeout'
    if shutil.disk_usage(w).free<2*1024**3:stop='disk_reserve'
    if stop:
     os.killpg(proc.pid,signal.SIGTERM)
     try:proc.wait(10)
     except subprocess.TimeoutExpired:os.killpg(proc.pid,signal.SIGKILL);proc.wait()
     break
    if elapsed-last>=30:
     last=elapsed;f.flush();print(label,round(elapsed),'s',shutil.disk_usage(w).free//1024**2,'MiBfree', (out/(label+'.log')).read_text(errors='replace').splitlines()[-2:],flush=True)
    time.sleep(.5)
  s['commands'].append({'label':label,'exit':proc.returncode,'stop':stop,'seconds':time.monotonic()-start});save()
  assert proc.returncode==0 and not stop,label
  return (out/(label+'.log')).read_text(errors='replace')
 try:
  run([sys.executable,Path(__file__).with_name('pilot.py')],'prepare',limit=720)
  p=json.loads((w/'pilot-records/result.json').read_text());expected=json.loads(Path(__file__).with_name('expected-plan.json').read_text())
  assert p['verdict']=='PREPARATION_PASS' and p['source']==s['source'] and p['planned_step_lines']==['['+str(i+1)+'/'+str(len(expected['actions']))+'] '+a for i,a in enumerate(expected['actions'])],'Target build plan changed'
  s['verified_source']=p['source'];s['steps']=len(expected['actions']);s['cached_objects_before']=p['objects_before']
  build=w/'gui-pilot-runtime/qtbuild'
  run(['cmake','--build',build,'--target','btx-qt','--parallel','2'],'qt-compile',limit=1800)
  s['compile_pass']=True
  # Retain successful executable before dependency inspection can fail.
  (w/'compiled-binary').mkdir(exist_ok=True);shutil.copy2(build/'bin/btx-qt',w/'compiled-binary/btx-qt')
  inspect_binary(build/'bin/btx-qt',out,s,run)
  assert sha(w/'saved-checkpoint/build-state.tar.gz')=='f8d97a5e97a1610206c27171956fd5e6cec821b0918086d014f5b4a970833986';s['original_archive_preserved']=True
  s['source_clean']=not subprocess.check_output(['git','status','--porcelain','--untracked-files=no'],cwd=w/'product')
 except Exception as e:s['error']=repr(e)
 finally:
  retain(w,s);s['child_max_rss_kib']=resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss;save()
 return 0 if s.get('compile_pass') and s.get('abi_pass') and s.get('checkpoint_pass') and s.get('source_clean') and s.get('original_archive_preserved') and not s.get('error') else 1
if __name__=='__main__':sys.exit(main())
