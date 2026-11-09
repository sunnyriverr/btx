from pathlib import Path
import json,os,sys,subprocess,time,shutil,socket,base64,urllib.request,urllib.error
import checkpoint
import integration_support as s
P=Path(__file__).resolve().parent;E=s.E;B=s.BUILD;ROOT=s.ROOT;SOURCE=s.SOURCE
I=json.loads((P/'target-inputs.json').read_text());TARGET=I['source'];s.STATE=E/'lifecycle.json';s.R=json.loads(s.STATE.read_text())if s.STATE.exists()else dict(status='SETUP',commands=[],process_active=False,source=TARGET,boots=[],forced_cleanup=[],tests_run=0,builds_run=0);R=s.R

def prepare():
 setup=json.loads((E/'result.json').read_text());marker=B/'btx-checkpoint.json';assert checkpoint.digest(marker)==I['checkpoint_sha256'];cp=json.loads(marker.read_text());assert cp['profile']['source']==TARGET
 assert cp['profile']['baseline_profile']==setup['profile'],'Native profile differs from saved build; do not run a mismatched binary'
 s.need('target-fetch',['git','fetch','--no-tags','--depth=1','https://github.com/btxchain/btx.git',TARGET],180)
 s.need('target-checkout',['git','checkout','--detach',TARGET],90)
 cat=s.catalog(TARGET,'target-before');assert cat==cp['source_catalog'];R['restore']=checkpoint.restore(ROOT,SOURCE,cp['profile'],cat);assert R['restore']['files_verified']==12858
 assert sum(k.endswith('.obj')for k in cp['files'])==5901
 for name,h in I['binaries'].items():assert checkpoint.digest(B/'bin'/(name+'.exe'))==h
 R['source_catalog']=cat;R['native_profile']=setup['profile'];R['checkpoint_sha256']=I['checkpoint_sha256'];R['binary_hashes']=I['binaries'];R['status']='RESTORED_VERIFIED';s.save()
 header=B/'src/bitcoin-build-info.h';text=header.read_text();assert TARGET in text and 'BUILD_GIT_DIRTY 0'in text;shutil.copyfile(header,E/'bitcoin-build-info.h')
 s.save()

def rpc(port,cookie,method,params=None):
 req=urllib.request.Request('http://127.0.0.1:'+str(port),data=json.dumps({'jsonrpc':'1.0','id':'native-life','method':method,'params':params or []}).encode(),headers={'Authorization':'Basic '+base64.b64encode(cookie.read_bytes().strip()).decode(),'Content-Type':'application/json'})
 try:
  with urllib.request.urlopen(req,timeout=4)as f:v=json.load(f)
 except urllib.error.HTTPError as e:v=json.loads(e.read())
 if v.get('error'):raise RuntimeError(method+': '+json.dumps(v['error']))
 return v['result']

def processes():
 prefix=str(B/'bin').replace("'","''")
 ps="$x=@(Get-CimInstance Win32_Process | Where-Object { $_.ExecutablePath -and $_.ExecutablePath.StartsWith('"+prefix+"',[StringComparison]::OrdinalIgnoreCase) } | Select-Object ProcessId,ParentProcessId,ExecutablePath,CommandLine,CreationDate);ConvertTo-Json -InputObject $x -Compress"
 return json.loads(subprocess.check_output(['powershell','-NoProfile','-Command',ps],text=True))

def freeport():
 with socket.socket()as sock:sock.bind(('127.0.0.1',0));return sock.getsockname()[1]

def wait(fn,limit,node):
 end=time.monotonic()+limit;last=None
 while time.monotonic()<end:
  if node.poll()is not None:raise RuntimeError('node exited '+str(node.returncode))
  try:
   v=fn()
   if v:return v
  except (OSError,RuntimeError)as e:last=str(e)
  time.sleep(.25)
 raise TimeoutError(str(last))

