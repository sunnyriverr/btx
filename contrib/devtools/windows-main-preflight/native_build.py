from pathlib import Path
import subprocess,time,json,os,hashlib
R=Path('D:/btx-native-035');B=R/'project-build';E=R/'preflight-evidence';r=json.loads((E/'result.json').read_text());assert r['planned_steps']==254 and not r['regeneration_in_plan'],r
assert r['status']=='CONFIGURED_DRY_RUN_COMPLETE'
targets=['btxd','btx-cli','btx-tx','btx-util','btx-open','btx-modeld','btx-guardd','btx-security']
st=time.monotonic();r['compile_invoked']=True;r['status']='BUILD_RUNNING';(E/'build-result.json').write_text(json.dumps(r,indent=2))
with (E/'build.log').open('w') as log:
 p=subprocess.Popen(['ninja','-C',str(B),'-j2']+targets,stdout=log,stderr=subprocess.STDOUT)
 try:
  while p.poll() is None:
   time.sleep(15);print('elapsed',round(time.monotonic()-st),'s',flush=True);print((E/'build.log').read_text(errors='replace')[-1800:],flush=True)
   if time.monotonic()-st>1800:
    subprocess.run(['taskkill','/PID',str(p.pid),'/T','/F']);p.wait();r['timeout']=True;break
 finally:
  if p.poll() is None:subprocess.run(['taskkill','/PID',str(p.pid),'/T','/F']);p.wait()
r['exit']=p.returncode;r['seconds']=round(time.monotonic()-st,2);r['status']='BUILD_PASS' if p.returncode==0 else 'BUILD_BLOCKED';r['binary_hashes']={t:hashlib.sha256((B/'bin'/(t+'.exe')).read_bytes()).hexdigest() for t in targets if (B/'bin'/(t+'.exe')).is_file()};(E/'build-result.json').write_text(json.dumps(r,indent=2));raise SystemExit(0 if r['status']=='BUILD_PASS' else 1)
