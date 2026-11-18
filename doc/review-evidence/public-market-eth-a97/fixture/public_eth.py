"""One disposable native public BTX->ETH settlement/restart receipt; no builds."""
import base64
import importlib.util
import json
import os
from pathlib import Path
import platform
import secrets
import signal
import stat
import subprocess
import sys
import time
from urllib.request import Request, urlopen

P = Path(__file__).resolve().parent
M = json.loads((P / 'manifest.json').read_text())
sys.path.insert(0, M['source_package'])
sys.path.insert(0, str(P))
import btc_helpers as g
from evm_verify import verify_evm_leg
from swapnet.evm import keccak256

PIN = 'a06e30bad714ff02db5a2401a898bd7194d1c475b61bdab312ae194b1509e45d'
FLAGS = ('-autoshieldcoinbase=0', '-regtestmatmulbindingheight=2147483647',
         '-regtestmatmulproductdigestheight=2147483647', '-regtestmatmulv4height=2147483647',
         '-regtestmatmulrequireproductpayload=0', '-dbcache=16', '-par=1')
ANVIL = None
ETH_URL = None


def eth(method, *params):
    req = Request(ETH_URL, json.dumps({'jsonrpc':'2.0','id':1,'method':method,'params':params}).encode(),
                  {'Content-Type':'application/json'})
    with urlopen(req, timeout=10) as f:
        reply = json.load(f)
    if reply.get('error'):
        raise RuntimeError('Anvil.' + method + ': ' + str(reply['error']))
    return reply['result']


def ethmine(count=8):
    for _ in range(count):
        eth('evm_mine')


def receipt(txid):
    def ready():
        r = eth('eth_getTransactionReceipt', txid)
        if r:
            assert int(r['status'], 16) == 1
            return r
    return g.until(ready, 15)


class Node(g.Node):
    def start(self, suffix, *args):
        super().start(suffix, *args)
        if '-swapnet=1' in args:
            info = self.rpc('getsharedp2pinfo')
            assert info == {'available':True,'network':g.BTX,'wallet_authority':False}, info
            sockets = [p for p in self.data.rglob('*.sock') if stat.S_ISSOCK(p.stat().st_mode)]
            assert sockets, 'Expected real shared control socket, not an unavailable adapter'
            log = (g.OUT / f'{self.name}-{suffix}.log').read_text(errors='replace')
            assert 'shared control plane did not start' not in log
            g.result.setdefault('shared_control_startups', []).append({
                'node':self.name,'stage':suffix,'status':info,
                'sockets':[str(p.relative_to(g.ROOT)) for p in sockets]})


def view(n, sid):
    return next((s for s in n.rpc('listswaps')['swaps'] if s['swap_id'] == sid), {})


def ops(n, sid):
    return n.rpc('listswapoperations', {'swap_id':sid})['operations']


def funds(n, sid):
    return [o for o in ops(n, sid) if o['kind'] == 'fund']


def ethbalances(accounts):
    return {k:int(eth('eth_getBalance', v, 'latest'), 16) for k,v in accounts.items()}


