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
root=Path(sys.argv[1]);root.mkdir(mode=0o700,parents=True);mode='pending-recovery'
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
mine(3)
genesis=rpc('eth_getBlockByNumber','0x0',False)['hash'][2:];chain=int(rpc('eth_chainId'),16)
te.A='evm:'+genesis+':'+str(chain)+':native';te.B='btx:'+te.NETWORK+':0:native';mc.A=te.A;mc.B=te.B
class NativePair(te.Pair):
 def open(self,n):
  folder=self.path/n;folder.mkdir(mode=0o700,exist_ok=True)
  from swapnet.vault import atomic_private_write
  if not (folder/'vault.key').exists():atomic_private_write(folder/'vault.key',b'0123456789abcdef0123456789abcdef')
  st=Store(folder/'state.sqlite');j=Journal(st);auth=Authority(st,j,self.time);v=ForeignKeyVault(folder/'foreign-vault.json',(folder/'vault.key').read_bytes());v.save()
  evm=EVMDriver(te.A,rpc,j,v,contract,runtime,clock=self.time)
  c=Coordinator(j,auth,{te.A:evm,te.B:te.Driver(self.b,n)},self.identities[n],v,lambda peer,kind,sid,body:self.queue.append((n,peer,kind,sid,body)),clock=self.time,policy=SafetyPolicy(btx_confirmations=2,btc_confirmations=2,settlement_margin_seconds=10,reveal_margin_seconds=10));self.nodes[n]=(st,j,auth,c)
from swapnet.authorization import Principal
from swapnet.policy import Mandate
from swapnet.quote import Quote
from swapnet.canonical import digest
from swapnet.recovery import export_bundle,restore_bundle
from swapnet.funding_scan import find_funding_output
import shutil
p=NativePair(root);result={'status':'INCOMPLETE','scope':'actual Anvil/HTLC/EVMDriver/coordinator/export+restore; simulated BTX leg'}
phrase='independent disposable recovery verification password'
def snapshot():
 st,j,_,c=p.nodes['alice'];s=p.state('alice')
 return {'stage':s['stage'],'funding_prepared':s['funding_prepared'],'funding_broadcast':s['funding_broadcast'],'reference':s['refs'].get('a'),'operations':[{k:o[k] for k in ['kind','txid','state']} for o in j.operations(p.sid)],'nonces':st.db.execute('select nonce from sn_nonces').fetchall(),'account':c.drivers[te.A]._account()[2]}
def tick():
 p.time.n=int(rpc('eth_getBlockByNumber','latest',False)['timestamp'],16)
 p.nodes['alice'][3].tick_one(p.sid)
