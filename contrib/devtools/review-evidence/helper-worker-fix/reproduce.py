#!/usr/bin/env python3
"""Real helper/loadmodel/restart; synthetic finite loader, loopback, no GPU/node/wallet."""
from pathlib import Path
import os,sys,json,socket,struct,subprocess,tempfile,time,hashlib,shutil,argparse,signal
p=argparse.ArgumentParser();p.add_argument('--out',required=True,type=Path);p.add_argument('--binary',required=True,type=Path);p.add_argument('--cases',default='resident-crash,idle-crash,unload-crash');a=p.parse_args()
r=Path(__file__).resolve().parent;b=a.binary.resolve();adapter=r.parent/'helper-worker-inheritance/adapter';a.out.mkdir(exist_ok=False)
assert b.is_file()
def wait(fn,seconds=15):
 end=time.monotonic()+seconds
 while time.monotonic()<end:
  try:
   v=fn()
   if v:return v
  except (OSError,ValueError,RuntimeError):pass
  time.sleep(.05)
 raise RuntimeError('bounded wait expired')
def rpc(path,method,params=[]):
 with socket.socket(socket.AF_UNIX,socket.SOCK_STREAM) as s:
  s.settimeout(4);s.connect(str(path));s.sendall(json.dumps({'jsonrpc':'1.0','id':1,'method':method,'params':params}).encode()+b'\n');s.shutdown(socket.SHUT_WR);data=b''
  while b'\n' not in data:
   z=s.recv(65536)
   if not z:break
   data+=z
  x=json.loads(data)
  if x.get('error'):raise RuntimeError(str(x['error']))
  return x['result']
def listens(pid,port):
 q=subprocess.run(['/usr/sbin/lsof','-nP','-a','-p',str(pid),f'-iTCP:{port}','-sTCP:LISTEN','-Fpnft'],capture_output=True,text=True,timeout=4)
 assert q.returncode in [0,1],q.stderr
 return {'listens':q.returncode==0,'stdout':q.stdout,'stderr':q.stderr}
