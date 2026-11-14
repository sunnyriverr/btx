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

D=Path(__file__).resolve().parent;R=D/'native-runtime';R.mkdir(exist_ok=True,mode=0o700)
BINARY=Path('work/btx-lanes/session-3/swapnet-maker-terminal-capacity/embedded-runtime/bitcoin-30.4/bin/bitcoind').resolve()
assert shutil.disk_usage(D).free>1.25*1024**3
calls=[];nodes=[];proc=None
result={'status':'INCOMPLETE','target':'cb823a94f55685c60fd30e0b6d14d02ea1b951a8','scope':'Current production Python coordinator/driver and real Bitcoin Core30.4 wallet/chain; simulated BTX counterleg, no embedded native BTX runtime','binary_sha256':hashlib.sha256(BINARY.read_bytes()).hexdigest(),'cases':[]}
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
def case(label):
 p=NativePair(R/('case-'+label));p.time.n=int(time.time());nodes.append(p)
 p.start();p.deliver();assert p.state('alice')['stage']=='committed'
 if label=='committed':backup=exported(p)
 p.nodes['alice'][3].tick();assert p.state('alice')['stage']=='prepared',p.state('alice').get('last_error')
 if label=='prepared':backup=exported(p)
 tick(p,lambda:p.state('alice')['funding_broadcast'])
 original=dict(p.state('alice')['refs']['a']);first=transaction(original['txid']);terms=p.state('alice')['agreement']['long_leg'];before_calls=len(calls)
 assert rpc('gettxout',original['txid'],original['vout'],True)['scriptPubKey']['hex']==terms['lock_commitment']
 # Keep the same chain tip so the deadline check does not obscure funding recovery.
 p.time.n=int(time.time())
 if label=='restart':p.restart('alice')
 else:
  p.close('alice');dest=R/('restored-'+label)/'alice';restore_bundle(backup,dest,'long independent disposable backup password',fixture.NETWORK);p.path=dest.parent;p.open('alice')
 for _ in range(4):p.nodes['alice'][3].tick()
 state=p.state('alice');ref=state['refs'].get('a');assert ref, {k:state.get(k) for k in ['stage','last_error','last_action']};last=transaction(ref['txid'])
 unique=ref['txid']!=original['txid'];extra=len(calls)-before_calls
 if label=='committed':
  assert unique and extra==1,(state.get('last_error'),ref,original,extra)
  assert {v['txid']+':'+str(v['vout']) for v in first['vin']}.isdisjoint({v['txid']+':'+str(v['vout']) for v in last['vin']})
  rpc('generatetoaddress',1,wr('alice')('getnewaddress'))
  assert transaction(ref['txid'])['confirmations']>=1
 else:assert not unique and extra==0,(label,state.get('last_error'),extra)
 for r in [original,ref]:
  o=rpc('gettxout',r['txid'],r['vout'],True);assert o and o['scriptPubKey']['hex']==terms['lock_commitment'] and o['value']==Decimal('0.00010000')
 row={'snapshot':label,'additional_funding_preparations':extra,'distinct_payment':unique,'original':original,'restored_reference':ref,'stage':state['stage'],'funding_broadcast':state['funding_broadcast'],'last_action':state.get('last_action'),'last_error':state.get('last_error'),'original_inputs':first['vin'],'restored_inputs':last['vin'],'same_script':terms['lock_commitment'],'each_amount_atoms':10000}
 result['cases'].append(row);print(json.dumps({k:row[k] for k in ['snapshot','additional_funding_preparations','distinct_payment','stage','funding_broadcast','last_action','last_error']}),flush=True)
 for n in p.nodes:p.close(n)
 nodes.remove(p)
try:
 with (D/'native-node.log').open('wb') as log:
  proc=subprocess.Popen([str(BINARY),'-regtest=1','-datadir='+str(R),'-rpcport=38641','-port=38642','-server=1','-listen=0','-connect=0','-dnsseed=0','-discover=0','-dbcache=16','-par=1','-rpcthreads=1','-fastprune=1','-printtoconsole=1','-debuglogfile=0'],stdout=log,stderr=log)
 for _ in range(60):
  try:
   if rpc('getblockchaininfo')['chain']=='regtest':break
  except Exception:time.sleep(.2)
 else:raise RuntimeError('native startup failed')
 genesis=rpc('getblockhash',0);assert genesis=='0f9188f13cb7b2c71f2a335e3a4fc328bf5beb436012afca590b1a11466e2206'
 fixture.NETWORK='521ad0951ed299e9c56aeb7db8188972772067560351b8e55adf71dbed532360';fixture.A='btc:'+genesis+':0:native';fixture.B='btx:'+fixture.NETWORK+':0:native'
 for n in ['alice','bob']:
  for name,watch in [(n,False),('watch-'+n,True)]:
   if name not in rpc('listwallets'):
    if (R/'regtest/wallets'/name).exists():rpc('loadwallet',name)
    else:rpc('createwallet',name,watch,watch)
 if rpc('getblockcount')<107:rpc('generatetoaddress',107,wr('alice')('getnewaddress'))
 assert shutil.disk_usage(D).free>1.25*1024**3
 # The prior attempt already funded and mined both committed-snapshot outputs.
 # Verify that saved run instead of creating duplicate transactions again.
 import sqlite3
 saved=[]
 for folder in ['case-committed','restored-committed']:
  db=sqlite3.connect(str(R/folder/'alice/state.sqlite'));saved.append(json.loads(db.execute('select body from sn_negotiations').fetchone()[0]));db.close()
 refs=[x['refs']['a'] for x in saved];assert refs[0]['txid']!=refs[1]['txid']
 txs=[transaction(x['txid']) for x in refs];assert all(x['confirmations']>=1 for x in txs)
 assert {v['txid']+':'+str(v['vout']) for v in txs[0]['vin']}.isdisjoint({v['txid']+':'+str(v['vout']) for v in txs[1]['vin']})
 terms=saved[0]['agreement']['long_leg'];assert terms==saved[1]['agreement']['long_leg']
 for ref in refs:
  out=rpc('gettxout',ref['txid'],ref['vout'],True);assert out and out['scriptPubKey']['hex']==terms['lock_commitment'] and out['value']==Decimal('0.00010000')
 result['cases'].append({'snapshot':'committed','reused_prior_run':True,'distinct_payment':True,'original':refs[0],'restored_reference':refs[1],'transactions':txs,'same_terms':True,'both_confirmed':True,'each_amount_atoms':10000,'stage':saved[1]['stage']})
 print('committed snapshot: verified BOTH distinct funded outputs confirmed; disjoint native wallet inputs; identical terms',flush=True)
 for label in ['prepared','restart']:case(label)
 result['status']='PASS_EXPECTED_OBSERVATIONS'
finally:
 for p in nodes:
  for n in p.nodes:
   try:p.close(n)
   except Exception:pass
 if proc and proc.poll() is None:
  try:rpc('stop');proc.wait(timeout=15)
  except Exception:proc.terminate();proc.wait(timeout=10)
 result['rpc_funding_calls']=calls
 (D/'native-result.json').write_text(json.dumps(result,indent=2,default=str)+'\n')
