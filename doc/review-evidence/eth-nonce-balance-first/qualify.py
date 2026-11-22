"""Run the retained two-party fixture through the pinned ETH preparation path."""
from dataclasses import asdict
import json
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

import test_execution_v2 as fixture
from swapnet.authorization import Principal
from swapnet.canonical import digest
from swapnet.errors import SwapError
from swapnet.evm import Eip1559Transaction, keccak256
from swapnet.evm_driver import EVMDriver
from swapnet.policy import Mandate
from swapnet.quote import Quote
from swapnet.terms import Agreement

BTX = fixture.A
GENESIS = 'ee' * 32
ETH = f'evm:{GENESIS}:31337:native'
fixture.A, fixture.B = ETH, BTX
OWNER = Principal('alice')
TOPUP = 10**12
CAP = '200000'
PATCHED = sys.argv[1] == 'candidate'

class EthRPC:
    def __init__(self, clock):
        self.clock = clock
        self.balance = TOPUP
        self.pending = 0
        self.broadcasts = []
        self.fail_balance_read = False
        self.gas_estimate = 21000

    def __call__(self, method, *args):
        if method == 'eth_getBlockByNumber':
            if args[0] == '0x0':
                return {'hash': '0x' + GENESIS}
            return {'hash':'0x'+'12'*32,'number':'0x10',
                    'timestamp':hex(self.clock()),'baseFeePerGas':'0x1'}
        if method == 'eth_getBalance':
            if self.fail_balance_read:
                raise SwapError('RPC_UNAVAILABLE','scripted balance read error')
            return hex(self.balance)
        if method == 'eth_getTransactionCount':
            return hex(self.pending)
        if method == 'eth_sendRawTransaction':
            txid = '0x' + keccak256(bytes.fromhex(args[0][2:])).hex()
            self.broadcasts.append(txid)
            return txid
        answers = {'eth_chainId':'0x7a69','eth_getCode':'0x01','eth_syncing':False,
                   'eth_call':'0x'+'00'*224,'eth_estimateGas':hex(self.gas_estimate),
                   'eth_maxPriorityFeePerGas':'0x1','eth_getTransactionByHash':None,
                   'eth_getTransactionReceipt':None}
        return answers[method]

class Pair(fixture.Pair):
    def __init__(self, path):
        self.rpc = {}
        super().__init__(path)

    def open(self, name):
        super().open(name)
        _, journal, _, coordinator = self.nodes[name]
        rpc = self.rpc.setdefault(name, EthRPC(self.time))
        coordinator.drivers[ETH] = EVMDriver(ETH, rpc, journal, coordinator.vault,
                                             '0x'+'44'*20, keccak256(b'\x01').hex(),
                                             clock=self.time)

    def commit_swap(self, n):
        ids = {}
        for name, asset in [('alice', ETH), ('bob', BTX)]:
            mandate = Mandate(name,asset,'10000000','1000000','500000',
                              self.time()+100000,f'{n+16:02x}'*32)
            ids[name] = self.nodes[name][2].install(Principal(name,True),asdict(mandate))
        nonce = f'{n:02x}'*32
        requester = digest('BTX/SWAPNET/REQUESTER/2',{'identity':'alice','nonce':nonce})
        rfq = dict(network=fixture.NETWORK, requester=requester, sell_asset=ETH,
                   buy_asset=BTX,sell_atoms='10000',nonce=nonce,issued_at=self.time(),
                   expires_at=self.time()+120)
        q = Quote(fixture.NETWORK,'bob',requester,f'{n+32:02x}'*32,n,ETH,BTX,'10000',
                  '20000','10','100',self.time(),self.time()+120)
        env = {'quote':asdict(q),'signature':self.identities['bob'].sign(q.signing_message)}
        self.market = {'principal':'bob','wallet':'','mandate_id':ids['bob'],
                       'max_local_fee_atoms':'500','refund_fee_atoms':'100','claim_fee_atoms':'100',
                       'market':{'sell_asset':ETH,'buy_asset':BTX,'numerator':'2','denominator':'1',
                                 'maker_fee_atoms':'10','max_receive_network_fee_atoms':'100',
                                 'max_input_atoms':'100000','expires_at':self.time()+10000}}
        sid = self.nodes['alice'][3].start(OWNER,env,rfq,ids['alice'],CAP,'100000')['swap_id']
        self.deliver()
        assert self.nodes['alice'][1].load(sid)[1]['stage']=='committed'
        return sid

    def action(self, sid, name):
        _, journal, _, c = self.nodes['alice']
        rev,state = journal.load(sid)
        getattr(c,name)(sid,state,rev,Agreement.parse(state['agreement']))

    def snapshot(self,sid):
        store,journal,_,c=self.nodes['alice']
        view=c.get(OWNER,sid)
        account=c.drivers[ETH]._account()[2]
        rows=store.db.execute('SELECT nonce,operation FROM sn_nonces WHERE asset=? AND address=? ORDER BY nonce',(ETH,account)).fetchall()
        return dict(stage=view['stage'],nonce_rows=rows,pending_nonce=self.rpc['alice'].pending,
                    operations=[{k:o[k] for k in ('txid','state','kind')} for o in journal.operations(sid)])

def refuses(code, fn):
    try:fn()
    except SwapError as e:
        assert e.code==code,(e.code,str(e))
        return e.code
    raise AssertionError(f'Expected {code}')

