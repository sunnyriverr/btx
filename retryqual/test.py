import pathlib,subprocess,json,socket,time,os,hashlib,sys,shutil
B=pathlib.Path(sys.argv[1]).resolve();R=pathlib.Path(sys.argv[2]).resolve();OUT=pathlib.Path(sys.argv[3]).resolve();assert os.getuid()!=0;OUT.mkdir(parents=True,exist_ok=True);R.mkdir(mode=0o700);P=None;L=None;M=None;S=None;calls=[];cases=[];starts=0

def rpc(method,*args):
 with socket.socket(socket.AF_UNIX) as s:
  s.settimeout(8);s.connect(str(S));s.sendall((json.dumps({'id':len(calls)+1,'method':method,'params':list(args)})+'\n').encode());s.shutdown(socket.SHUT_WR)
  with s.makefile('rb') as f:v=json.loads(f.readline(2**20))
 calls.append({'method':method,'args':args,'reply':v});return v

def ok(method,*args):
 v=rpc(method,*args);assert v.get('error') is None,(method,v);return v['result']
def stop():
 global P,L
 if P:
  P.terminate()
  try:P.wait(12)
  except subprocess.TimeoutExpired:P.kill();P.wait(5);raise AssertionError('unclean helper stop')
  assert P.returncode==0,P.returncode;P=None
 if L:L.close();L=None
 if S and S.exists():S.unlink()
def boot(directory):
 global P,L,M,S,starts
 M=directory;M.mkdir(exist_ok=True);S=M.parent/(M.name+'.sock');starts+=1;L=(OUT/f'helper-{starts}.log').open('wb')
 P=subprocess.Popen([str(B),'-modeldir='+str(M),'-modelrpcsocket='+str(S),'-modelstorage=8MiB','-modelbind=off','-modellandiscovery=0','-modelnatpmp=0','-modelfollowpeers=0','-modelseed=off','-modelpreserverare=0'],stdout=L,stderr=subprocess.STDOUT)
 end=time.monotonic()+25
 while time.monotonic()<end:
  assert P.poll() is None,'helper exited before ready'
  if S.exists():
   try:ok('getbountyfunding','synthetic');return
   except (ConnectionRefusedError,FileNotFoundError):pass
  time.sleep(.1)
 raise AssertionError('helper startup timed out')
def fact(outpoint,bounty,amount):return {'outpoint':outpoint,'bounty_id':bounty,'lot_id':outpoint,'amount_atoms':str(amount),'confirmations':6,'height':100,'spent':False}
A=fact('A:0','synthetic',100);BB=fact('B:0','synthetic',200);SENT=fact('S:0','unrelated',50)
def setup_case(label):
 boot(R/label)
 for f in [SENT,A,BB]:ok('observebountychain',f)
 assert funding()==300 and sentinel()==50
 return next(M.rglob('bounty-store.json'))
def funding():return int(ok('getbountyfunding','synthetic')['confirmed_atoms'])
def sentinel():return int(ok('getbountyfunding','unrelated')['confirmed_atoms'])
def fail_one(path,args):
 old=path.read_bytes();parent=path.parent;parent.chmod(0o500);fault=False
 try:
  try:
   marker=parent/'fault-control';marker.write_bytes(b'not allowed');marker.unlink()
  except PermissionError:fault=True
  assert fault,'permission fault not established'
  reply=rpc('reorgbountychain',args)
 finally:parent.chmod(0o700)
 assert isinstance(reply.get('error'),dict) and reply['error'].get('code')=='IO',reply
 assert path.read_bytes()==old,'durable store changed on IO failure'
 assert funding()==100 and sentinel()==50,'failure not at expected mutation/persistence point'
 assert not pathlib.Path(str(path)+'.tmp').exists(),'failed save left temp'
 return {'fault_proved':True,'reply':reply,'disk_sha256_before_and_after':hashlib.sha256(old).hexdigest(),'live_after_failed_save':100,'unrelated_after_failed_save':50}
def finish_case(label,details):
 cases.append({'label':label,**details});stop()
try:
 path=setup_case('healthy');res=ok('reorgbountychain',{'bounty_id':'synthetic'});assert funding()==100 and sentinel()==50;d=M;stop();boot(d);assert funding()==100 and sentinel()==50;finish_case('healthy_one_undo',{'persisted_after_restart':100})
 for keyed in [False,True]:
  label='same_key_retry' if keyed else 'unkeyed_retry';path=setup_case(label);args={'bounty_id':'synthetic'}
  if keyed:args['idempotency_key']='same-operation'
  details=fail_one(path,args);details['retry_reply']=ok('reorgbountychain',args);details['retry_live_total']=funding();assert details['retry_live_total']==0 and sentinel()==50,'second observation not consumed as hypothesized'
  assert not ok('getbountyfunding','synthetic')['facts'],'expected both A/B removed'
  directory=M;stop();boot(directory);assert funding()==0 and sentinel()==50;details['retry_persisted_after_restart']=0;details['unrelated_preserved']=True;finish_case(label,details)
 path=setup_case('reobserve_without_retry');details=fail_one(path,{'bounty_id':'synthetic','idempotency_key':'do-not-retry'});ok('observebountychain',A);assert funding()==100 and sentinel()==50;directory=M;stop();boot(directory);assert funding()==100 and sentinel()==50;facts=ok('getbountyfunding','synthetic')['facts'];assert len(facts)==1 and facts[0]['outpoint']=='A:0';details['known_correct_A_reobservation_persisted']=True;details['persisted_after_restart']=100;finish_case('verified_reobservation_without_undo_retry',details)
 path=setup_case('restart_without_retry');details=fail_one(path,{'bounty_id':'synthetic'});directory=M;stop();boot(directory);assert funding()==300 and sentinel()==50;details['unchanged_durable_state_reloaded']=300;details['intended_undo_not_committed']=True;finish_case('restart_discards_failed_memory_undo',details)
 result={'status':'DIAGNOSIS_REPRODUCED_WITH_RECOVERY_CONTROLS','uid':os.getuid(),'gid':os.getgid(),'binary_sha256':hashlib.sha256(B.read_bytes()).hexdigest(),'starts':starts,'cases':cases,'calls':calls};(OUT/'result.json').write_text(json.dumps(result,indent=2));print(result['status'],len(cases),'cases',starts,'starts',len(calls),'RPCs',flush=True)
finally:
 if M and M.exists():
  for path in M.rglob('*'):
   if path.is_dir():path.chmod(0o700)
  M.chmod(0o700)
 if P:stop()
