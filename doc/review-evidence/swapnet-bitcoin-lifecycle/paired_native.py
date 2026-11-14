"""Native Bitcoin wallet + current production coordinator; BTX counterleg simulated."""
import os,sys,json,time,base64,hashlib,subprocess,shutil
from pathlib import Path
from decimal import Decimal
from urllib.request import Request,urlopen
from urllib.error import HTTPError
from dataclasses import asdict
import test_execution_v2 as fixture
from swapnet.drivers import UTXODriver
from swapnet.store import Store
from swapnet.journal import Journal
from swapnet.authorization import Authority
from swapnet.coordinator import Coordinator
from swapnet.policy import SafetyPolicy
from swapnet.vault import ForeignKeyVault,atomic_private_write
from swapnet.recovery import export_bundle,restore_bundle
from swapnet.errors import SwapError

D=Path(__file__).resolve().parent;R=D/os.environ.get('CASE_DIR','paired-runtime');R.mkdir(exist_ok=True,mode=0o700)
BINARY=Path(os.environ.get('CORE_BINARY',str(D/'bin/bitcoind')))
assert shutil.disk_usage(D).free>1.25*1024**3
calls=[];nodes=[];proc=None
result={'status':'INCOMPLETE','target':'f08e0b4be0eea06152ad83e47311ff8907f9c25d','scope':'Current production Python coordinator/driver and real Bitcoin Core30.4 wallet/chain; simulated BTX counterleg, no embedded native BTX runtime','binary_sha256':hashlib.sha256(BINARY.read_bytes()).hexdigest(),'cases':[]}
def rpc(method,*args,wallet=None):
 cookie=(R/'regtest/.cookie').read_bytes().strip()
 req=Request('http://127.0.0.1:38651'+('/wallet/'+wallet if wallet else ''),json.dumps({'id':1,'method':method,'params':args},default=str).encode(),{'Authorization':'Basic '+base64.b64encode(cookie).decode(),'Content-Type':'application/json'})
 try:response=urlopen(req,timeout=20)
 except HTTPError as e:response=e
 with response:x=json.load(response,parse_float=Decimal)
 if x.get('error'):raise SwapError(str(x['error']['code']),x['error']['message'])
 return x['result']
def wr(name):
 def f(method,*args):
  out=rpc(method,*args,wallet=name)
  if method=='walletcreatefundedpsbt':calls.append({'wallet':name,'method':method,'decoded':rpc('decodepsbt',out['psbt'])['tx']})
  return out
 return f
class NativePair(fixture.Pair):
 def open(self,n):
  folder=self.path/n;folder.mkdir(mode=0o700,exist_ok=True,parents=True);key=b'0123456789abcdef0123456789abcdef'
  if not (folder/'vault.key').exists():atomic_private_write(folder/'vault.key',key)
  st=Store(folder/'state.sqlite');j=Journal(st);a=Authority(st,j,self.time);v=ForeignKeyVault(folder/'foreign-vault.json',key);v.save()
  driver=UTXODriver(fixture.A,rpc,wr(n),wr('watch-'+n),j,v,network=fixture.NETWORK,hrp='bcrt',confirmations=2,clock=self.time)
  c=Coordinator(j,a,{fixture.A:driver,fixture.B:fixture.Driver(self.b,n)},self.identities[n],v,lambda peer,kind,sid,body:self.queue.append((n,peer,kind,sid,body)),clock=self.time,policy=SafetyPolicy(btx_confirmations=2,btc_confirmations=2,settlement_margin_seconds=10,reveal_margin_seconds=10))
  self.nodes[n]=(st,j,a,c)
def tick(p,pred):
 for _ in range(6):
  p.nodes['alice'][3].tick()
  if pred():return
 raise AssertionError({k:p.state('alice').get(k) for k in ['stage','last_error','last_action']})
def exported(p):return export_bundle(p.nodes['alice'][1],p.path/'alice','long independent disposable backup password',fixture.NETWORK)['path']
def transaction(txid):
 w=wr('alice')('gettransaction',txid,True);return {**rpc('decoderawtransaction',w['hex']),'confirmations':w.get('confirmations',0),'wallet_fee':w.get('fee')}

from swapnet.embedded import Host
from swapnet.rpcclient import LocalRPC
class SelectedPair(NativePair):
 def open(self,n):
  super().open(n);st,j,auth,c=self.nodes[n]
  host=Host.__new__(Host);host.config={'chain':'regtest'};host.network=fixture.NETWORK;host.journal=j;host.vault=c.vault
  chain=LocalRPC('http://127.0.0.1:38651',cookie_path=R/'regtest/.cookie')
  policy={'asset':fixture.A,'wallet':n,'watch_wallet':'watch-'+n,'confirmations':2,'fee_rate':2}
  driver=host._bitcoin(chain,policy);realwallet=driver.wallet
  def measured(method,*args):
   if method=='walletcreatefundedpsbt':
    row={'wallet':n,'options':args[3],'positional_psbt_version':args[6] if len(args)>6 else None};calls.append(row)
    try:out=realwallet(method,*args)
    except SwapError as e:row['error']={'code':e.code,'message':e.message};raise
    decoded=rpc('decodepsbt',out['psbt']);row['has_tx']=isinstance(decoded.get('tx'),dict);row['fee']=out['fee'];return out
   return realwallet(method,*args)
  driver.wallet=measured;driver.now=self.time;c.drivers[fixture.A]=driver
  c.test_host=host;c.test_chain=chain;c.test_policy=policy


