import json,hashlib,subprocess,tarfile,resource,time,base64,os,shutil
from pathlib import Path
from urllib.request import Request,urlopen
from urllib.error import HTTPError
P=Path(__file__).resolve().parents[1];R=P/'repair';out=R/'relocated archives';out.mkdir(exist_ok=True);results=([json.loads((R/'archive-results-previous-qualified.json').read_text())[0]] if os.environ.get('ONLY_CANDIDATE_TESTS') else [])
for name in ['baseline','candidate']:
 target=out/(name+' moved')
 if target.exists():shutil.rmtree(target)
 target.mkdir(exist_ok=True)
 with tarfile.open(R/name/'archives/btx-0.34.16-arm64-apple-darwin.tar.gz') as tar:tar.extractall(target,filter='data')
roots={x:out/(x+' moved')/'btx-0.34.16' for x in ['baseline','candidate']}
def limits():resource.setrlimit(resource.RLIMIT_CORE,(0,0))
def rpc(d,method):
 cookie=(d/'regtest/.cookie').read_bytes().strip();req=Request('http://127.0.0.1:49671',json.dumps({'id':'archive-control','method':method,'params':[]}).encode(),{'Authorization':'Basic '+base64.b64encode(cookie).decode(),'Content-Type':'application/json'})
 try:r=urlopen(req,timeout=2)
 except HTTPError as e:r=e
 with r:v=json.load(r)
 return v

def run(label,root,swapnet,expected,reuse=None):
 d=R/'archive-runtime'/(reuse or label);d.mkdir(parents=True,exist_ok=True);log=R/(label+'.log');cmd=[str(root/'bin/btxd'),'-datadir='+str(d),'-regtest=1','-autoupdate=0','-modelnet=0','-swapnet='+str(swapnet),'-server=1','-disablewallet=1','-listen=0','-connect=0','-dnsseed=0','-discover=0','-rpcbind=127.0.0.1','-rpcallowip=127.0.0.1','-rpcport=49671','-port=49672','-dbcache=16','-par=1','-nosettings','-printtoconsole=1','-debuglogfile=0'];proc=None;row={'case':label,'expected_ready':expected,'swapnet':swapnet,'environment':'PATH=/usr/bin:/bin; DYLD_PRINT_LIBRARIES=1 only (no loader overrides)','archive':str(root.relative_to(R))};start=time.monotonic()
 try:
  with log.open('wb') as handle:
   proc=subprocess.Popen(cmd,env={'PATH':'/usr/bin:/bin','DYLD_PRINT_LIBRARIES':'1'},stdout=handle,stderr=handle,preexec_fn=limits)
   ready=False
   for _ in range(150):
    if proc.poll() is not None:break
    try:
     if rpc(d,'getblockchaininfo').get('result',{}).get('chain')=='regtest':ready=True;break
    except Exception:pass
    time.sleep(.2)
   row['rpc_ready']=ready
   if ready:
    row['network']=rpc(d,'getswapnetworkinfo')
    if swapnet:
     info=row['network']['result'];assert info['in_process'] and info['automatic_spend_atoms']=='0' and info['wallet_loaded'] is False
    else:assert row['network']['error']
    for _ in range(3):assert rpc(d,'getblockchaininfo')['result']['chain']=='regtest';time.sleep(.2)
    rpc(d,'stop');proc.wait(timeout=15);row['clean_stop']=proc.returncode==0
   row['exit']=proc.poll();row['matched']=ready==expected and (not ready or row['clean_stop'])
 finally:
  if proc and proc.poll() is None:
   try:rpc(d,'stop');proc.wait(timeout=8)
   except Exception:proc.terminate();proc.wait(timeout=8)
   row['forced_cleanup']=True
  row['seconds']=round(time.monotonic()-start,3);results.append(row);(R/'archive-results.json').write_text(json.dumps(results,indent=2)+'\n');print(label,json.dumps(row),flush=True)
 assert row['matched'],row
# Hide the complete producer runtime while consumers execute. Restore it unconditionally.
producer=P/'python-pkg';hidden=P/'python-pkg-producer-hidden';producer.rename(hidden)
try:
 if not os.environ.get('ONLY_CANDIDATE_TESTS'):run('baseline-default-off',roots['baseline'],0,False)
 run('candidate-default-off',roots['candidate'],0,True)
 run('candidate-enabled',roots['candidate'],1,True)
 run('candidate-restart',roots['candidate'],1,True,reuse='candidate-enabled')
finally:hidden.rename(producer)
for name,root in roots.items():
 archive=R/name/'archives/btx-0.34.16-arm64-apple-darwin.tar.gz';print(name,'archiveSHA',hashlib.sha256(archive.read_bytes()).hexdigest(),flush=True)
print('ARCHIVES COMPLETE',flush=True)