def run():
    global ANVIL, ETH_URL
    g.save('initialize native Anvil and two fresh BTX regtest wallets')
    assigned = g.ports(5)
    ETH_URL = 'http://127.0.0.1:' + str(assigned[4])
    with (g.OUT / 'anvil.log').open('wb') as f:
        ANVIL = subprocess.Popen([M['anvil']['path'], '--host','127.0.0.1','--port',str(assigned[4]),
                                  '--slots-in-an-epoch','1','--quiet'], stdout=f, stderr=f)
    def ready():
        assert ANVIL.poll() is None, 'Anvil exited before readiness'
        try:
            return int(eth('eth_chainId'), 16) == 31337
        except OSError:
            return False
    assert g.until(ready, 15)
    a = Node('a', Path(M['btx']['path']), g.BTX, assigned[:2])
    b = Node('b', Path(M['btx']['path']), g.BTX, assigned[2:4])
    for n in (a,b):
        n.start('setup','-swapnet=0',*FLAGS)
        assert n.rpc('createwallet','trader')['name'] == 'trader'
    a.rpc('createwallet','miner')
    sink = a.rpc('getnewaddress','','p2mr',wallet='miner')
    a.rpc('unloadwallet','miner',False)
    g.connected(a,b)
    a.mine(3,a.wallet('getnewaddress','','p2mr'))
    a.mine(105,sink)
    g.synced(a,b)
    for n in (a,b):
        n.stop()
        n.start('market','-swapnet=1','-wallet=trader','-swapnetwallet=trader',*FLAGS)
        assert n.rpc('listwallets') == ['trader']
    g.connected(a,b)
    g.until(lambda:all(n.rpc('getswapbootstrapinfo')['admitted_peers'] == 1 for n in (a,b)),40)
    artifact = json.loads(Path(M['contract']['path']).read_text())
    creation = bytes.fromhex(artifact['bytecode']['object'].removeprefix('0x'))
    runtime = bytes.fromhex(artifact['deployedBytecode']['object'].removeprefix('0x'))
    assert keccak256(creation).hex() == '401e81e4ab795f39e48b76bda608771e10078e23cfc1d807983b05ee3da97cde'
    assert keccak256(runtime).hex() == PIN
    deployer = eth('eth_accounts')[0]
    deployed = receipt(eth('eth_sendTransaction', {'from':deployer,'data':'0x'+creation.hex(),'gas':'0x600000'}))
    contract = deployed['contractAddress']
    assert keccak256(bytes.fromhex(eth('eth_getCode',contract,'latest')[2:])).hex() == PIN
    genesis = eth('eth_getBlockByNumber','0x0',False)['hash'][2:]
    eid = f'evm:{genesis}:31337:native'
    accounts = {}
    for n in (a,b):
        n.rpc('setswapassetpolicy', {'policy':{'asset':eid,'rpc_url':ETH_URL,'contract':contract,'runtime_hash':PIN}})
        assert {v['asset'] for v in n.rpc('listswapassets')['assets'] if v['ready']} == {g.BTX_ID,eid}
        info = n.rpc('getswapwalletinfo')
        accounts[n.name] = next(v['address'] for v in info['foreign_accounts'] if v['asset'] == eid)
        eth('anvil_setBalance',accounts[n.name],hex(10**21))
    assert len(set(accounts.values())) == 2
    ethmine()
    before_btx = {n.name:g.balance(n) for n in (a,b)}
    before_eth = ethbalances(accounts)
    assert before_btx['a'] >= 10_000_000 and before_btx['b'] == 0
    assert set(before_eth.values()) == {10**21}
    g.result.update(evm={'asset':eid,'contract':contract,'runtime_hash':PIN,'deployment':deployed['transactionHash']},
                    before_btx_atoms=before_btx,before_eth_wei={k:str(v) for k,v in before_eth.items()})
    g.save('publish exact signed public BTX to ETH offer')
    sell, gross, maker_fee = 10_000_000, 10**16, 10**12
    local_cap, eth_cap, eth_recovery, btx_recovery = 500_000, 6*10**15, 2*10**15, 100_000
    assert a.rpc('getswapmode')['mode'] == 'taker'
    assert a.rpc('getswapmode')['automatic_spend_atoms'] == '0'
    assert a.rpc('listswapmandates')['mandates'] == []
    b.rpc('setswapmode', {'mode':'maker'})
    maker = b.rpc('createswapmandate', {'mandate':{'principal':b.rpc('getswapauthinfo')['principal'],
        'asset':eid,'max_total_atoms':str(5*10**16),'max_trade_atoms':str(2*10**16),
        'max_fee_atoms':str(eth_cap),'expires_at':int(time.time())+900,'nonce':secrets.token_hex(32)}})['mandate_id']
    b.rpc('setswapmarket', {'market':{'sell_asset':g.BTX_ID,'buy_asset':eid,'numerator':str(10**9),
        'denominator':'1','maker_fee_atoms':str(maker_fee),'max_receive_network_fee_atoms':str(eth_recovery),
        'max_input_atoms':str(sell*2),'expires_at':int(time.time())+600},'mandate_id':maker,
        'max_local_fee_atoms':str(eth_cap),'refund_fee_atoms':str(eth_recovery),'claim_fee_atoms':str(btx_recovery)})
    published = b.rpc('publishswapoffer', {'sell_asset':g.BTX_ID,'buy_asset':eid,'sizes':[str(sell)],'kind':'firm','slots':1,'ttl':300})
    offer = published['offer']['body']
    assert published['advertised'] is True and published['remote_liquidity_guaranteed'] is False
    assert offer['network'] == g.BTX and offer['sell_asset'] == g.BTX_ID and offer['buy_asset'] == eid
    assert len(offer['tiers']) == 1 and offer['tiers'][0]['sell_atoms'] == str(sell) and offer['tiers'][0]['buy_atoms'] == str(gross)
    def capacity():
        return [r for r in b.rpc('getswapmakercapacity')['slots'] if r['offer_id'] == offer['offer_id']]
    def slot(state):
        assert capacity() == [{'offer_id':offer['offer_id'],'tier':0,'state':state,'count':1}]
    slot('available')
    def discovered():
        return next((r for r in a.rpc('listswappublicoffers', {'sell_asset':g.BTX_ID,'buy_asset':eid})['offers']
                     if r['body']['offer_id'] == offer['offer_id'] and r['body']['provider'] == offer['provider']),None)
    assert g.until(discovered,40) == published['offer']
    request = a.rpc('requestpublicswapquote', {'provider':offer['provider'],'offer_id':offer['offer_id'],'tier':0})
    assert request['spending_authority'] is False
    def quoted():
        r = a.rpc('getswapquotes', {'request_id':request['request_id']})
        assert not r.get('declined'), r.get('declined')
        return r['quotes']
    quotes = g.until(quoted,40)
    assert len(quotes) == 1
    q = quotes[0]
    assert (q['sell_asset'],q['buy_asset'],q['sell_atoms'],q['buy_atoms']) == (g.BTX_ID,eid,str(sell),str(gross))
    assert q['provider'] == offer['provider'] and q['maker_fee_atoms'] == str(maker_fee) and q['max_receive_network_fee_atoms'] == str(eth_recovery)
    slot('quoted')
    locks = {n.name:n.wallet('listlockunspent') for n in (a,b)}
    pools = {n.name:n.rpc('getrawmempool') for n in (a,b)}
    assert all(not p for p in pools.values())
    before_pending = {v:eth('eth_getTransactionCount',v,'pending') for v in accounts.values()}
    floor = gross-maker_fee-eth_recovery
    preview = a.rpc('previewswap', {'quote_id':q['id'],'max_local_fee_atoms':str(local_cap),
        'refund_fee_atoms':str(btx_recovery),'claim_fee_atoms':str(eth_recovery),'min_receive_atoms':str(floor)})
    assert preview['requires_owner_confirmation'] is True and preview['funds_reserved'] is False
    assert (preview['sell_asset'],preview['buy_asset'],preview['sell_atoms']) == (g.BTX_ID,eid,str(sell))
    assert preview['maximum_send_atoms'] == str(sell+local_cap)
    assert preview['minimum_receive_atoms'] == preview['net_receive_floor_atoms'] == str(floor)
    assert preview['max_local_fee_atoms'] == str(local_cap) and preview['refund_fee_atoms'] == str(btx_recovery) and preview['claim_fee_atoms'] == str(eth_recovery)
    assert preview['provider'] == q['provider'] and int(time.time()) < preview['expires_at'] <= q['expires_at']
    assert a.rpc('listswapmandates')['mandates'] == []
    assert all(n.rpc('listswaps')['swaps'] == [] for n in (a,b))
    assert {n.name:g.balance(n) for n in (a,b)} == before_btx
    assert ethbalances(accounts) == before_eth
    assert {v:eth('eth_getTransactionCount',v,'pending') for v in accounts.values()} == before_pending
    assert {n.name:n.wallet('listlockunspent') for n in (a,b)} == locks
    assert {n.name:n.rpc('getrawmempool') for n in (a,b)} == pools
    g.save('owner confirms one public trade; wait for original BTX funding')
    sid = a.rpc('confirmswap', {'preview_id':preview['preview_id']})['swap_id']
    assert a.rpc('confirmswap', {'preview_id':preview['preview_id']})['swap_id'] == sid
    mandates = a.rpc('listswapmandates')['mandates']
    assert len(mandates) == 1
    taker = mandates[0]['id']
    assert mandates[0]['mandate']['max_total_atoms'] == str(sell+local_cap)
    assert mandates[0]['mandate']['max_trade_atoms'] == str(sell)
    assert mandates[0]['mandate']['max_fee_atoms'] == str(local_cap)
    funded = g.until(lambda:(v if (v:=view(a,sid)).get('funding_broadcast') else None),45)
    ref = funded['refs']['a']
    assert funded['recovery_ready'] and not funded['secret_exposed']
    assert a.rpc('getswaprecoveryinfo', {'swap_id':sid})['refund_transaction_ready']
    assert [o['txid'] for o in funds(a,sid)] == [ref['txid']]
    assert view(b,sid) and not funds(b,sid)
    slot('reserved')
    assert a.rpc('gettxout',ref['txid'],ref['vout'],True)['confirmations'] == 0
    a.mine(1,sink)
    g.synced(a,b)
    assert a.rpc('gettxout',ref['txid'],ref['vout'],False)['confirmations'] == 1
    g.result.update(swap_id=sid,public_entry={'offer_id':offer['offer_id'],'quote_id':q['id'],
        'preview_id':preview['preview_id'],'preview_nonfunding_verified':True,'confirmation_retry_same_swap':True,
        'signed_offer_native_arrival':True,'maker_slot_transferred_once':True},original_btx_funding=ref)
    g.save('restart both funded nodes before counterparty funding')
    for n in (a,b):
        n.stop()
    for n in (a,b):
        n.start('funded-restart','-swapnet=1','-wallet=trader','-swapnetwallet=trader',*FLAGS)
        assert n.rpc('getswapmode')['mode'] == ('taker' if n is a else 'maker')
        assert not n.rpc('getswapwalletinfo')['startup_errors']
        assert next(v['address'] for v in n.rpc('getswapwalletinfo')['foreign_accounts'] if v['asset'] == eid) == accounts[n.name]
    assert view(a,sid)['refs']['a'] == ref
    assert a.rpc('confirmswap', {'preview_id':preview['preview_id']})['swap_id'] == sid
    assert [v['id'] for v in a.rpc('listswapmandates')['mandates']] == [taker]
    assert [o['txid'] for o in funds(a,sid)] == [ref['txid']]
    slot('reserved')
    g.connected(a,b)
    g.until(lambda:all(n.rpc('getswapbootstrapinfo')['admitted_peers'] == 1 for n in (a,b)),40)
    a.mine(19,sink)
    g.synced(a,b)
    g.save('observe native public Ethereum settlement and actual withdrawal')
    deadline = time.monotonic()+180
    while time.monotonic() < deadline:
        states = {n.name:view(n,sid) for n in (a,b)}
        summary = {k:{f:v.get(f) for f in ['stage','last_error','last_action','refs']} for k,v in states.items()}
        if summary != g.result.get('last_states'):
            g.result['last_states'] = summary
            g.save('observe native public Ethereum settlement and actual withdrawal')
        assert all(v.get('stage') not in ('cancelled','refunded','rejected') for v in states.values())
        if all(v.get('stage') == 'complete' for v in states.values()):
            break
        ethmine()
        if a.rpc('getrawmempool'):
            a.mine(20,sink)
            g.synced(a,b)
        time.sleep(.5)
    else:
        raise TimeoutError('public Ethereum settlement did not finish in180s')
    left,right = (view(n,sid) for n in (a,b))
    assert left['agreement'] == right['agreement']
    assert left['refs']['a'] == ref
    allops = ops(a,sid)+ops(b,sid)
    native = g.check_leg(left['agreement']['long_leg'],ref,allops,a,b,local_cap)
    evm = verify_evm_leg(eth,left['agreement']['short_leg'],left['refs']['b'],allops)
    assert native['locked_atoms'] == sell
    assert evm['runtime_hash'] == PIN and int(evm['amount_wei']) == gross-maker_fee
    assert evm['remaining_credit_wei'] == '0'
    assert int(evm['funding_fee_wei'])+eth_recovery <= eth_cap
    assert native['funding_fee_atoms']+btx_recovery <= local_cap
    assert len(funds(a,sid)) == len(funds(b,sid)) == 1
    assert len([v for v in allops if v['asset'] == eid and v['kind'] == 'withdraw']) == 1
    after_btx = {n.name:g.balance(n) for n in (a,b)}
    after_eth = ethbalances(accounts)
    actual_btx = {k:after_btx[k]-before_btx[k] for k in before_btx}
    actual_eth = {k:after_eth[k]-before_eth[k] for k in before_eth}
    assert actual_btx == {'a':-sell-native['funding_fee_atoms'],'b':native['paid_atoms']}
    assert actual_eth == {'a':gross-maker_fee-int(evm['settlement_fee_wei'])-int(evm['withdrawal_fee_wei']),
                          'b':-(gross-maker_fee)-int(evm['funding_fee_wei'])}
    assert int(eth('eth_getBalance',contract,'latest'),16) == 0
    for n in (a,b):
        assert n.wallet('listlockunspent') == []
    terminal_ops = {n.name:ops(n,sid) for n in (a,b)}
    terminal_budgets = {n.name:n.rpc('listswapmandates')['mandates'] for n in (a,b)}
    assert all(row['held_atoms'] == '0' for rows in terminal_budgets.values() for row in rows)
    terminal_slot = capacity()
    assert all(v['state'] == 'reserved' for v in terminal_slot), 'Historical consumed slot must not become newly spendable capacity'
    g.save('verify terminal restart preserves exact operations and accounting')
    for n in (a,b):
        n.stop()
    for n in (a,b):
        n.start('terminal-restart','-swapnet=1','-wallet=trader','-swapnetwallet=trader',*FLAGS)
        assert view(n,sid)['stage'] == 'complete'
        assert ops(n,sid) == terminal_ops[n.name]
        assert n.rpc('listswapmandates')['mandates'] == terminal_budgets[n.name]
        assert n.wallet('listlockunspent') == []
    assert capacity() == terminal_slot
    assert {n.name:g.balance(n) for n in (a,b)} == after_btx
    assert ethbalances(accounts) == after_eth
    assert int(eth('eth_getBalance',contract,'latest'),16) == 0
    g.result.update(native_settlement=native,evm_settlement=evm,
        actual_btx_delta_atoms=actual_btx,actual_eth_delta_wei={k:str(v) for k,v in actual_eth.items()},
        terminal_budget_rows=terminal_budgets,terminal_slot_history=terminal_slot,
        funded_restart_preserved=True,terminal_restart_preserved=True,all_held_budgets_zero=True,
        original_funding_once=True,withdrawal_once=True,contract_balance_wei='0')


