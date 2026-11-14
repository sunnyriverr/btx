"""Actual Anvil HTLC and EVMDriver; production coordinator/SQLite; BTX ledger simulated."""
import sys,json,time,subprocess,os
from pathlib import Path
from dataclasses import asdict
from urllib.request import Request,urlopen
import test_execution_v2 as te
import test_maker_terminal_capacity as mc
from swapnet.evm import keccak256,calldata
from swapnet.evm_driver import EVMDriver
from swapnet.store import Store
from swapnet.journal import Journal
from swapnet.authorization import Authority
from swapnet.vault import ForeignKeyVault
from swapnet.coordinator import Coordinator
from swapnet.policy import SafetyPolicy
from swapnet.terms import Agreement
from swapnet.errors import SwapError
root=Path(sys.argv[1]);root.mkdir(mode=0o700,parents=True);mode=sys.argv[2]
def rpc(method,*args):
 with urlopen(Request('http://127.0.0.1:18545',json.dumps({'jsonrpc':'2.0','id':1,'method':method,'params':args}).encode(),{'Content-Type':'application/json'}),timeout=15) as r:d=json.load(r)
 if d.get('error'):raise RuntimeError(d['error'])
 return d['result']
def mine(n=1):
 for _ in range(n):rpc('evm_mine')
def receipt(tx):
 for _ in range(40):
  r=rpc('eth_getTransactionReceipt',tx)
  if r:assert int(r['status'],16)==1,r;return r
  time.sleep(.1)
 raise RuntimeError('missing receipt')
accounts=rpc('eth_accounts');code=json.loads(Path('product/contrib/swapnet/contracts/out/SwapNetHTLC.sol/SwapNetHTLC.json').read_text())['bytecode']['object']
deploy=receipt(rpc('eth_sendTransaction',{'from':accounts[0],'data':code,'gas':'0x600000'}));contract=deploy['contractAddress'];runtime=keccak256(bytes.fromhex(rpc('eth_getCode',contract,'latest')[2:])).hex()
genesis=rpc('eth_getBlockByNumber','0x0',False)['hash'][2:];chain=int(rpc('eth_chainId'),16)
te.A='evm:'+genesis+':'+str(chain)+':native';te.B='btx:'+te.NETWORK+':0:native';mc.A=te.A;mc.B=te.B
class NativePair(te.Pair):
 def open(self,n):
  folder=self.path/n;folder.mkdir(mode=0o700,exist_ok=True);st=Store(folder/'state.db');j=Journal(st);auth=Authority(st,j,self.time);v=ForeignKeyVault(folder/'vault.json',b'0123456789abcdef0123456789abcdef')
  evm=EVMDriver(te.A,rpc,j,v,contract,runtime,clock=self.time)
  c=Coordinator(j,auth,{te.A:evm,te.B:te.Driver(self.b,n)},self.identities[n],v,lambda peer,kind,sid,body:self.queue.append((n,peer,kind,sid,body)),clock=self.time,policy=SafetyPolicy(btx_confirmations=2,btc_confirmations=2,settlement_margin_seconds=10,reveal_margin_seconds=10));self.nodes[n]=(st,j,auth,c)
p=NativePair(root);result={'status':'INCOMPLETE','mode':mode,'scope':'native Anvil/EVMDriver/coordinator/SQLite, simulated BTX ledger; not full embedded daemon swap'}
def account():
 st,j,_,c=p.nodes['bob'];s=p.state('bob');held=st.db.execute('SELECT held FROM mandates WHERE id=(SELECT mandate_id FROM reservations WHERE id=?)',(s['reservation_id'],)).fetchone()[0];grant=st.db.execute('SELECT revoked FROM sn_grants WHERE id=?',(s['grant_id'],)).fetchone()[0]
 return {**mc.maker_state(p),'held':held,'grant_revoked':grant}
try:
 p.time.n=int(rpc('eth_getBlockByNumber','latest',False)['timestamp'],16);p.start();p.deliver();state=p.state('bob');agr=Agreement.parse(state['agreement']);driver=p.nodes['bob'][3].drivers[te.A];ref=driver.reference(p.sid,agr.long_leg,'0x'+'00'*32);sender=agr.long_leg.refund_key
 rpc('anvil_setBalance',sender,hex(10**21));rpc('anvil_impersonateAccount',sender)
 data=driver.adapter.funding_data(ref['salt'],agr.long_leg.hashlock,agr.long_leg.claim_key,agr.long_leg.lock_value)
 tx=rpc('eth_sendTransaction',{'from':sender,'to':contract,'value':hex(int(agr.long_leg.amount_atoms)),'data':'0x'+data.hex(),'gas':'0x80000'});receipt(tx);ref=driver.reference(p.sid,agr.long_leg,tx)
 p.nodes['bob'][3].receive_reference('alice',p.sid,{'agreement_id':agr.id,'leg':'a','reference':ref})
 for _ in range(8):
  mine();p.time.n=int(rpc('eth_getBlockByNumber','latest',False)['timestamp'],16)
  if driver.observe(agr.long_leg,ref).observation.present:break
 assert driver.observe(agr.long_leg,ref).observation.present
 rpc('evm_setNextBlockTimestamp',agr.long_leg.lock_value+1)
 refund=rpc('eth_sendTransaction',{'from':sender,'to':contract,'data':'0x'+calldata('refund(bytes32)',bytes.fromhex(ref['lock_id'])).hex(),'gas':'0x80000'});receipt(refund)
 p.time.n=int(rpc('eth_getBlockByNumber','latest',False)['timestamp'],16);p.b.height=agr.short_leg.lock_value+1;p.market['market']['expires_at']=p.time()+10000
 before=driver.observe(agr.long_leg,ref).observation;result['before_finality']=asdict(before)
 assert not before.refunded,'refund finalized immediately; finality control not reached'
 try:p.nodes['bob'][3].tick_one(p.sid)
 except SwapError as e:assert e.code in {'UNSAFE_TIMEOUT','LATE_REVEAL'},e
 assert account()['reservation']=='held'
 for _ in range(8):
  mine();p.time.n=int(rpc('eth_getBlockByNumber','latest',False)['timestamp'],16)
  obs=driver.observe(agr.long_leg,ref).observation
  if obs.refunded:break
 assert obs.refunded and obs.finalized and obs.exact_terms and obs.canonical
 result['finalized_refund']=asdict(obs)
 if mode=='funded':p.nodes['bob'][1].prepare(p.sid,te.B,'fund','88'*32,'00')
 p.nodes['bob'][3].tick_one(p.sid);result['before_restart']=account();p.restart('bob');p.nodes['bob'][3].tick_one(p.sid);result['after_restart']=account()
 s=result['after_restart']
 if mode=='funded':assert s['reservation']=='held' and int(s['held'])>0 and not s['grant_revoked'] and s['operations']==['fund']
 else:
  assert s['stage']=='cancelled' and s['reservation']=='closed' and s['held']=='0' and s['grant_revoked']==1,s
  st,j,_,c=p.nodes['bob']
  for n in range(1,128):j.save(f'{n:064x}',{'stage':'committed','principal':'fixture','peer':'fixture'})
  sid,proposal=mc.fresh_proposal(p);c.receive_proposal('alice',sid,proposal,p.market);assert j.load(sid)[1]['stage']=='offered';result['fresh_proposal_accepted']=True
 result['status']='PASS'
finally:
 for n in list(p.nodes):p.close(n)
 Path('records').mkdir(exist_ok=True);Path('records/'+root.name+'.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result),flush=True)
