from pathlib import Path
import os,subprocess,time,shutil,json,signal,datetime
r=Path(__file__).resolve().parent;rust=Path('<user-home>/.rustup/toolchains/1.95.0-aarch64-apple-darwin/bin')
env=os.environ.copy();env['PATH']=str(rust)+':'+env['PATH'];env['CARGO_HOME']=str(r.parent.parent/'btx-atlas-test2/cargo-home');env['CARGO_TARGET_DIR']=str(r/'target');env['CARGO_INCREMENTAL']='0';env['TAURI_CONFIG']=json.dumps({'identifier':'dev.btx.atlas.downloadstest'})
cmd=[str(rust/'cargo'),'build','--offline','--locked','--release','-p','btx-atlas','-j','1']
start=time.time();samples=[];reason=None
with (r/'build.log').open('w') as log:
 p=subprocess.Popen(cmd,cwd=r/'source/gui/atlas',env=env,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
 while p.poll() is None:
  free=shutil.disk_usage(r).free;samples.append({'t':time.time(),'free':free})
  if free<1.25*1024**3:reason='disk reserve reached';os.killpg(p.pid,signal.SIGTERM);break
  time.sleep(2)
 rc=p.wait()
(r/'build-result.json').write_text(json.dumps({'command':cmd,'exit':rc,'reason':reason,'elapsed':time.time()-start,'samples':samples},indent=2))
print(json.dumps({'exit':rc,'reason':reason,'elapsed':time.time()-start}))
