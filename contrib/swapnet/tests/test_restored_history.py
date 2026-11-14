from decimal import Decimal
from types import SimpleNamespace
import pytest
from test_execution_v2 import pair,A
from test_funding_scan_and_capacity import Chain,TXID,OTHER,AdoptingDriver
from swapnet.funding_scan import find_funding_output
from swapnet.errors import SwapError
from swapnet.drivers import UTXODriver
from swapnet.journal import Journal
from swapnet.store import Store
from swapnet.recovery import export_bundle,restore_bundle
from swapnet.vault import atomic_private_write

class History(Chain):
 def __init__(self,mode):super().__init__('aa','10000');self.mode=mode;self.history_calls=0
 def wallet(self,m,*a):
  if m=='getwalletinfo':return {'txcount':2,'scanning':False}
  if m=='listtransactions':
   self.history_calls+=1
   if self.mode=='missing':raise SwapError('CHAIN_RPC','missing history')
   if self.mode=='incomplete':return [{'txid':TXID}]*100
   if self.mode=='empty':return []
   return [{'txid':TXID}]+([{'txid':OTHER}] if self.mode=='ambiguous' else [])
  if m=='gettransaction':return {'txid':a[0],'hex':'ee' if a[0]==TXID else 'ff','confirmations':2,'blockhash':'block'}
  return super().wallet(m,*a)
 def rpc(self,m,*a):
  if m=='getbestblockhash':return 'tip'
  if m=='getblockheader':return {'confirmations':2}
  if m=='decoderawtransaction':return {'txid':TXID if a[0]=='ee' else OTHER,'vout':[{'n':0,'scriptPubKey':{'hex':self.script},'value':self.coin}]}
  return super().rpc(m,*a)
class Probe(AdoptingDriver):
 def prepare_funding(self,*a,**kw):self.funding_calls+=1;return self.inner.prepare_funding(*a,**kw)
 def broadcast(self,raw):return self.inner.broadcast(raw)
def setup(p,mode,restored=True):
 p.start();p.deliver();c=p.nodes['alice'][3];h=History(mode);leg=p.state('alice')['agreement']['long_leg'];h.script=leg['lock_commitment'];h.coin=Decimal(leg['amount_atoms'])/100000000;d=Probe(c.drivers[A],h);c.drivers[A]=d
 if restored:p.nodes['alice'][1].set_setting('restored_session:'+p.sid,True)
 # Test fixture leg uses BTX identity. Recovery gate is Bitcoin-specific; expose
 # BTC family on wrapper, retain simulated clock/signing as component controls.
 d.asset=type(d.asset).parse('btc:'+('22'*32)+':0:native')
 return c,d,h
@pytest.mark.parametrize('mode',['missing','incomplete','ambiguous','empty'])
def test_restored_history_refuses_fresh_funding(pair,mode):
 c,d,h=setup(pair,mode)
 try:c.tick_one(pair.sid);c.tick_one(pair.sid)
 except SwapError:pass
 assert d.funding_calls==0
 assert not pair.state('alice')['funding_broadcast']
 assert h.history_calls>0

def test_fresh_funding(pair):
 c,d,h=setup(pair,'missing',False);c.tick_one(pair.sid);c.tick_one(pair.sid)
 assert d.funding_calls==1 and pair.state('alice')['funding_broadcast'] and h.history_calls==0

def test_spent_history_adopts_no_funding(pair):
 c,d,h=setup(pair,'unique');c.tick_one(pair.sid);c.tick_one(pair.sid)
 assert d.funding_calls==0 and pair.state('alice')['refs']['a']=={'txid':TXID,'vout':0}
 assert pair.state('alice')['funding_broadcast']
 assert not [o for o in pair.nodes['alice'][1].operations(pair.sid) if o['kind']=='fund']

def test_restore_marker_installed_before_publication(pair,tmp_path):
 pair.start();pair.deliver();folder=pair.path/'alice';key=b'0123456789abcdef0123456789abcdef';atomic_private_write(folder/'vault.key',key);pair.nodes['alice'][3].vault.save();(folder/'foreign-vault.json').write_bytes((folder/'vault.json').read_bytes())
 b=export_bundle(pair.nodes['alice'][1],folder,'long independently owned fixture password',pair.identities['alice'].network)
 dest=tmp_path/'imported';restore_bundle(b['path'],dest,'long independently owned fixture password',pair.identities['alice'].network)
 s=Store(dest/'state.sqlite')
 try:assert Journal(s).setting('restored_session:'+pair.sid) is True
 finally:s.close()


def test_signed_wal_reuse(pair):
 from copy import deepcopy
 from swapnet.terms import Agreement
 c,d,h=setup(pair,'missing',False);old=deepcopy(pair.state('alice'));c.tick_one(pair.sid)
 rev,_=pair.nodes['alice'][1].load(pair.sid);pair.nodes['alice'][1].set_setting('restored_session:'+pair.sid,True);h.fail={'scantxoutset'}
 c._prepare(pair.sid,old,rev,Agreement.parse(old['agreement']))
 assert d.funding_calls==1 and h.history_calls==0
 assert len([o for o in pair.nodes['alice'][1].operations(pair.sid) if o['kind']=='fund'])==1

def test_unique_unspent_with_history(pair):
 c,d,h=setup(pair,'unique');h.add(TXID,0)
 c.tick_one(pair.sid);c.tick_one(pair.sid)
 assert d.funding_calls==0 and pair.state('alice')['refs']['a']=={'txid':TXID,'vout':0}

@pytest.mark.parametrize('failure',['scanning','changed_count','changed_tip','bad_page','bad_raw','conflict'])
def test_incomplete_history_never_funds(pair,failure):
 c,d,h=setup(pair,'unique');wallet=h.wallet;rpc=h.rpc;calls=[0];tips=[0]
 def w(m,*a):
  if m=='getwalletinfo':
   calls[0]+=1;return {'txcount':calls[0] if failure=='changed_count' else 2,'scanning':{'duration':1} if failure=='scanning' else False}
  if m=='listtransactions' and failure=='bad_page':return {'transactions':[]}
  if m=='gettransaction' and failure=='bad_raw':return {'txid':a[0],'hex':''}
  if m=='gettransaction' and failure=='conflict':return {**wallet(m,*a),'confirmations':-1}
  return wallet(m,*a)
 def r(m,*a):
  if m=='getbestblockhash' and failure=='changed_tip':tips[0]+=1;return str(tips[0])
  return rpc(m,*a)
 d.wallet=d.watch=w;d.rpc=r
 with pytest.raises(SwapError):c.tick_one(pair.sid)
 assert d.funding_calls==0