def locks():return {x['txid']+':'+str(x['vout']) for x in wr('alice')('listlockunspent')}
try:
 with (D/(R.name+'-node.log')).open('wb') as log:
  proc=subprocess.Popen([str(BINARY),'-regtest=1','-datadir='+str(R),'-rpcport=38651','-port=38652','-server=1','-listen=0','-connect=0','-dnsseed=0','-discover=0','-dbcache=16','-par=1','-rpcthreads=1','-fastprune=1','-printtoconsole=1','-debuglogfile=0'],stdout=log,stderr=log)
 for _ in range(60):
  try:
   if rpc('getblockchaininfo')['chain']=='regtest':break
  except Exception:time.sleep(.2)
 else:raise RuntimeError('startup failed')
 genesis=rpc('getblockhash',0);assert genesis=='0f9188f13cb7b2c71f2a335e3a4fc328bf5beb436012afca590b1a11466e2206'
 fixture.NETWORK='521ad0951ed299e9c56aeb7db8188972772067560351b8e55adf71dbed532360';fixture.A='btc:'+genesis+':0:native';fixture.B='btx:'+fixture.NETWORK+':0:native'
 for n in ['alice','bob']:rpc('createwallet',n);rpc('createwallet','watch-'+n,True,True)
 rpc('generatetoaddress',110,wr('alice')('getnewaddress'))
 unspent=wr('alice')('listunspent',2);old=unspent[0];keep=[{'txid':old['txid'],'vout':old['vout']}];assert wr('alice')('lockunspent',False,keep)
 preexisting=locks();assert len(preexisting)==1
 p=SelectedPair(R/'pair');p.time.n=int(time.time());nodes.append(p);p.start();p.deliver();c=p.nodes['alice'][3];driver=c.drivers[fixture.A]
 driver.fee_rate=10;observations=[]
 for i in range(3):
  c.tick();state=p.state('alice');row={'attempt':i+1,'error':state.get('last_error'),'locks':sorted(locks())};observations.append(row);result['fee_failures']=observations
  assert state['last_error']['code']=='FEE_CAP'
  assert locks()==preexisting,'failed fee check changed pre-existing lock set'
  assert not p.nodes['alice'][1].operations(p.sid)
 driver.fee_rate=2
 original_sign=driver.adapter.sign_funding
 def refuse_sign(*args,**kwargs):raise SwapError('TEST_SIGN','Injected signer rejection')
 driver.adapter.sign_funding=refuse_sign;c.tick();assert p.state('alice')['last_error']['code']=='TEST_SIGN';assert locks()==preexisting
 assert not p.nodes['alice'][0].db.execute('select * from coinlocks').fetchall()
 driver.adapter.sign_funding=original_sign
 original_lock=p.nodes['alice'][0].lock_coins
 def refuse_store(*args,**kwargs):raise SwapError('TEST_STORE','Injected reservation rejection')
 p.nodes['alice'][0].lock_coins=refuse_store;c.tick();assert p.state('alice')['last_error']['code']=='TEST_STORE';assert locks()==preexisting
 p.nodes['alice'][0].lock_coins=original_lock
 c.tick();assert p.state('alice')['stage']=='prepared',p.state('alice').get('last_error')
 prepared_locks=locks();assert preexisting<prepared_locks
 prepared_ops=p.nodes['alice'][1].operations(p.sid);assert {o['kind'] for o in prepared_ops}=={'fund','refund'}
 c.tick();assert p.state('alice')['funding_broadcast'];assert locks()==preexisting
 assert all(x.get('has_tx') for x in calls if 'error' not in x)
 result['controls']={'preexisting_locks':sorted(preexisting),'after_fee_failures_unchanged':True,'signer_failure_cleanup':True,'store_failure_cleanup':True,'prepared_locks_retained':True,'healthy_funding':'funded','after_broadcast_only_preexisting':True,'fund_operations':len([x for x in prepared_ops if x['kind']=='fund'])}
 result['status']='PASS_PAIRED_NATIVE_REGRESSION';print(json.dumps(result['controls']),flush=True)
finally:
 for p in nodes:
  for n in p.nodes:
   try:p.close(n)
   except Exception:pass
 if proc and proc.poll() is None:
  try:rpc('stop');proc.wait(timeout=15)
  except Exception:proc.terminate();proc.wait(timeout=10)
 result['funding_calls']=calls
 (D/(R.name+'-result.json')).write_text(json.dumps(result,indent=2,default=str)+'\n')
