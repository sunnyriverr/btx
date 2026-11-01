#!/usr/bin/env python3
"""Identical Linux-native supervisor/IPC test; only driver binary differs."""
import os,sys,json,time,tempfile,subprocess,threading,queue,socket,errno,signal,hashlib
from pathlib import Path
HERE=Path(__file__).resolve().parent
results={'scope':'Full original supervisor TU + exact transport slices; synthetic helper; Linux aarch64 musl; NOT full daemon/GPU','cases':{},'long':{},'harness_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
(HERE/'results').mkdir(exist_ok=True)
HELPER=HERE/'fixture_helper.py';HELPER.chmod(0o700)
allprocs=[]
def until(fn,timeout=10):
 end=time.monotonic()+timeout
 while time.monotonic()<end:
  try:
   v=fn()
   if v:return v
  except (OSError,ValueError):pass
  time.sleep(.03)
 raise RuntimeError('precondition timeout')
class Driver:
 def __init__(self,binary,root,external):
  self.p=subprocess.Popen([str(binary),str(root),str(HELPER),'external' if external else 'owned'],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,bufsize=1);allprocs.append(self.p);self.q=queue.Queue();self.lines=[]
  def read():
   for l in self.p.stdout:self.lines.append(l.strip());self.q.put(l.strip())
  threading.Thread(target=read,daemon=True).start();self.wait('START',10)
 def send(self,s):self.p.stdin.write(s+'\n');self.p.stdin.flush()
 def wait(self,prefix,timeout):
  end=time.monotonic()+timeout
  while time.monotonic()<end:
   try:l=self.q.get(timeout=max(.01,end-time.monotonic()))
   except queue.Empty:break
   if l.startswith(prefix):return l
  return None
 def ready(self):
  def check():self.send('status');l=self.wait('STATUS',1);return l if l and ' READY ' in l else None
  return until(check,12)
def starthelper(root):
 p=subprocess.Popen([str(HELPER),'-modeldir='+str(root),'-modelrpcsocket='+str(root/'rpc.sock')],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL);allprocs.append(p);until(lambda:(root/'rpc.sock').exists());return p
def ping(root):
 with socket.socket(socket.AF_UNIX,socket.SOCK_STREAM) as s:
  s.settimeout(2);s.connect(str(root/'rpc.sock'));s.sendall(b'{"method":"fixture_ping","params":[]}\n');return json.loads(s.recv(8192))['result']
def snapshot(root,target):
 for f in root.glob('fixture-*'):
  if f.is_file(): (target/f.name).write_bytes(f.read_bytes())
def run(binary,label,case):
 root=Path(tempfile.mkdtemp(prefix='btcl-'));os.chmod(root,0o700)
 external=case.startswith('external');ext=starthelper(root) if external else None
 driver=Driver(binary,root,external);status=driver.ready();pid=int((root/'fixture-pid').read_text());fillers=[]
 if case=='stubborn_owned':(root/'fixture-ignore-term').touch()
 if case in ['partial_owned','silent_owned','external_partial']:
  (root/'fixture-fault').write_text('silent' if case=='silent_owned' else 'partial')
  until(lambda:(root/'fixture-stalled-getmodelnetworkinfo').exists(),8)
 if case=='external_backlog':
  (root/'fixture-pause-accept').touch()
  with socket.socket(socket.AF_UNIX,socket.SOCK_STREAM) as s:s.connect(str(root/'rpc.sock'))
  until(lambda:(root/'fixture-accept-paused').exists())
  for _ in range(64):
   s=socket.socket(socket.AF_UNIX,socket.SOCK_STREAM);s.setblocking(False);code=s.connect_ex(str(root/'rpc.sock'));fillers.append(s)
   if code in [errno.EAGAIN,errno.EWOULDBLOCK]:break
  assert code in [errno.EAGAIN,errno.EWOULDBLOCK]
  time.sleep(2.5)
 start=time.monotonic();driver.send('stop');limit=7 if case=='stubborn_owned' else 1.5
 stopped=driver.wait('STOPPED',limit);elapsed=time.monotonic()-start
 record={'pass':stopped is not None,'stop_observation_seconds':elapsed,'limit':limit,'initial_status':status,'helper_pid':pid}
 # A bounded baseline observation failure is released for clean teardown, never allowed to hang forever.
 (root/'fixture-release').touch();(root/'fixture-fault').unlink(missing_ok=True);(root/'fixture-pause-accept').unlink(missing_ok=True)
 for s in fillers:s.close()
 if not stopped:assert driver.wait('STOPPED',12),'cleanup did not recover after release'
 assert driver.p.wait(timeout=5)==0
 if external:
  assert ext.poll() is None;assert ping(root)['pid']==pid
  again=Driver(binary,root,True);record['restart_status']=again.ready();again.send('stop');assert again.wait('STOPPED',2);assert again.p.wait(timeout=5)==0
  assert ext.poll() is None and ping(root)['pid']==pid;record['external_same_pid_after_restart']=True;ext.terminate();ext.wait(timeout=5)
 else:
  try:os.kill(pid,0);alive=True
  except ProcessLookupError:alive=False
  assert not alive,'owned helper remains alive';record['owned_helper_gone']=True
 target=HERE/'results'/(label+'-'+case);target.mkdir();snapshot(root,target);record['driver_lines']=driver.lines
 results['cases'][label+'-'+case]=record
 print(label,case,json.dumps(record),flush=True);(HERE/'results/result.json').write_text(json.dumps(results,indent=2))
def long(binary,label):
 root=Path(tempfile.mkdtemp(prefix='btcl-long-'));os.chmod(root,0o700);(root/'fixture-long-delay').write_text('123')
 ext=starthelper(root);driver=Driver(binary,root,True);driver.ready();pid=ping(root)['pid']
 start=time.monotonic();p=subprocess.Popen([str(binary),'call',str(root/'rpc.sock'),'fixture-long'],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True);allprocs.append(p)
 until(lambda:(root/'fixture-long-started').exists());driver.send('stop');assert driver.wait('STOPPED',2);assert driver.p.wait(timeout=5)==0;assert ext.poll() is None
 output,error=p.communicate(timeout=140);elapsed=time.monotonic()-start;assert p.returncode==0,(output,error)
 reply=json.loads(output);assert reply['ok'] and reply['result']['fixture_long_reply'] and elapsed>=122
 refusal=subprocess.run([str(binary),'call',str(root/'rpc.sock'),'fixture-refusal'],capture_output=True,text=True,timeout=5);assert refusal.returncode==1 and 'INVALID_PARAMETER' in refusal.stdout
 assert ping(root)['pid']==pid
 results['long'][label]={'pass':True,'seconds':elapsed,'reply':reply,'external_helper_survives_supervisor_stop':True,'refusal':json.loads(refusal.stdout)};ext.terminate();ext.wait(timeout=5)
 target=HERE/'results'/(label+'-long');target.mkdir();snapshot(root,target);print(label,'long PASS',elapsed,flush=True)
try:
 for label in ['before','after']:
  binary=HERE/label/'test-driver'
  for case in ['healthy_owned','partial_owned','silent_owned','stubborn_owned','external_partial','external_backlog']:run(binary,label,case)
 errors=[]
 def worker(label):
  try:long(HERE/label/'test-driver',label)
  except Exception as e:errors.append(repr(e))
 threads=[threading.Thread(target=worker,args=(label,)) for label in ['before','after']]
 for t in threads:t.start()
 for t in threads:t.join()
 assert not errors,errors
 results['final']='PASS' if all(v['pass'] for k,v in results['cases'].items() if k.startswith('after-')) and sum(not v['pass'] for k,v in results['cases'].items() if k.startswith('before-'))==4 else 'FAIL'
 assert results['final']=='PASS',results
finally:
 for p in reversed(allprocs):
  if p.poll() is None:
   p.terminate()
   try:p.wait(timeout=6)
   except subprocess.TimeoutExpired:p.kill();p.wait()
 (HERE/'results/result.json').write_text(json.dumps(results,indent=2))
