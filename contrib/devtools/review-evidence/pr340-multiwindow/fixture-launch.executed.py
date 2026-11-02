from pathlib import Path
import subprocess,os,time,signal,json,shutil
r=Path(__file__).resolve().parent.parent;o=Path(__file__).resolve().parent
args=['python3',str(o/'make_fixture.py'),'--configfile='+str(r/'pr340-fold-rerun/build/test/config.ini'),'--tmpdir='+str(o/'fixture-run'),'--portseed=501','--nocleanup']
env=os.environ.copy();env.update(BTXD=str(r/'pr340-churn-fix/native/candidate-btxd'),BTXCLI=str(r/'pr340-churn-fix/native/candidate-btx-cli'),BTX_MATMUL_BACKEND='metal',BTX_MATMUL_V4_BACKEND='metal',BTX_MATMUL_REQUIRE_BACKEND='metal')
start=time.monotonic();stop=None
with (o/'fixture.log').open('w') as f:
 p=subprocess.Popen(args,env=env,stdout=f,stderr=f,start_new_session=True)
 while p.poll() is None:
  if time.monotonic()-start>900:stop='900second_deadline'
  if shutil.disk_usage(o).free<1.5*1024**3:stop='disk_floor'
  if stop:os.killpg(p.pid,signal.SIGTERM);break
  time.sleep(1)
 try:rc=p.wait(timeout=15)
 except subprocess.TimeoutExpired:os.killpg(p.pid,signal.SIGKILL);rc=p.wait()
(o/'fixture-launch.json').write_text(json.dumps({'returncode':rc,'elapsed_s':time.monotonic()-start,'stop':stop},indent=2));print((o/'fixture.log').read_text()[-2500:]);assert rc==0
