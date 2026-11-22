"""Disposable native regtest run. Evidence omits transaction witnesses and keys."""
import base64
import hashlib
from decimal import Decimal
import json
import os
from pathlib import Path
import secrets
import signal
import socket
import subprocess
import sys
import time
from urllib.error import HTTPError
from urllib.request import Request, urlopen

ROOT = Path(sys.argv[1]).resolve()
OUT = (Path("records") / sys.argv[2]).resolve()
OUT.mkdir(parents=True, exist_ok=True)
BTX = "521ad0951ed299e9c56aeb7db8188972772067560351b8e55adf71dbed532360"
BTC = "0f9188f13cb7b2c71f2a335e3a4fc328bf5beb436012afca590b1a11466e2206"
BTX_ID, BTC_ID = f"btx:{BTX}:0:native", f"btc:{BTC}:0:native"
HOME = ROOT / "home"
HOME.mkdir(mode=0o700)
FIXTURE_EPOCH = int(time.time()) - 1800
CASE = sys.argv[2]
assert CASE == "maker-refund"
result = {"status": "INCOMPLETE", "case": CASE}
nodes = []


def save(stage):
    result["stage"] = stage
    (OUT / "result.json").write_text(json.dumps(result, indent=2, default=str) + "\n")
    print(stage, flush=True)


def until(predicate, seconds=25):
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        value = predicate()
        if value:
            return value
        time.sleep(0.4)
    raise TimeoutError("predicate did not become true")


def ports(count):
    held = []
    try:
        for _ in range(count):
            sock = socket.socket()
            sock.bind(("127.0.0.1", 0))
            held.append(sock)
        return [sock.getsockname()[1] for sock in held]
    finally:
        for sock in held:
            sock.close()


class RPCError(Exception):
    pass


class Node:
    def __init__(self, name, binary, genesis, assigned_ports):
        self.name, self.binary, self.genesis = name, binary, genesis
        self.port, self.p2p = assigned_ports
        self.data = ROOT / name
        self.data.mkdir(mode=0o700)
        self.cookie = self.data / "regtest" / ".cookie"
        self.url = f"http://127.0.0.1:{self.port}"
        self.process = None
        self.version = "OLD"
        nodes.append(self)

    def rpc(self, method, *params, wallet=None, timeout=25):
        cookie = base64.b64encode(self.cookie.read_bytes().strip()).decode()
        request = Request(self.url + (f"/wallet/{wallet}" if wallet else ""),
                          json.dumps({"jsonrpc": "1.0", "id": 1, "method": method,
                                      "params": params}).encode(),
                          {"Authorization": f"Basic {cookie}", "Content-Type": "application/json"})
        try:
            response = urlopen(request, timeout=timeout)
        except HTTPError as error:
            response = error
        with response:
            row = json.load(response, parse_float=Decimal)
        if row.get("error"):
            raise RPCError(f"{self.name}.{method}: {row['error']}")
        return row["result"]

    def wallet(self, method, *params):
        return self.rpc(method, *params, wallet="trader")

    def start(self, suffix, *args):
        log = OUT / f"{self.name}-{suffix}.log"
        env = {**os.environ, "HOME": str(HOME)}
        for key in ("LD_PRELOAD", "PYTHONPATH", "PYTHONHOME"):
            env.pop(key, None)
        with log.open("wb") as stream:
            self.process = subprocess.Popen(
                [str(self.binary), "-regtest", f"-datadir={self.data}",
                 f"-rpcport={self.port}", f"-port={self.p2p}", "-rpcbind=127.0.0.1",
                 "-bind=127.0.0.1", "-listen=1", "-connect=0", "-dnsseed=0",
                 "-discover=0", "-txindex=1", *args], stdout=stream, stderr=stream,
                env=env)
        def ready():
            if self.process.poll() is not None:
                raise RuntimeError(f"{self.name} exited during {suffix}; see {log.name}")
            try:
                return self.rpc("getblockchaininfo", timeout=2)
            except (OSError, RPCError):
                return None
        assert until(ready, 40)["chain"] == "regtest"
        assert self.rpc("getblockhash", 0) == self.genesis
        expected = os.environ[f"BTX_{self.version}_SHA256"]
        assert hashlib.sha256(self.binary.read_bytes()).hexdigest() == expected

    def stop(self):
        if self.process is not None and self.process.poll() is None:
            try:
                self.rpc("stop", timeout=8)
                assert self.process.wait(timeout=15) == 0
            except Exception:
                self.process.terminate()
                try:
                    self.process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    self.process.kill()
                    self.process.wait()
                raise

    def mine(self, count, address, spacing=1):
        before = self.rpc("getblockcount")
        header = self.rpc("getblockheader", self.rpc("getbestblockhash"))
        stamp = header["time"] if before else FIXTURE_EPOCH - (107 * spacing if spacing > 1 else 0)
        for index in range(count):
            self.rpc("setmocktime", stamp + (index + 1) * spacing)
            assert len(self.rpc("generatetoaddress", 1, address, timeout=90)) == 1
        assert self.rpc("getblockcount") == before + count
        self.rpc("setmocktime", 0)


