from pathlib import Path
import subprocess,time,json,shutil,os,signal
r=Path('/BTX_REVIEW_ROOT/pr340-fold-rerun');cmd=['/opt/homebrew/bin/cmake','--build',str(r/'build'),'--target','btxd','btx-cli','-j','2'];(r/'build-command.json').write_text(json.dumps(cmd)+'\n')
start=time.monotonic();reason=None
with (r/'build.log').open('wb') as f:
 p=subprocess.Popen(cmd,stdout=f,stderr=subprocess.STDOUT,start_new_session=True)
 while p.poll() is None:
  if shutil.disk_usage(r).free < 1536*1024**2:reason='disk_headroom_below_1.5GiB'
  if time.monotonic()-start > 1200:reason='build_exceeded_20_minutes'
  if reason:os.killpg(p.pid,signal.SIGTERM);break
  time.sleep(1)
 try:ret=p.wait(timeout=10)
 except subprocess.TimeoutExpired:os.killpg(p.pid,signal.SIGKILL);ret=p.wait()
(r/'build-result.json').write_text(json.dumps({'exit_code':ret,'elapsed_s':time.monotonic()-start,'stop_reason':reason,'free_bytes':shutil.disk_usage(r).free},indent=2)+'\n');print((r/'build-result.json').read_text());print((r/'build.log').read_text()[-5000:])