def main():
    global ANVIL
    assert os.environ.get('BTX_PUBLIC_ETH_EXECUTE') == 'disposable-regtest-only'
    assert platform.system() == 'Darwin' and platform.machine() == 'arm64'
    root = Path(sys.argv[1]).resolve()
    assert root == Path(os.environ['BTX_PUBLIC_ETH_ROOT']).resolve()
    assert root.parent == Path('/private/tmp') and root.name.startswith('se-')
    assert root.is_dir() and not any(root.iterdir())
    g.ROOT = root
    g.OUT = Path(os.environ['BTX_PUBLIC_ETH_RECORDS']).resolve()
    assert g.OUT.is_relative_to(P.parent/'execution')
    g.OUT.mkdir(parents=True,exist_ok=False)
    g.TEST_HOME = root/'home'
    g.TEST_HOME.mkdir(mode=0o700)
    os.environ['HOME'] = str(g.TEST_HOME)
    g.FIXTURE_EPOCH = int(time.time())-1800
    g.MANIFEST = M
    g.result.update(status='INCOMPLETE',source=M['source'],case='public-btx-eth-restart',profile=M['profile'])
    for role in ['btx','anvil','contract']:
        assert g.sha(Path(M[role]['path'])) == M[role]['sha256']
    signal.signal(signal.SIGTERM,lambda *_:(_ for _ in ()).throw(TimeoutError('outer execution interrupted')))
    try:
        run()
    except Exception as e:
        g.result.update(status='FAIL',error=type(e).__name__+': '+str(e))
        g.save(g.result.get('stage','initialization'))
        raise
    finally:
        errors = []
        for n in reversed(g.nodes):
            try:
                n.stop()
            except Exception as e:
                errors.append(n.name+': '+type(e).__name__)
        if ANVIL is not None:
            if ANVIL.poll() is None:
                ANVIL.terminate()
            try:
                ANVIL.wait(timeout=10)
            except subprocess.TimeoutExpired:
                ANVIL.kill(); ANVIL.wait(timeout=10)
            if ANVIL.returncode not in (0,-15):
                errors.append('Anvil exit '+str(ANVIL.returncode))
        g.result['cleanup_errors'] = errors
        g.result['anvil_exited'] = ANVIL is None or ANVIL.poll() is not None
        g.save(g.result.get('stage','initialization'))
        if errors:
            raise RuntimeError('cleanup failed: '+str(errors))
    g.result['status'] = 'PASS'
    g.save('public BTX to ETH settlement withdrawal and restarts verified')


if __name__ == '__main__':
    main()