def connected(a, b):
    a.rpc("addnode", f"127.0.0.1:{b.p2p}", "onetry")
    until(lambda: a.rpc("getconnectioncount") == b.rpc("getconnectioncount") == 1)


def synced(a, b):
    def match():
        return a.rpc("getbestblockhash") == b.rpc("getbestblockhash")
    if a.genesis != BTC:
        until(match, 40)
        return
    try:
        until(match, 4)
    except TimeoutError:
        peer_height = b.rpc("getblockcount")
        miner_height = a.rpc("getblockcount")
        assert a.rpc("getblockhash", peer_height) == b.rpc("getblockhash", peer_height)
        if peer_height == miner_height:
            return
        print(f"Bitcoin regtest relay lagged at {peer_height}; submitting blocks through {miner_height}", flush=True)
        for height in range(peer_height + 1, miner_height + 1):
            block_hash = a.rpc("getblockhash", height)
            submitted = b.rpc("submitblock", a.rpc("getblock", block_hash, 0))
            assert submitted in (None, "duplicate"), (height, submitted)
            assert b.rpc("getblockhash", height) == block_hash
        result.setdefault("bitcoin_relay_fallback", []).append([peer_height, miner_height])
        until(match, 8)


def atoms(value):
    scaled = Decimal(value) * 100_000_000
    assert scaled == scaled.to_integral_value()
    return int(scaled)


def balance(node):
    return atoms(node.wallet("getbalances")["mine"]["trusted"])


def check_leg(terms, ref, ops, funder, recipient, cap):
    asset = terms["asset"]
    funds = [op for op in ops if op["asset"] == asset and op["kind"] == "fund"]
    claims = [op for op in ops if op["asset"] == asset and op["kind"] == "claim"]
    assert len(funds) == len(claims) == 1
    fund, claim = funds[0]["txid"], claims[0]["txid"]
    assert ref["txid"] == fund
    for observer in (funder, recipient):
        funding = observer.rpc("getrawtransaction", fund, True)
        spend = observer.rpc("getrawtransaction", claim, True)
        assert funding["confirmations"] >= 20 and spend["confirmations"] >= 20
        output = funding["vout"][ref["vout"]]
        assert output["scriptPubKey"]["hex"] == terms["lock_commitment"]
        locked = atoms(output["value"])
        assert locked == int(terms["amount_atoms"])
        assert len(spend["vin"]) == len(spend["vout"]) == 1
        vin, payout = spend["vin"][0], spend["vout"][0]
        assert (vin["txid"], vin["vout"]) == (fund, ref["vout"])
        paid = atoms(payout["value"])
        assert payout["scriptPubKey"]["address"] == terms["payout"]
        assert 0 <= locked - paid <= int(terms["max_claim_fee_atoms"])
    assert recipient.wallet("getaddressinfo", terms["payout"])["ismine"]
    input_atoms = sum(atoms(funder.rpc("getrawtransaction", item["txid"], True)
                           ["vout"][item["vout"]]["value"]) for item in funding["vin"])
    funding_fee = input_atoms - sum(atoms(output["value"]) for output in funding["vout"])
    assert 0 <= funding_fee <= cap
    return {"funding_txid": fund, "funding_vout": ref["vout"], "claim_txid": claim,
            "locked_atoms": locked, "paid_atoms": paid, "funding_fee_atoms": funding_fee,
            "claim_fee_atoms": locked - paid, "payout": terms["payout"]}


