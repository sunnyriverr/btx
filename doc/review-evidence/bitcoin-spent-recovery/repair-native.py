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

D=Path('records').resolve();D.mkdir(exist_ok=True);R=Path(os.environ['TEST_ROOT']);R.mkdir(exist_ok=True,mode=0o700)
BINARY=Path(os.environ['BITCOIND']).resolve()
assert shutil.disk_usage(D).free>1.25*1024**3
calls=[];funding_attempts=[];nodes=[];proc=None
result={'status':'INCOMPLETE','target':'d7b9594b1d6f0b69fc743341725ae04cbf9681fb','scope':'Current production Python coordinator/driver and real Bitcoin Core30.4 wallet/chain; simulated BTX counterleg, no embedded native BTX runtime','binary_sha256':hashlib.sha256(BINARY.read_bytes()).hexdigest(),'cases':[]}
from swapnet.authorization import Principal

def rpc(method,*args,wallet=None):
 cookie=(R/'regtest/.cookie').read_bytes().strip()
 req=Request('http://127.0.0.1:38641'+('/wallet/'+wallet if wallet else ''),json.dumps({'id':1,'method':method,'params':args},default=str).encode(),{'Authorization':'Basic '+base64.b64encode(cookie).decode(),'Content-Type':'application/json'})
 try:response=urlopen(req,timeout=20)
 except HTTPError as e:response=e
 with response:x=json.load(response,parse_float=Decimal)
 if x.get('error'):raise SwapError(str(x['error']['code']),x['error']['message'])
 return x['result']
def wr(name):
 def f(method,*args):
  if method=='walletcreatefundedpsbt':funding_attempts.append({'wallet':name})
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

from swapnet.terms import Agreement
from swapnet.funding_scan import find_funding_output

def advance(p,n):
 for _ in range(n):
  p.time.n+=600;p.b.height+=600;rpc('setmocktime',p.time.n)
  rpc('generatetoaddress',1,wr('alice')('getnewaddress'))

def spent_case():
 p=NativePair(R/'pair');p.time.n=int(time.time());nodes.append(p)
 p.start();p.deliver();assert p.state('alice')['stage']=='committed'
 backup=exported(p)
 tick(p,lambda:p.state('alice')['funding_broadcast'])
 original=dict(p.state('alice')['refs']['a']);terms=Agreement.parse(p.state('alice')['agreement']).long_leg
 advance(p,2)
 bob=p.nodes['bob'][3];d=bob.drivers[fixture.A];key=p.state('bob')['keys']['claim']
 template=d.prepare_claim_template(p.sid,terms,original,key,fee_atoms='100')
 secret=p.nodes['alice'][3].vault.secret(p.sid,terms.hashlock)
 claim=d.finish_claim(terms,original,template,secret);d.broadcast(claim.raw)
 advance(p,2)
 assert rpc('gettxout',original['txid'],original['vout'],True) is None
 spent=rpc('decoderawtransaction',claim.raw)
 assert spent['vin'][0]['txid']==original['txid'] and spent['vin'][0]['vout']==original['vout']
 payout=rpc('validateaddress',terms.payout)['scriptPubKey']
 assert spent['vout'][0]['scriptPubKey']['hex']==payout and spent['vout'][0]['value']==Decimal('0.00009900')
 history=wr('alice')('gettransaction',original['txid'],True);assert history['hex']
 result['original']={'funding':original,'claim_txid':claim.txid,'principal_atoms':10000,'claim_received_atoms':9900,'claim_fee_atoms':100,'wallet_history_present':True,'spent_on_chain':True}
 before=len(funding_attempts);p.close('alice');p.nodes.pop('alice')
 dest=R/'restored'/'alice';restore_bundle(backup,dest,'long independent disposable backup password',fixture.NETWORK);p.path=dest.parent;p.open('alice')
 c=p.nodes['alice'][3];driver=c.drivers[fixture.A]
 result['lookup_after_restore']=find_funding_output(driver,terms,p.sid)
 result['restored_before']={k:p.state('alice').get(k) for k in ['stage','funding_prepared','funding_broadcast','refs']}
 try:
  for _ in range(4):c.tick_one(p.sid)
 except Exception as e:result['resume_error']={'type':type(e).__name__,'message':str(e)}
 state=p.state('alice');ref=state['refs'].get('a');result['funding_attempts_after_restore']=len(funding_attempts)-before
 result['restored_after']={k:state.get(k) for k in ['stage','funding_prepared','funding_broadcast','refs','last_error']}
 result['another_payment']=bool(ref and ref['txid']!=original['txid'] and state['funding_broadcast'])
 if result['another_payment']:
  raw=transaction(ref['txid']);advance(p,2);out=rpc('gettxout',ref['txid'],ref['vout'],True)
  assert out and out['value']==Decimal('0.00010000') and out['scriptPubKey']['hex']==terms.lock_commitment
  assert transaction(ref['txid'])['confirmations']>=2
  result['second_payment']={'reference':ref,'principal_atoms':10000,'confirmed':True,'disjoint_inputs':{(i['txid'],i['vout']) for i in raw['vin']}.isdisjoint({(i['txid'],i['vout']) for i in transaction(original['txid'])['vin']})}
  assert result['second_payment']['disjoint_inputs']
 p.restart('alice');result['reopened']={k:p.state('alice').get(k) for k in ['stage','funding_prepared','funding_broadcast','refs']}
 assert not result['another_payment'] and result['funding_attempts_after_restore']==0
 assert result['restored_after']['refs']['a']==original
 assert result['reopened']['refs']['a']==original
 result['status']='PASS_ORIGINAL_SPENT_PAYMENT_RETAINED'

try:
 with (D/'current-native-node.log').open('wb') as log:
  proc=subprocess.Popen([str(BINARY),'-regtest=1','-datadir='+str(R),'-rpcport=38641','-port=38642','-server=1','-listen=0','-connect=0','-dnsseed=0','-discover=0','-dbcache=16','-par=1','-rpcthreads=1','-fastprune=1','-printtoconsole=1','-debuglogfile=0'],stdout=log,stderr=log)
 for _ in range(60):
  try:
   if rpc('getblockchaininfo')['chain']=='regtest':break
  except Exception:time.sleep(.2)
 else:raise RuntimeError('native startup failed')
 genesis=rpc('getblockhash',0);assert genesis=='0f9188f13cb7b2c71f2a335e3a4fc328bf5beb436012afca590b1a11466e2206'
 fixture.NETWORK='521ad0951ed299e9c56aeb7db8188972772067560351b8e55adf71dbed532360';fixture.A='btc:'+genesis+':0:native';fixture.B='btx:'+fixture.NETWORK+':0:native'
 for n in ['alice','bob']:rpc('createwallet',n);rpc('createwallet','watch-'+n,True,True)
 rpc('generatetoaddress',107,wr('alice')('getnewaddress'))
 assert shutil.disk_usage(D).free>1.25*1024**3
 spent_case()
finally:
 for p in nodes:
  for n in p.nodes:
   try:p.close(n)
   except Exception:pass
 if proc and proc.poll() is None:
  try:rpc('stop');proc.wait(timeout=15)
  except Exception:proc.terminate();proc.wait(timeout=10)
 result['rpc_funding_calls']=calls;result['rpc_funding_attempts']=funding_attempts
 (D/'spent-result.json').write_text(json.dumps(result,indent=2,default=str)+'\n')