try:
 p.time.n=int(rpc('eth_getBlockByNumber','latest',False)['timestamp'],16)
 ai=p.nodes['alice'][2].install(Principal('alice',True),asdict(Mandate('alice',te.A,str(10**22),str(10**20),str(10**17),p.time()+100000,'33'*32)))
 bi=p.mandate('bob',te.B);now=p.time();rfq={'network':te.NETWORK,'requester':digest('BTX/SWAPNET/REQUESTER/2',{'identity':'alice','nonce':'44'*32}),'sell_asset':te.A,'buy_asset':te.B,'sell_atoms':str(10**18),'nonce':'44'*32,'issued_at':now,'expires_at':now+120}
 q=Quote(te.NETWORK,'bob',rfq['requester'],'55'*32,1,te.A,te.B,str(10**18),'20000','10','100',now,now+120)
 env={'quote':asdict(q),'signature':p.identities['bob'].sign(q.signing_message)}
 p.market={'principal':'bob','wallet':'','mandate_id':bi,'max_local_fee_atoms':'500','refund_fee_atoms':'100','claim_fee_atoms':str(10**16),'market':{'sell_asset':te.A,'buy_asset':te.B,'numerator':'2','denominator':str(10**14),'maker_fee_atoms':'10','max_receive_network_fee_atoms':'100','max_input_atoms':str(10**20),'expires_at':now+100000}}
 p.sid=p.nodes['alice'][3].start(Principal('alice'),env,rfq,ai,str(10**17),str(10**16))['swap_id'];p.deliver()
 driver=p.nodes['alice'][3].drivers[te.A];sender=driver._account()[2];rpc('anvil_setBalance',sender,hex(10**21));balance_before=int(rpc('eth_getBalance',sender,'latest'),16)
 initial=snapshot();assert initial['stage']=='committed' and not initial['operations'] and not initial['nonces'];result['backup_state']=initial
 bundle=export_bundle(p.nodes['alice'][1],p.path/'alice',phrase,te.NETWORK);backup=Path(bundle['path']);result['backup_sha256']=bundle['sha256']
 tick();assert p.state('alice')['stage']=='prepared';original_ref=p.state('alice')['refs']['a'];original_tx=original_ref['txid']
 rpc('evm_setAutomine',False);tick();assert rpc('eth_getTransactionByHash',original_tx)['blockNumber'] is None
 result['original_pending']=snapshot();result['pending_nonce']=int(rpc('eth_getTransactionCount',sender,'pending'),16)
 assert find_funding_output(driver,Agreement.parse(p.state('alice')['agreement']).long_leg,p.sid) is None
 p.close('alice');p.nodes.pop('alice');saved=root/'immutable-backup.snr';shutil.copyfile(backup,saved);dest=root/'restored';dest.mkdir(mode=0o700);restore_bundle(saved,dest/'alice',phrase,te.NETWORK);p.path=dest;p.open('alice')
 result['restored_before_retry']=snapshot();assert result['restored_before_retry']['account']==sender
 try:
  tick();result['retry_prepare']='returned'
  if p.state('alice')['stage']=='prepared':tick()
 except Exception as e:result['retry_prepare_error']={'type':type(e).__name__,'message':str(e)}
 result['restored_after_retry']=snapshot();retry_ref=p.state('alice')['refs'].get('a');result['same_lock_id']=bool(retry_ref and retry_ref.get('lock_id')==original_ref['lock_id'])
 mine();rpc('evm_setAutomine',True)
 txids=list(dict.fromkeys([original_tx]+[o['txid'] for o in p.nodes['alice'][1].operations(p.sid) if o['kind']=='fund']))
 result['funding_receipts']=[]
 for tx in txids:
  rec=rpc('eth_getTransactionReceipt',tx);obj=rpc('eth_getTransactionByHash',tx)
  result['funding_receipts'].append({'txid':tx,'nonce':int(obj['nonce'],16) if obj else None,'receipt':None if not rec else {'status':int(rec['status'],16),'gas_used':int(rec['gasUsed'],16),'gas_cost':int(rec['gasUsed'],16)*int(rec['effectiveGasPrice'],16)}})
 driver=p.nodes['alice'][3].drivers[te.A];terms=Agreement.parse(p.state('alice')['agreement']).long_leg
 result['adoptable_after_mining']=find_funding_output(driver,terms,p.sid)
 if not p.state('alice')['funding_prepared']:tick()
 result['adopted_snapshot']=snapshot();assert result['adopted_snapshot']['reference']==original_ref
 assert not [o for o in p.nodes['alice'][1].operations(p.sid) if o['kind']=='fund'], 'Restore signed a fresh funding transaction'
 p.restart('alice');driver=p.nodes['alice'][3].drivers[te.A]
 result['adopted_reopened_snapshot']=snapshot();assert result['adopted_reopened_snapshot']['reference']==original_ref
 for _ in range(4):mine();p.time.n=int(rpc('eth_getBlockByNumber','latest',False)['timestamp'],16)
 result['state_after_finalization']=snapshot();obs=driver.observe(terms,original_ref).observation;assert obs.present and obs.exact_terms and obs.finalized
 topic='0x'+keccak256(b'Locked(bytes32,bytes32,address,address,address,uint256,uint64)').hex()
 logs=rpc('eth_getLogs',{'address':contract,'fromBlock':'0x0','toBlock':'latest','topics':[topic,'0x'+original_ref['lock_id']]});result['locked_events']=len(logs);assert len(logs)==1
 rpc('evm_setNextBlockTimestamp',terms.lock_value+1);mine();p.time.n=int(rpc('eth_getBlockByNumber','latest',False)['timestamp'],16);p.b.height=p.state('alice')['agreement']['short_leg']['lock_value']+1
 try:
  p.nodes['alice'][3].request_refund(Principal('alice'),p.sid)
  for _ in range(12):
   mine();tick()
   if p.state('alice')['stage']=='refunded':break
  result['refund_stage']=p.state('alice')['stage'];result['refund_observation']=asdict(driver.observe(terms,original_ref).observation)
 except Exception as e:result['refund_error']={'type':type(e).__name__,'message':str(e)}
 assert result.get('refund_stage')=='refunded',result.get('refund_error',result.get('refund_stage'))
 assert result['refund_observation']['refunded'] and result['refund_observation']['finalized']
 result['terminal_snapshot']=snapshot();p.restart('alice');result['reopened_snapshot']=snapshot()
 assert result['reopened_snapshot']['stage']=='refunded'
 assert result['reopened_snapshot']['reference']==original_ref
 result['recovery_receipts']=[]
 for op in p.nodes['alice'][1].operations(p.sid):
  rec=rpc('eth_getTransactionReceipt',op['txid'])
  assert rec and int(rec['status'],16)==1,op['kind']
  result['recovery_receipts'].append({'kind':op['kind'],'txid':op['txid'],'gas_cost':int(rec['gasUsed'],16)*int(rec['effectiveGasPrice'],16)})
 result['original_principal_wei']=int(terms.amount_atoms);result['sender_balance_before']=balance_before;result['sender_balance_after']=int(rpc('eth_getBalance',sender,'latest'),16);result['contract_balance_after']=int(rpc('eth_getBalance',contract,'latest'),16)
 assert result['contract_balance_after']==0,'Escrow still holds the principal'
 gas=sum(x['receipt']['gas_cost'] for x in result['funding_receipts'] if x['receipt'])+sum(x['gas_cost'] for x in result['recovery_receipts'])
 result['total_gas_wei']=gas;result['balance_reconciles']=balance_before-result['sender_balance_after']==gas
 assert result['balance_reconciles'],'Original principal did not return net of exact gas'
 result['status']='MEASUREMENT_COMPLETE'
finally:
 for name in list(p.nodes):p.close(name)
 Path('records').mkdir(exist_ok=True);Path('records/pending-result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result),flush=True)