# BTX actions below remain public RPCs into the retained compiled daemon.
# External Python is orchestration and read-only receipt verification only.
sys.path.insert(0, str(Path('product/contrib/swapnet').resolve()))
from swapnet.evm import keccak256
from evm_verify import verify_evm_leg
ETH_URL = os.environ['ANVIL_URL']
PIN = 'a06e30bad714ff02db5a2401a898bd7194d1c475b61bdab312ae194b1509e45d'

def eth(method, *params):
    request = Request(ETH_URL, json.dumps({'jsonrpc':'2.0','id':1,'method':method,'params':params}).encode(), {'Content-Type':'application/json'})
    with urlopen(request, timeout=15) as response:
        row=json.load(response)
    if row.get('error'): raise RPCError(f'Anvil.{method}: {row["error"]}')
    return row['result']

def ethmine(n=8):
    for _ in range(n): eth('evm_mine')

def ethreceipt(txid):
    def ready():
        r=eth('eth_getTransactionReceipt', txid)
        if r:
            assert int(r['status'],16)==1
            return r
    return until(ready, 15)

def view(n, sid):
    return next((s for s in n.rpc('listswaps')['swaps'] if s['swap_id']==sid), {})

def ops(n, sid, kind=None):
    rows=n.rpc('listswapoperations', {'swap_id':sid})['operations']
    return rows if kind is None else [o for o in rows if o['kind']==kind]

def summary(a,b,sid):
    return {n.name:{k:v for k,v in view(n,sid).items() if k in ('stage','last_error','last_action','funding_broadcast','refs')} for n in (a,b) if n.process and n.process.poll() is None}

def native_refund(terms, ref, funder, sid, sink, before):
    current=funder.rpc('getblockcount');maturity=terms['lock_value']
    assert terms['lock_domain']=='height' and current<maturity and maturity-current<=600, ('bounded maturity admission',current,maturity)
    original=[o for o in ops(funder,sid,'fund') if o['asset']==BTX_ID]
    assert len(original)==1 and original[0]['txid']==ref['txid']
    funder.stop();funder.start('maker-funded-restart','-swapnet=1','-wallet=trader','-swapnetwallet=trader',*FLAGS)
    assert view(funder,sid)['refs']['b']==ref
    assert [o['txid'] for o in ops(funder,sid,'fund') if o['asset']==BTX_ID]==[ref['txid']]
    try: funder.rpc('refundswap', {'swap_id':sid})
    except RPCError as error: assert 'REFUND_EARLY:' in str(error), error
    else: raise AssertionError('native refund accepted before maturity')
    refund=until(lambda:next((o for o in ops(funder,sid,'refund') if o['asset']==BTX_ID),None),15)
    refund_id=refund['txid'];assert refund_id
    funder.mine(maturity-1-current,sink)
    assert funder.rpc('getblockcount')==maturity-1
    assert refund_id not in funder.rpc('getrawmempool')
    assert funder.rpc('gettxout',ref['txid'],ref['vout'],True)
    funder.mine(1,sink)
    until(lambda:refund_id in funder.rpc('getrawmempool'),30)
    assert funder.rpc('getblockcount')==maturity
    funder.mine(20,sink)
    until(lambda:view(funder,sid).get('stage')=='refunded',40)
    tx=funder.rpc('getrawtransaction',refund_id,True);fund=funder.rpc('getrawtransaction',ref['txid'],True)
    assert tx['confirmations']>=20 and tx['locktime']==maturity
    assert len(tx['vin'])==len(tx['vout'])==1
    assert (tx['vin'][0]['txid'],tx['vin'][0]['vout'])==(ref['txid'],ref['vout'])
    out=tx['vout'][0];assert out['scriptPubKey']['address']==terms['refund_payout']
    assert funder.wallet('getaddressinfo',terms['refund_payout'])['ismine']
    locked=atoms(fund['vout'][ref['vout']]['value']);paid=atoms(out['value'])
    assert locked==int(terms['amount_atoms']) and 0<locked-paid<=int(terms['max_refund_fee_atoms'])
    inputs=sum(atoms(funder.rpc('getrawtransaction',v['txid'],True)['vout'][v['vout']]['value']) for v in fund['vin'])
    fee=inputs-sum(atoms(o['value']) for o in fund['vout'])
    assert 0<fee and fee+(locked-paid)<=500_000 and balance(funder)-before==-fee-(locked-paid)
    assert [o['txid'] for o in ops(funder,sid,'fund') if o['asset']==BTX_ID]==[ref['txid']]
    assert not ops(funder,sid,'claim') and not view(funder,sid)['secret_exposed']
    oldops=ops(funder,sid);funder.stop();funder.start('terminal-restart','-swapnet=1','-wallet=trader','-swapnetwallet=trader',*FLAGS)
    assert view(funder,sid)['stage']=='refunded' and ops(funder,sid)==oldops
    return {'funding_txid':ref['txid'],'funding_vout':ref['vout'],'refund_txid':refund_id,'maturity':maturity,'refund_atoms':paid,'funding_fee_atoms':fee,'refund_fee_atoms':locked-paid,'early_refused':True,'restart_original_preserved':True}

