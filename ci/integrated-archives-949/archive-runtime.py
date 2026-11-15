"""Offline wallet-disabled archive lifecycle; run with system Python independent of producer."""
import os,sys,json,time,socket,subprocess,base64,urllib.request,urllib.error,signal,hashlib
from pathlib import Path
root=Path(sys.argv[1]).resolve();framework=Path(sys.argv[2]);out=Path(sys.argv[3]);out.mkdir(exist_ok=True);hidden=framework.with_name(framework.name+'.producer-hidden');rows=[]
def interrupted(*args):raise SystemExit('Owned runtime interrupted')
signal.signal(signal.SIGTERM,interrupted)
def rpc(d,port,method):
 auth=base64.b64encode((d/'regtest/.cookie').read_bytes().strip()).decode();req=urllib.request.Request('http://127.0.0.1:'+str(port),json.dumps({'id':'archive-acceptance','method':method,'params':[]}).encode(),{'Authorization':'Basic '+auth,'Content-Type':'application/json'})
 try:r=urllib.request.urlopen(req,timeout=2)
 except urllib.error.HTTPError as e:r=e
 with r:return json.load(r)
def run(label,enabled,reuse=None):
 d=out/(reuse or label);d.mkdir(exist_ok=True)
 with socket.socket() as sock:sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
 args=[str(root/'bin/btxd'),'-datadir='+str(d),'-regtest','-autoupdate=0','-modelnet=0','-server=1','-disablewallet','-listen=0','-connect=0','-dnsseed=0','-discover=0','-rpcbind=127.0.0.1','-rpcallowip=127.0.0.1','-rpcport='+str(port),'-dbcache=16','-par=1','-nosettings','-printtoconsole=1','-debuglogfile=0']
 if enabled:args+=['-swapnet=1']
 row={'case':label,'swapnet_argument':'1' if enabled else 'omitted','wallet_disabled':True,'modelnet_disabled_for_offline_test':True};p=None
 try:
  with (out/(label+'.log')).open('wb') as log:
   p=subprocess.Popen(args,env={'PATH':'/usr/bin:/bin','DYLD_PRINT_LIBRARIES':'1'},stdout=log,stderr=log)
   ready=False
   for _ in range(150):
    if p.poll() is not None:break
    try:
     ready=rpc(d,port,'getblockchaininfo').get('result',{}).get('chain')=='regtest'
     if ready:break
    except Exception:pass
    time.sleep(.2)
   assert ready,('Archive failed RPC admission',label,p.poll())
   row['network']=rpc(d,port,'getswapnetworkinfo')
   if enabled:
    info=row['network']['result'];assert info['in_process'] is True and info['automatic_spend_atoms']=='0' and info['wallet_loaded'] is False
   else:
    error=row['network'].get('error');assert error and error['code']==-1 and error['message']=='SwapNet is disabled or not initialized','Unexpected default-off RPC response'
   for _ in range(3):assert rpc(d,port,'getblockchaininfo')['result']['chain']=='regtest';time.sleep(.2)
   rpc(d,port,'stop');p.wait(timeout=15);assert p.returncode==0
   row.update(rpc_ready=True,clean_stop=True,exit=p.returncode)
 finally:
  if p and p.poll() is None:
   try:rpc(d,port,'stop');p.wait(timeout=8)
   except Exception:
    p.terminate()
    try:p.wait(timeout=8)
    except subprocess.TimeoutExpired:p.kill();p.wait(timeout=8)
   row['forced_cleanup']=True
  rows.append(row);(out/'lifecycle.json').write_text(json.dumps(rows,indent=2)+'\n')
assert framework.is_dir() and not hidden.exists()
try:
 framework.rename(hidden)
 run('default-off',False)
 run('explicit-on',True)
 run('restart-on',True,reuse='explicit-on')
finally:
 if hidden.exists():hidden.rename(framework)
assert len(rows)==3 and all(x.get('clean_stop') and not x.get('forced_cleanup') for x in rows)
print('Archive lifecycle PASS: omitted SwapNet flag, explicit enable, same-datadir restart; producer framework restored')