def run():
 assert R['status']=='RESTORED_VERIFIED';assert not processes();root=Path('D:/dl'+os.environ['GITHUB_RUN_ID']);assert not root.exists();root.mkdir();R['runtime_root']=str(root);data=root/'node';data.mkdir();model=root/'model-store';active=[];common=['-regtest','-server=1','-disablewallet=1','-listen=0','-listenonion=0','-connect=0','-networkactive=0','-dnsseed=0','-fixedseeds=0','-discover=0','-upnp=0','-natpmp=0','-autoupdate=0','-modellandiscovery=0','-modelfollowpeers=0','-modelseed=off','-modelbind=0','-modelstorage=16MiB','-modeldir='+str(model),'-printtoconsole=0'];R['node_common_args']=common;R['status']='RUNNING';s.save()
 try:
  for number in [1,2]:
   port=freeport();cookie=data/'regtest/.cookie';f=(E/('boot'+str(number)+'-console.log')).open('wb');argv=[str(B/'bin/btxd.exe'),'-datadir='+str(data),'-rpcbind=127.0.0.1','-rpcallowip=127.0.0.1','-rpcport='+str(port),*common];node=subprocess.Popen(argv,cwd=SOURCE,stdout=f,stderr=subprocess.STDOUT);active.append((node,f));boot=dict(number=number,pid=node.pid,args=argv,rpc_port=port,health=[]);R['boots'].append(boot);s.save()
   chain=wait(lambda:rpc(port,cookie,'getblockchaininfo')if cookie.exists()else None,90,node);assert chain['chain']=='regtest'and chain['blocks']==0
   net=rpc(port,cookie,'getnetworkinfo');assert not net['networkactive']and net['connections']==0;assert rpc(port,cookie,'getblockcount')==0
   boot.update(rpc_ready=True,chain=chain,network=net,model=rpc(port,cookie,'getmodelnetworkinfo'));boot['wallet_disabled_argument']=True
   if number==2:assert chain['bestblockhash']==R['boots'][0]['chain']['bestblockhash'];boot['same_chain_after_restart']=True
   guard_error=None;status=None
   try:status=wait(lambda:rpc(port,cookie,'modelsecurity',[{'op':'status'}]),25,node)
   except (OSError,RuntimeError,TimeoutError)as e:guard_error=repr(e)
   boot.update(security_status=status,guard_error=guard_error,guard_observed=False)
   rows=processes();boot['processes']=rows;guards=[p for p in rows if Path(p['ExecutablePath']).name.lower()=='btx-guardd.exe'];helpers=[p for p in rows if Path(p['ExecutablePath']).name.lower()=='btx-modeld.exe'];boot['helper_processes']=helpers
   if status is not None:
    assert status['ok']is True and status['automatic_spend_atoms']=='0'and status['policy_installed']is False and status['journal_valid']is True
    assert len(guards)==1 and guards[0]['ParentProcessId']==node.pid;boot['guard_observed']=True;boot['guard_pid']=guards[0]['ProcessId']
   for i in range(10):
    assert node.poll()is None;ch=rpc(port,cookie,'getblockchaininfo');assert ch['blocks']==0 and ch['bestblockhash']==chain['bestblockhash'];assert rpc(port,cookie,'getconnectioncount')==0
    sample={'poll':i,'height':ch['blocks']}
    if boot['guard_observed']:
     st=rpc(port,cookie,'modelsecurity',[{'op':'status'}]);assert st['ok']and st['automatic_spend_atoms']=='0'and st['journal_valid'];sample['security_status']=st
    boot['health'].append(sample);time.sleep(.5)
   endrows=processes();boot['processes_after_health']=endrows
   if boot['guard_observed']:assert [p['ProcessId']for p in endrows if Path(p['ExecutablePath']).name.lower()=='btx-guardd.exe']==[boot['guard_pid']]
   guardfile=model/'swarm/guard-process.json'
   if guardfile.exists():
    gs=json.loads(guardfile.read_text());boot['guard_process_record']=gs
    if boot['guard_observed']:assert gs['ready']and gs['pid']==boot['guard_pid']and gs['restart_count']==0
   boot['stop_reply']=rpc(port,cookie,'stop');boot['exit']=node.wait(timeout=45);f.close();assert boot['exit']==0
   until=time.monotonic()+10
   while processes()and time.monotonic()<until:time.sleep(.25)
   boot['remaining_processes']=processes();assert not boot['remaining_processes'];assert not cookie.exists()
   with socket.socket()as sock:sock.settimeout(1);boot['rpc_port_closed']=sock.connect_ex(('127.0.0.1',port))!=0
   assert boot['rpc_port_closed'];boot['cookie_removed']=True
   if(data/'regtest/debug.log').exists():shutil.copyfile(data/'regtest/debug.log',E/('boot'+str(number)+'-debug.log'))
   s.save()
  if all(b['guard_observed']for b in R['boots']):
   s.need('security-offline-inspect',[str(B/'bin/btx-security.exe'),'inspect','--root',str(model/'security')],30)
   inspect=json.loads((E/'security-offline-inspect.log').read_text());assert inspect['journal_valid']and inspect['automatic_spend_atoms']=='0';R['offline_security_inspect']=inspect;R['status']='NODE_AND_GUARD_LIFECYCLE_PASS'
  else:R['status']='NODE_LIFECYCLE_PASS_GUARD_BLOCKED'
 finally:
  for node,f in active:
   if node.poll()is None:
    R['forced_cleanup'].append(node.pid);subprocess.run(['taskkill','/PID',str(node.pid),'/T','/F'],capture_output=True);node.wait(timeout=30)
   if not f.closed:f.close()
  leftover=processes();R['remaining_before_forced_cleanup']=leftover
  if leftover:R['forced_cleanup']+=['descendants'];s.quiesce()
  assert not processes();R['process_cleanup_verified']=True
  if R['forced_cleanup']:R['status']='FAILED_FORCED_CLEANUP'
  # Only owned disposable runtime removed, after preserving useful logs.
  if root.exists():shutil.rmtree(root)
  R['runtime_removed']=not root.exists();s.save()
 assert R['status']=='NODE_AND_GUARD_LIFECYCLE_PASS',R['status']

def verify():
 cp=json.loads((B/'btx-checkpoint.json').read_text());assert checkpoint.digest(B/'btx-checkpoint.json')==I['checkpoint_sha256']
 current={str(p.relative_to(ROOT))for folder in ['project-build','vcpkg-installed']for p in(ROOT/folder).rglob('*')if p.is_file()and not p.is_symlink()and p.name!='btx-checkpoint.json'};assert current==set(cp['files'])
 for k,v in cp['files'].items():assert checkpoint.digest(ROOT/k)==v['sha256'],k
 assert s.catalog(TARGET,'target-after')==R['source_catalog'];assert not processes();R['cache_unchanged']=True;R['cached_objects_unchanged']=5901;R['cached_files_unchanged']=12858;s.save()

