from pathlib import Path
import subprocess,json,shutil,os,time,signal
r=Path(__file__).resolve().parent.parent;o=Path(__file__).resolve().parent;repo=r/'toolchain-2026-10-31/source';src=o/'source';build=o/'build';head='5deb327871efbca832e1a4e420f76dad74ff6b41'
assert shutil.disk_usage(o).free>3.5*1024**3
subprocess.run(['git','-C',str(repo),'worktree','add','--detach','--no-checkout',str(src),head],check=True,stdout=subprocess.DEVNULL)
for args in [('sparse-checkout','init','--cone'),('sparse-checkout','set','cmake','contrib','depends','doc','scripts/ci','share','src','test/functional'),('checkout',head)]:subprocess.run(['git','-C',str(src),*args],check=True,stdout=subprocess.DEVNULL)
args=json.loads((r/'pr340-fold-rerun/configure-command.json').read_text());args[args.index('-S')+1]=str(src);args[args.index('-B')+1]=str(build)
(o/'configure-command.json').write_text(json.dumps(args,indent=2))
with (o/'configure.log').open('w') as f:subprocess.run(args,stdout=f,stderr=f,check=True)
start=time.monotonic();stop=None
with (o/'build.log').open('w') as f:
 p=subprocess.Popen(['/opt/homebrew/bin/cmake','--build',str(build),'--target','btxd','btx-cli','-j','2'],stdout=f,stderr=f,start_new_session=True)
 while p.poll() is None:
  if shutil.disk_usage(o).free<1.5*1024**3:stop='disk_floor'
  if time.monotonic()-start>1800:stop='30min_build_deadline'
  if stop:os.killpg(p.pid,signal.SIGTERM);break
  time.sleep(1)
 try:rc=p.wait(timeout=10)
 except subprocess.TimeoutExpired:os.killpg(p.pid,signal.SIGKILL);rc=p.wait()
(o/'build-result.json').write_text(json.dumps({'returncode':rc,'seconds':time.monotonic()-start,'stop':stop,'head':head,'isolated_clean_build':True},indent=2));print((o/'build-result.json').read_text());assert rc==0