def run(kind):
    with TemporaryDirectory(prefix='nonce-check-') as tmp:
        pair=Pair(Path(tmp))
        rpc=pair.rpc['alice']
        signed=[]
        original_sign=Eip1559Transaction.sign
        def sign(tx,*args,**kwargs):
            signed.append(tx.nonce)
            return original_sign(tx,*args,**kwargs)
        try:
            with patch.object(Eip1559Transaction,'sign',sign):
                first=pair.commit_swap(1)
                if kind=='pending':
                    pair.action(first,'_prepare')
                    pair.action(first,'_fund')
                    rpc.pending=1
                    durable = pair.nodes['alice'][1].operations(first,private=True)
                    before=pair.snapshot(first)
                    assert len(before['operations'])==1 and before['operations'][0]['state']=='broadcast'
                    assert signed==[0] and rpc.broadcasts==[before['operations'][0]['txid']]
                    c=pair.nodes['alice'][3]
                    refused=refuses('FUNDS_LOCKED',lambda:c.cancel(OWNER,first))
                    pair.restart('alice')
                    assert pair.snapshot(first)==before
                    # Model delayed peer notification while the first transaction
                    # is pending. The durable operation and chain reply stay intact.
                    deferred = list(pair.queue)
                    assert deferred and all(msg[2] == 'funded' for msg in deferred)
                    pair.queue.clear()
                    second=pair.commit_swap(2)
                    pair.queue.extend(deferred)
                    rpc.pending=0
                    held=refuses('NONCE_HELD',lambda:pair.action(second,'_prepare'))
                    assert pair.snapshot(first)['operations']==before['operations']
                    assert signed==[0] and len(rpc.broadcasts)==1
                    rpc.pending=1
                    pair.action(second,'_prepare')
                    after=pair.snapshot(second)
                    assert signed==[0,1] and len(rpc.broadcasts)==1
                    assert pair.snapshot(first)['operations']==before['operations']
                    assert [row[0] for row in after['nonce_rows']]==[0,1]
                    assert pair.nodes['alice'][1].operations(first,private=True)==durable
                    return dict(before=before,cancel=refused,stale_pending_nonce_error=held,next_payment=after,signed_nonces=signed,
                                broadcast_count=len(rpc.broadcasts))
                if kind in ('balance_read', 'fee_cap'):
                    rpc.fail_balance_read = kind=='balance_read'
                    rpc.gas_estimate = 10**6 if kind=='fee_cap' else 21000
                    code = 'RPC_UNAVAILABLE' if kind=='balance_read' else 'FEE_CAP'
                    failure=refuses(code,lambda:pair.action(first,'_prepare'))
                    state=pair.snapshot(first)
                    assert len(state['nonce_rows'])==int(kind=='balance_read' and not PATCHED)
                    assert not state['operations'] and not signed and not rpc.broadcasts
                    return dict(error=failure,state=state,signed_nonces=signed,broadcast_count=0)
                rpc.balance=0
                failure=refuses('INSUFFICIENT_GAS',lambda:pair.action(first,'_prepare'))
                before=pair.snapshot(first)
                assert [row[0] for row in before['nonce_rows']]==([] if PATCHED else [0])
                assert not before['operations'] and not signed and not rpc.broadcasts
                budget_after_cancel=None
                if kind=='distinct':
                    c=pair.nodes['alice'][3]
                    assert c.cancel(OWNER,first)['stage']=='cancelled'
                    store=pair.nodes['alice'][0]
                    budget_after_cancel=sum(int(row[0]) for row in store.db.execute('SELECT held FROM mandates'))
                    assert budget_after_cancel==0
                closed=pair.snapshot(first)
                pair.restart('alice')
                assert pair.snapshot(first)==closed
                rpc.balance=TOPUP
                if kind=='same':
                    pair.action(first,'_prepare')
                    after=pair.snapshot(first)
                    assert [row[0] for row in after['nonce_rows']]==[0] and after['stage']=='prepared'
                    if not PATCHED:
                        assert after['nonce_rows']==before['nonce_rows']
                    assert signed==[0] and not rpc.broadcasts
                    return dict(first_error=failure,before=before,after_retry=after,signed_nonces=signed,broadcast_count=0)
                second=pair.commit_swap(2)
                if PATCHED:
                    pair.action(second,'_prepare')
                    after=pair.snapshot(second)
                    assert [row[0] for row in after['nonce_rows']]==[0] and after['stage']=='prepared'
                    assert signed==[0] and len(after['operations'])==1
                    pair.action(second,'_fund')
                    after=pair.snapshot(second)
                    assert signed==[0] and rpc.broadcasts==[after['operations'][0]['txid']]
                    assert after['operations'][0]['state']=='broadcast'
                    assert not pair.snapshot(first)['operations']
                    blocked=None
                else:
                    blocked=refuses('NONCE_HELD',lambda:pair.action(second,'_prepare'))
                    after=pair.snapshot(second)
                    assert after['nonce_rows']==before['nonce_rows'] and not after['operations']
                    assert not signed and not rpc.broadcasts
                return dict(first_error=failure,before=before,after_cancel_and_reopen=closed,
                            held_after_cancel=budget_after_cancel,next_payment=after,
                            next_error=blocked,signed_nonces=signed,broadcast_count=len(rpc.broadcasts))
        finally:
            for name in pair.nodes:
                pair.close(name)

print(json.dumps({kind:run(kind) for kind in ('same','distinct','pending','balance_read','fee_cap')},indent=2))