FLAGS=('-autoshieldcoinbase=0','-regtestmatmulbindingheight=2147483647','-regtestmatmulproductdigestheight=2147483647','-regtestmatmulv4height=2147483647','-regtestmatmulrequireproductpayload=0','-autoupdate=0','-dbcache=16','-par=1')

def run():
    assigned=ports(4);binary=Path(os.environ['BTX_OLD']).absolute()
    a=Node('btx-a',binary,BTX,assigned[:2]);b=Node('btx-b',binary,BTX,assigned[2:])
    save('initialize real native wallets and chain')
    for n in (a,b):n.start('setup','-swapnet=0',*FLAGS);n.rpc('createwallet','trader')
    a.rpc('createwallet','miner');sink=a.rpc('getnewaddress','','p2mr',wallet='miner');a.rpc('unloadwallet','miner',False)
    connected(a,b)
    for n in (a,b):a.mine(3,n.wallet('getnewaddress','','p2mr'));synced(a,b)
    a.mine(105,sink);synced(a,b)
    for n in (a,b):n.stop();n.start('native-swapnet','-swapnet=1','-wallet=trader','-swapnetwallet=trader',*FLAGS)
    connected(a,b);until(lambda:all(n.rpc('getswapbootstrapinfo')['admitted_peers']==1 for n in (a,b)),40)
    assert all(n.rpc('getswapnetworkinfo')['in_process'] is True for n in (a,b))
    # Exact compiler-profile contract deployment, not injected runtime/storage.
    artifact=json.loads(Path(os.environ['CONTRACT_ARTIFACT']).read_text());code=artifact['bytecode']['object']
    assert keccak256(bytes.fromhex(code.removeprefix('0x'))).hex()=='401e81e4ab795f39e48b76bda608771e10078e23cfc1d807983b05ee3da97cde'
    accounts=eth('eth_accounts');deployment=ethreceipt(eth('eth_sendTransaction',{'from':accounts[0],'data':code if code.startswith('0x') else '0x'+code,'gas':'0x600000'}));contract=deployment['contractAddress']
    assert keccak256(bytes.fromhex(eth('eth_getCode',contract,'latest')[2:])).hex()==PIN
    genesis=eth('eth_getBlockByNumber','0x0',False)['hash'][2:];chain=int(eth('eth_chainId'),16);eid=f'evm:{genesis}:{chain}:native'
    result['evm']={'asset':eid,'contract':contract,'runtime_hash':PIN,'deployment':deployment['transactionHash']}
    eth_accounts = {}
    for n in (a,b):
        n.rpc('setswapassetpolicy',{'policy':{'asset':eid,'rpc_url':ETH_URL,'contract':contract,'runtime_hash':PIN}})
        assert {x['asset'] for x in n.rpc('listswapassets')['assets'] if x['ready']}=={BTX_ID,eid}
        info=n.rpc('getswapwalletinfo');address=next(x['address'] for x in info['foreign_accounts'] if x['asset']==eid)
        eth_accounts[n.name] = address
        eth('anvil_setBalance',address,hex(10**21))
        assert int(eth('eth_getBalance',address,'latest'),16)==10**21
    # Establish the deployment on the finalized chain before holding mining.
    ethmine(8)
    finalized = eth('eth_getBlockByNumber', 'finalized', False)
    assert int(finalized['number'], 16) >= int(deployment['blockNumber'], 16)
    historical = eth('eth_getCode', contract, finalized['number'])
    assert keccak256(bytes.fromhex(historical[2:])).hex() == PIN
    result['finalized_deployment'] = {'block': finalized['number'],
                                      'hash': finalized['hash'], 'runtime_pin_matched': True}
    # Keep the short-lock transaction pending until both old processes are stopped.
    eth('evm_setAutomine', False)
    before={n.name:balance(n) for n in (a,b)};result['before_btx_atoms']=before
    assert min(before.values())>=20_000_000
    sell,buy=BTX_ID,eid
    sell_amount=10_000_000
    def cap(asset):return 500_000 if asset==BTX_ID else 6*10**15
    def recovery_cap(asset):return 100_000 if asset==BTX_ID else 2*10**15
    def mandate(n,asset):
        return n.rpc('createswapmandate',{'mandate':{'principal':'owner:cookie','asset':asset,'max_total_atoms':str(50_000_000 if asset==BTX_ID else 5*10**16),'max_trade_atoms':str(25_000_000 if asset==BTX_ID else 2*10**16),'max_fee_atoms':str(2_000_000 if asset==BTX_ID else 10**16),'expires_at':int(time.time())+3600,'nonce':secrets.token_hex(32)}})['mandate_id']
    maker=mandate(b,buy);taker=mandate(a,sell)
    save('advertise native maker and request exact quote')
    b.rpc('setswapmarket',{'market':{'sell_asset':sell,'buy_asset':buy,'numerator':str(10**9),'denominator':str(1),'maker_fee_atoms':str(10**12 if buy==eid else 1000),'max_receive_network_fee_atoms':str(recovery_cap(buy)),'max_input_atoms':str(sell_amount*2),'expires_at':int(time.time())+1200},'mandate_id':maker,'max_local_fee_atoms':str(cap(buy)),'refund_fee_atoms':str(recovery_cap(buy)),'claim_fee_atoms':str(recovery_cap(sell))})
    until(lambda:a.rpc('listswapproviders')['providers'],30)
    rfq=a.rpc('requestswapquote',{'sell_asset':sell,'buy_asset':buy,'sell_atoms':str(sell_amount)})
    quotes=until(lambda:a.rpc('getswapquotes',{'request_id':rfq['request_id']})['quotes'],40);assert len(quotes)==1
    quote=quotes[0];assert int(quote['sell_atoms'])==sell_amount
    accepted=a.rpc('acceptswapquote',{'quote_id':quote['id'],'mandate_id':taker,'max_local_fee_atoms':str(cap(sell)),'refund_fee_atoms':str(recovery_cap(sell)),'claim_fee_atoms':str(recovery_cap(buy))});sid=accepted['swap_id'];result['swap_id']=sid
    save('observe original BTX and pending ETH funding on v0.34.16')
    native_ref = None
    deadline = time.monotonic() + 180
    while time.monotonic() < deadline:
        taker_state = view(a, sid)
        maker_state = view(b, sid)
        ref = taker_state.get('refs', {}).get('a')
        if ref and native_ref is None and any(
                op['asset'] == BTX_ID and op['kind'] == 'fund' and op['state'] == 'broadcast'
                for op in ops(a, sid)):
            funding = a.rpc('getrawtransaction', ref['txid'], True)
            terms = taker_state['agreement']['long_leg']
            output = funding['vout'][ref['vout']]
            assert atoms(output['value']) == int(terms['amount_atoms'])
            assert output['scriptPubKey']['hex'] == terms['lock_commitment']
            assert funding.get('confirmations', 0) == 0
            native_ref = ref
            height = a.rpc('getblockcount')
            eth_before = int(eth('eth_getBlockByNumber', 'latest', False)['timestamp'], 16)
            eth_after = eth_before + 20 * 45
            short_remaining = int(taker_state['agreement']['short_leg']['lock_value']) - eth_after
            long_remaining = (int(terms['lock_value']) - height - 20) * 45
            assert long_remaining >= short_remaining + 7200 and short_remaining > 3600
            eth('evm_setNextBlockTimestamp', eth_after)
            ethmine(1)
            assert int(eth('eth_getBlockByNumber', 'latest', False)['timestamp'], 16) == eth_after
            a.mine(20, sink)
            synced(a, b)
        eth_funds = [op['txid'] for op in ops(b, sid, 'fund')
                     if op['asset'] == eid and op['state'] == 'broadcast']
        lock = maker_state.get('refs', {}).get('b')
        if native_ref and lock and eth_funds:
            assert eth_funds == [lock['txid']]
            break
        time.sleep(0.5)
    else:
        raise TimeoutError('original old-build funding did not reach the upgrade cut')

    assert maker_state['refs']['a'] == native_ref
    assert maker_state['recovery_ready']
    short = maker_state['agreement']['short_leg']
    assert short['asset'] == eid and short['lock_domain'] == 'timestamp'
    assert eth('eth_getTransactionByHash', lock['txid'])['hash'] == lock['txid']
    assert eth('eth_getTransactionReceipt', lock['txid']) is None
    for node in (a, b):
        assert not view(node, sid)['secret_exposed']
        assert not ops(node, sid, 'claim')
    synced(a, b)
    btx_tip = b.rpc('getbestblockhash')
    data_identity = (b.data.stat().st_dev, b.data.stat().st_ino)
    budget = b.rpc('listswapmandates')['mandates']
    assert len(budget) == 1 and budget[0]['id'] == maker and int(budget[0]['held_atoms']) > 0

    a.stop()
    assert a.process.poll() == 0
    b.stop()
    assert b.process.poll() == 0
    save('both old nodes stopped before confirming the original ETH lock')
    ethmine(8)
    funding_receipt = ethreceipt(lock['txid'])
    assert funding_receipt['to'].lower() == contract.lower()
    assert int(eth('eth_getBlockByNumber', 'finalized', False)['number'], 16) >= int(funding_receipt['blockNumber'], 16)
    eth('evm_setAutomine', True)

    flags = ('-swapnet=1', '-swapnetmode=recovery', '-wallet=trader', '-swapnetwallet=trader', *FLAGS)
    b.binary = Path(os.environ['BTX_NEW']).resolve()
    b.version = 'NEW'

    def assert_isolated_maker():
        assert a.process.poll() == 0 and b.rpc('getconnectioncount') == 0
        assert (b.data.stat().st_dev, b.data.stat().st_ino) == data_identity
        assert b.rpc('getbestblockhash') == btx_tip
        assert eth('eth_getBlockByNumber', '0x0', False)['hash'][2:] == genesis
        assert int(eth('eth_chainId'), 16) == chain
        assert ethreceipt(lock['txid'])['blockHash'] == funding_receipt['blockHash']
        mode = b.rpc('getswapmode')
        assert mode['mode'] == 'recovery' and mode['startup_recovery_lock'] is True
        assert mode['existing_obligations_recovery_enabled'] is True
        assert mode['new_trades_enabled'] is False

    b.start('upgrade-maker', *flags)
    assert_isolated_maker()
    assert eid in {x['asset'] for x in b.rpc('listswapassets')['assets'] if x['ready']}
    assert view(b, sid)['refs'] == maker_state['refs']
    assert b.rpc('listswapmandates')['mandates'] == budget
    result['upgrade_boundary'] = {
        'btx_tip': btx_tip, 'btx_outpoint': native_ref, 'eth_lock': lock,
        'eth_funding_block': funding_receipt['blockHash'], 'held_before_refund': budget[0]['held_atoms'],
        'taker_stop_exit': a.process.poll(), 'maker_connections': b.rpc('getconnectioncount'),
    }
    save('verify early refund refusal after maker-only upgrade')
    assert int(eth('eth_getBlockByNumber', 'latest', False)['timestamp'], 16) < int(short['lock_value'])
    try:
        b.rpc('refundswap', {'swap_id': sid})
    except RPCError as error:
        assert 'REFUND_EARLY:' in str(error)
    else:
        raise AssertionError('refund accepted before maturity')
    assert all(o['kind'] not in ('claim', 'refund', 'withdraw') for o in ops(b, sid))
    result['early_refusal'] = 'REFUND_EARLY'

    save('mature the original ETH lock and verify refund and withdrawal')
    eth('evm_setNextBlockTimestamp', int(short['lock_value']))
    ethmine(1)
    b.rpc('refundswap', {'swap_id': sid})

    def refunded():
        assert a.process.poll() == 0 and b.rpc('getconnectioncount') == 0
        ethmine(1)
        state = view(b, sid)
        return state if state.get('stage') == 'refunded' else None

    final = until(refunded, 90)
    assert final['refs'] == maker_state['refs'] and not final['secret_exposed']
    terminal_ops = ops(b, sid)
    assert [op['txid'] for op in terminal_ops if op['kind'] == 'fund'] == [lock['txid']]
    for kind in ('refund', 'withdraw'):
        assert len([op for op in terminal_ops if op['kind'] == kind]) == 1
    receipt = verify_evm_leg(eth, short, lock, terminal_ops, kind='refund')
    assert receipt['runtime_hash'] == PIN and receipt['remaining_credit_wei'] == '0'
    assert int(receipt['amount_wei']) == int(short['amount_atoms'])
    fees = sum(int(receipt[k]) for k in ('funding_fee_wei', 'settlement_fee_wei', 'withdrawal_fee_wei'))
    assert fees <= cap(eid)
    address = short['refund_payout']
    assert address == eth_accounts[b.name]
    assert int(eth('eth_getBalance', eth_accounts[a.name], 'latest'), 16) == 10**21
    assert int(eth('eth_getBalance', address, 'latest'), 16) == 10**21 - fees
    assert int(eth('eth_getBalance', contract, 'latest'), 16) == 0
    terminal_budget = b.rpc('listswapmandates')['mandates']
    assert len(terminal_budget) == 1 and terminal_budget[0]['id'] == maker
    assert int(terminal_budget[0]['held_atoms']) == 0
    result['eth_refund'] = receipt
    before_reopen = b.rpc('gettxout', native_ref['txid'], native_ref['vout'], True)

    save('reopen only the maker and check original IDs and cleared budget')
    b.stop()
    b.start('terminal-recovery', *flags)
    assert_isolated_maker()
    reopened = view(b, sid)
    assert reopened['stage'] == 'refunded' and reopened['refs'] == final['refs']
    assert ops(b, sid) == terminal_ops
    assert b.rpc('listswapmandates')['mandates'] == terminal_budget
    assert int(eth('eth_getBalance', address, 'latest'), 16) == 10**21 - fees
    assert b.rpc('gettxout', native_ref['txid'], native_ref['vout'], True) == before_reopen
    result.update(held_after_restart=terminal_budget[0]['held_atoms'],
                  original_lock_refunded_and_withdrawn_once=True, taker_offline=True,
                  btx_outpoint_unspent=before_reopen is not None)

def terminate(*_):raise TimeoutError('bounded outer controller interrupted')
signal.signal(signal.SIGTERM,terminate)
try:
    run()
except Exception as error:
    result.update(status='FAIL',error=f'{type(error).__name__}: {error}');save(result.get('stage','setup'));raise
finally:
    failures=[]
    for n in reversed(nodes):
        try:n.stop()
        except Exception as error:failures.append(f'{n.name}: {type(error).__name__}')
    result['cleanup_errors']=failures;save(result.get('stage','setup'))
    if failures:raise RuntimeError('owned cleanup failed')
result['status']='PASS';save(CASE+' native workflow verified')