results=[]
for index,name in enumerate(a.cases.split(',')):
 case=a.out/f'{index}-{name}';case.mkdir();d=Path(tempfile.mkdtemp(prefix='btx18-',dir='/tmp'));os.chmod(d,0o700);state=d/'model';sock=d/'rpc.sock';record=d/'worker.json';release=d/'release';procs=[];logs=[];child=None
 obs={'case':name,'binary_sha256':hashlib.sha256(b.read_bytes()).hexdigest(),'synthetic_adapter':True,'no_GPU':True,'trace':[]};start=time.monotonic()
 def note(step,**kw):obs['trace'].append({'seconds':round(time.monotonic()-start,4),'step':step,**kw})
 with socket.socket() as s:s.bind(('127.0.0.1',0));port=s.getsockname()[1]
 env={k:v for k,v in os.environ.items() if not k.startswith('BTX_')};env.update(BTX_MODEL_CUDA_LOADER=str(adapter),BTX_TEST_RECORD=str(record),BTX_TEST_RELEASE=str(release))
 cmd=[str(b),f'-modeldir={state}',f'-modelrpcsocket={sock}',f'-modelbind=127.0.0.1:{port}','-modelstorage=8MiB','-modelseed=off','-modelfollowpeers=0','-modellandiscovery=0','-modelnatpmp=0','-pwcchain=regtest']
 obs['command']=[x.replace(str(d),'<disposable>') for x in cmd]
 def launch(label):
  log=(case/(label+'.log')).open('wb');logs.append(log);q=subprocess.Popen(cmd,env=env,stdout=log,stderr=subprocess.STDOUT,start_new_session=True);procs.append(q)
  def ready():
   if q.poll() is not None:raise AssertionError(f'helper {label} exited {q.returncode}')
   return rpc(sock,'getmodelnetworkinfo')
  info=wait(ready);(case/(label+'-info.json')).write_text(json.dumps(info,indent=2)+'\n');note(label+'-ready',pid=q.pid);return q
 def stop(q):
  q.terminate();q.wait(timeout=12);assert q.returncode==0,q.returncode;note('clean-stop',pid=q.pid)
 try:
  q=launch('initial');assert listens(q.pid,port)['listens'];note('initial-listener',evidence=listens(q.pid,port))
  if name!='idle-crash':
   fixture=d/'fixture.safetensors';h=json.dumps({'weight':{'dtype':'F32','shape':[2,3],'data_offsets':[0,24]}},separators=(',',':')).encode();fixture.write_bytes(struct.pack('<Q',len(h))+h+struct.pack('<6f',1,2,3,4,5,6))
   hosted=rpc(sock,'hostmodel',[str(fixture),{'publish':False}]);obs['hosted']=hosted;mid=hosted['model_id'];loaded=rpc(sock,'loadmodel',[mid]);obs['loaded']=loaded
   w=json.loads(record.read_text());child=w['pid'];assert loaded['loader_pid']==child and w['ppid']==q.pid;assert w['args'][-2:]==['--hold','--smoke'];obs['worker']=w
   obs['worker_has_listener']=listens(child,port)['listens'];note('worker-listener-observation',pid=child,evidence=listens(child,port));obs['worker_lsof']=subprocess.run(['/usr/sbin/lsof','-nP','-p',str(child)],text=True,capture_output=True).stdout
   if name=='unload-crash':
    obs['unloaded']=rpc(sock,'unloadmodel',[mid]);wait(lambda:not listens(child,port)['listens']);note('worker-unloaded');child=None
  q.kill();q.wait(timeout=5);assert q.returncode==-signal.SIGKILL;note('owned-helper-crash',pid=q.pid)
  if name=='resident-crash':note('worker-after-crash',evidence=listens(child,port));obs['worker_alive_after_crash']=subprocess.run(['ps','-p',str(child),'-o','pid=,ppid=,stat='],text=True,capture_output=True).stdout
  replacement=launch('replacement');check=listens(replacement.pid,port);note('replacement-listener',evidence=check);obs['replacement_has_tcp_listener']=check['listens'];obs['replacement_rpc_responds']=True
  if name=='resident-crash' and obs.get('worker_has_listener'):
   assert not check['listens'];assert 'PQ1 bind' in (case/'replacement.log').read_text() and 'bind/listen failed' in (case/'replacement.log').read_text()
   release.write_text('release finite fixture\n');wait(lambda:record.with_suffix('.exited').exists());wait(lambda:not listens(child,port)['listens']);note('worker-normal-exit');child=None
   obs['after_release_polls']=[]
   for _ in range(3):
    info=rpc(sock,'getmodelnetworkinfo');v=listens(replacement.pid,port)['listens'];obs['after_release_polls'].append({'rpc':True,'tcp_listener':v});assert not v;time.sleep(.3)
   stop(replacement);final=launch('recovered');assert listens(final.pid,port)['listens'];note('recovered-listener',evidence=listens(final.pid,port));stop(final)
  else:
   assert check['listens'];assert 'PQ1 bind' not in (case/'replacement.log').read_text();stop(replacement)
   if child:release.write_text('release finite fixture\n');wait(lambda:record.with_suffix('.exited').exists());child=None
  obs['pass']=True
  obs['regression_pass']=not obs.get('worker_has_listener',False) and obs['replacement_has_tcp_listener']
 except Exception as e:obs['error']=repr(e)
 finally:
  release.write_text('cleanup\n')
  for q in procs:
   if q.poll() is None:
    q.terminate()
    try:q.wait(timeout=12)
    except subprocess.TimeoutExpired:q.kill();q.wait(timeout=4);obs['forced_cleanup']=True
  if child:
   try:wait(lambda:not listens(child,port)['listens'],seconds=5)
   except Exception:os.kill(child,signal.SIGTERM);obs['child_cleanup_signal']=True
  for log in logs:log.close()
  obs['owned_helpers_exited']=all(q.poll() is not None for q in procs)
  with socket.socket() as s:
   s.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
   try:s.bind(('127.0.0.1',port));obs['port_released']=True
   except OSError:obs['port_released']=False
  shutil.rmtree(d);obs['disposable_removed']=not d.exists();(case/'result.json').write_text(json.dumps(obs,indent=2)+'\n');results.append(obs)
  print(json.dumps({k:obs.get(k) for k in ['case','pass','error','replacement_has_tcp_listener','replacement_rpc_responds','port_released']}),flush=True)
 if obs.get('error'):break
(a.out/'results.json').write_text(json.dumps(results,indent=2)+'\n')
assert len(results)==len(a.cases.split(',')) and all(x.get('pass') and x['port_released'] and x['regression_pass'] for x in results),results[-1].get('error')
