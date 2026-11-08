from pathlib import Path
import os,subprocess,signal,time,shutil,json,hashlib
from abi_inspect import inspect_binary
w=Path(os.environ['GITHUB_WORKSPACE']);src=w/'product';out=w/'gui-compile-results';out.mkdir();s={'source':'ff5f3f04ea11f044594987fc6be043ff68b136ad','fixture':os.environ['GITHUB_SHA'],'commands':[],'working_package_accessed':False,'shipped_openssl_modified':False}
def run(args,label,limit=120):
 start=time.monotonic()
 with (out/(label+'.log')).open('wb') as f:
  p=subprocess.Popen(list(map(str,args)),cwd=src/'gui/atlas',stdout=f,stderr=subprocess.STDOUT,start_new_session=True,env=dict(os.environ,CARGO_BUILD_JOBS='2'))
  stop=None
  while p.poll() is None:
   if time.monotonic()-start>limit:stop='timeout'
   if shutil.disk_usage(w).free<2*1024**3:stop='disk reserve'
   if stop:
    os.killpg(p.pid,signal.SIGTERM)
    try:p.wait(timeout=10)
    except subprocess.TimeoutExpired:os.killpg(p.pid,signal.SIGKILL);p.wait(timeout=5)
    break
   time.sleep(1)
 s['commands'].append({'label':label,'args':list(map(str,args)),'exit':p.returncode,'seconds':time.monotonic()-start,'stop':stop})
 assert not stop and p.returncode==0,label
 return (out/(label+'.log')).read_text(errors='replace')
try:
 assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=src,text=True).strip()==s['source']
 assert shutil.disk_usage(w).free>8*1024**3
 run(['rustup','toolchain','install','1.95.0','--profile','minimal'],'rust-toolchain',limit=300)
 run(['cargo','+1.95.0','build','--locked','--release','-p','btx-atlas'],'atlas-compile',limit=1800)
 s['atlas_compiled']=True
 binary=src/'gui/atlas/target/release/btx-atlas';assert binary.exists()
 inspect_binary(binary,out,s,run)
 outputs=w/'gui-component-output';outputs.mkdir();shutil.copyfile(binary,outputs/'btx-atlas');s['component_sha256']=hashlib.sha256(binary.read_bytes()).hexdigest()
except Exception as e:s['error']=repr(e)
finally:
 s['source_clean']=not bool(subprocess.check_output(['git','status','--porcelain','--untracked-files=no'],cwd=src))
 (out/'result.json').write_text(json.dumps(s,indent=2)+'\n')
raise SystemExit(0 if s.get('atlas_compiled') and s.get('abi_pass') and s['source_clean'] and not s.get('error') else 1)
