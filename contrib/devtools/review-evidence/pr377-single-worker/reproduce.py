#!/usr/bin/env python3
"""Bounded local RPC scheduling observation; no wallet, mining, peers or exploit traffic."""
from pathlib import Path
import argparse,subprocess,tempfile,shutil,json,time,threading,http.client,base64,hashlib,socket,os
ap=argparse.ArgumentParser();ap.add_argument('--bin-dir',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);args=ap.parse_args();args.out.mkdir(parents=True,exist_ok=False)
b=args.bin_dir.resolve();out=args.out.resolve();results=[]
def port():
 with socket.socket() as s:s.bind(('127.0.0.1',0));return s.getsockname()[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
for workers in [1,2]:
 d=Path(tempfile.mkdtemp(prefix='btx377-'));os.chmod(d,0o700);case=out/f'workers-{workers}';case.mkdir();rpcport=port();p=None;threads=[]
 obs={'workers':workers,'rpcport':rpcport,'wait_ms':15000,'commands':[],'binary_sha256':{x:sha(b/x) for x in ['btxd','btx-modeld']}}
 log=(case/'stdout.log').open('wb')
 cmd=[str(b/'btxd'),'-regtest',f'-datadir={d}','-server=1','-listen=0','-connect=0','-dnsseed=0','-discover=0','-natpmp=0','-disablewallet=1','-dbcache=4','-maxmempool=41','-persistmempool=0',f'-rpcport={rpcport}','-rpcbind=127.0.0.1','-rpcallowip=127.0.0.1',f'-rpcthreads={workers}','-modelnet=1',f'-modelhelper={b / "btx-modeld"}','-modelbind=off','-modellandiscovery=0','-modelstorage=0','-rpcdoccheck=0','-printtoconsole=0']
 obs['args']=[x.replace(str(d),'<disposable-datadir>') for x in cmd]
 def rpc(method,params=None,timeout=25):
  cookie=(d/'regtest/.cookie').read_text().strip();conn=http.client.HTTPConnection('127.0.0.1',rpcport,timeout=timeout)
  try:
   conn.request('POST','/',json.dumps({'jsonrpc':'2.0','id':method,'method':method,'params':params or []}),{'Authorization':'Basic '+base64.b64encode(cookie.encode()).decode(),'Content-Type':'application/json'})
   response=conn.getresponse();body=json.loads(response.read())
   if body.get('error'):raise RuntimeError(str(body['error']))
   return body['result']
  finally:conn.close()
 def measure(method,params=None):
  start=time.monotonic();v=rpc(method,params);return {'elapsed_s':time.monotonic()-start,'result':v}
 def wait_result(dst,method,params):
  try:dst.update(measure(method,params))
  except Exception as e:dst['error']=repr(e)
 try:
  p=subprocess.Popen(cmd,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
  end=time.monotonic()+60
  while True:
   if p.poll() is not None:raise RuntimeError(f'node startup exit {p.returncode}')
   try:
    info=rpc('getmodelnetworkinfo',timeout=2)
    if info.get('owner_helper_pid',0)>0 and info.get('helper_ready'):break
   except (OSError,ValueError,RuntimeError):pass
   if time.monotonic()>end:raise RuntimeError('helper not ready within60s')
   time.sleep(.15)
  obs['owned_helper_pid']=info['owner_helper_pid'];obs['before']=measure('getblockcount')
  first={};t=threading.Thread(target=wait_result,args=(first,'waitformodelevent',[{'cursor':1<<60,'timeout_ms':15000}]),daemon=True);t.start();threads.append(t)
  end=time.monotonic()+5
  while True:
   active=rpc('getrpcinfo',timeout=2)['active_commands']
   if any(x['method']=='waitformodelevent' for x in active):break
   if time.monotonic()>end:raise RuntimeError('wait never became active')
   time.sleep(.02)
  obs['active_before_probe']=active
  probe={};q=threading.Thread(target=wait_result,args=(probe,'getblockcount',[]),daemon=True);q.start();threads.append(q)
  time.sleep(.2);obs['control_during_wait']=measure('getrpcinfo');obs['ordinary_pending_after_200ms']=q.is_alive()
  q.join(22);t.join(22)
  assert not t.is_alive() and not q.is_alive(),'bounded calls failed to finish'
  obs['event_wait']=first;obs['ordinary_during_wait']=probe
  assert 'error' not in first and first['result']['timeout'] is True,first
  assert probe.get('result')==0,probe
  obs['after']=measure('getblockcount');obs['slot_reuse']=measure('waitformodelevent',[{'cursor':1<<60,'timeout_ms':0}]);obs['control_available']=obs['control_during_wait']['elapsed_s']<2
  obs['ordinary_available_within_2s']=probe['elapsed_s']<2
  assert obs['control_available'];assert obs['after']['elapsed_s']<2
  obs['stop']=measure('stop');p.wait(timeout=15);obs['exit_code']=p.returncode
  assert p.returncode==0
 except Exception as e:
  obs['harness_error']=repr(e)
 finally:
  for t in threads:t.join(timeout=20)
  if p is not None and p.poll() is None:
   p.terminate()
   try:p.wait(timeout=15)
   except subprocess.TimeoutExpired:p.kill();p.wait(timeout=5);obs['forced_cleanup']=True
  log.close()
  if (d/'regtest/debug.log').exists():shutil.copy2(d/'regtest/debug.log',case/'debug.log')
  # Generated model identities and cookies stay in disposable private dirs, then are removed.
  shutil.rmtree(d)
  (case/'result.json').write_text(json.dumps(obs,indent=2)+'\n');results.append(obs)
  print(json.dumps({k:obs.get(k) for k in ['workers','ordinary_available_within_2s','ordinary_during_wait','before','after','control_available','exit_code','harness_error']}),flush=True)
 if obs.get('harness_error'):break
(out/'results.json').write_text(json.dumps(results,indent=2)+'\n')
assert len(results)==2 and all(not x.get('harness_error') for x in results)
