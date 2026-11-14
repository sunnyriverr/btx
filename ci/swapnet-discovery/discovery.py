"""Disposable native regtest run. Evidence omits transaction witnesses and keys."""
import base64
from decimal import Decimal
import json
import os
from pathlib import Path
import secrets
import signal
import socket
import sqlite3
import subprocess
import sys
import time
from urllib.error import HTTPError
from urllib.request import Request, urlopen

ROOT = Path(sys.argv[1]).resolve()
OUT = Path("records").resolve()
BTX = "521ad0951ed299e9c56aeb7db8188972772067560351b8e55adf71dbed532360"
BTC = "0f9188f13cb7b2c71f2a335e3a4fc328bf5beb436012afca590b1a11466e2206"
BTX_ID, BTC_ID = f"btx:{BTX}:0:native", f"btc:{BTC}:0:native"
HOME = ROOT / "home"
HOME.mkdir(mode=0o700)
result = {"status": "INCOMPLETE"}
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
        with log.open("wb") as stream:
            self.process = subprocess.Popen(
                [str(self.binary), "-regtest", f"-datadir={self.data}",
                 f"-rpcport={self.port}", f"-port={self.p2p}", "-rpcbind=127.0.0.1",
                 "-bind=127.0.0.1", "-listen=1", "-connect=0", "-dnsseed=0",
                 "-discover=0", "-txindex=1", *args], stdout=stream, stderr=stream,
                env={**os.environ, "HOME": str(HOME)})
        def ready():
            if self.process.poll() is not None:
                raise RuntimeError(f"{self.name} exited during {suffix}; see {log.name}")
            try:
                return self.rpc("getblockchaininfo", timeout=2)
            except (OSError, RPCError):
                return None
        assert until(ready, 40)["chain"] == "regtest"
        assert self.rpc("getblockhash", 0) == self.genesis
        assert Path(f"/proc/{self.process.pid}/exe").resolve() == self.binary

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

    def mine(self, count, address):
        before = self.rpc("getblockcount")
        assert len(self.rpc("generatetoaddress", count, address, timeout=90)) == count
        assert self.rpc("getblockcount") == before + count


def connected(a, b):
    a.rpc("addnode", f"127.0.0.1:{b.p2p}", "onetry")
    until(lambda: a.rpc("getconnectioncount") == b.rpc("getconnectioncount") == 1)


def synced(a, b):
    until(lambda: a.rpc("getbestblockhash") == b.rpc("getbestblockhash"), 40)


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
        assert funding["confirmations"] > 0 and spend["confirmations"] > 0
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


def run():
    assigned=iter(ports(6));binary=Path('payload/bin/btxd').resolve()
    a,b,x=[Node(name,bin,gen,(next(assigned),next(assigned))) for name,bin,gen in [('a',binary,BTX),('b',binary,BTX),('btc',ROOT/'bitcoin-30.4/bin/bitcoind',BTC)]]
    flags=('-autoshieldcoinbase=0','-regtestmatmulbindingheight=2147483647','-regtestmatmulproductdigestheight=2147483647','-regtestmatmulv4height=2147483647','-regtestmatmulrequireproductpayload=0')
    save('default-off and disposable wallets')
    for n in (a,b,x):
        n.start('setup', *(( '-swapnet=0',*flags) if n!=x else ()))
        n.rpc('createwallet','trader')
    try:a.rpc('getswapnetworkinfo')
    except RPCError as e:assert 'disabled' in str(e)
    else:raise AssertionError('SwapNet unexpectedly enabled')
    for n in (a,b):n.stop()
    enabled=('-swapnet=1','-wallet=trader','-swapnetwallet=trader',*flags)
    a.start('enabled',*enabled);time.sleep(2);b.start('enabled',*enabled)
    connected(a,b)
    mutual=lambda:all(n.rpc('getswapbootstrapinfo')['admitted_peers']>=1 for n in (a,b))
    until(mutual,30);result['mutual_staggered_admission']=True
    save('configure test market without accepting quotes')
    b.rpc('setswapassetpolicy',{'policy':{'asset':BTC_ID,'rpc_url':x.url,'cookie_path':str(x.cookie),'wallet':'trader','confirmations':2,'fee_rate':2}})
    cap='300000'
    mid=b.rpc('createswapmandate',{'mandate':{'principal':'owner:cookie','asset':BTC_ID,'max_total_atoms':'50000000','max_trade_atoms':'50000000','max_fee_atoms':cap,'expires_at':int(time.time())+900,'nonce':secrets.token_hex(32)}})['mandate_id']
    b.rpc('setswapmarket',{'market':{'sell_asset':BTX_ID,'buy_asset':BTC_ID,'numerator':'2','denominator':'1','maker_fee_atoms':'10000','max_receive_network_fee_atoms':'10000','max_input_atoms':'25000000','expires_at':int(time.time())+600},'mandate_id':mid,'max_local_fee_atoms':cap,'refund_fee_atoms':'10000','claim_fee_atoms':'18000'})
    ad=b.rpc('publishswapprovider');assert ad['advertised'];identity=ad['identity']
    def env():
        return next((e for e in a.rpc('listswapproviders')['providers'] if e['body']['identity']==identity),None)
    first=until(env,30);body=first['body'];assert first['signature'] and body['network']==BTX and {'sell':BTX_ID,'buy':BTC_ID} in body['pairs']
    result['first_provider']={'identity':identity,'sequence':body['sequence'],'signature_present':True,'network':body['network']}
    audit=a.rpc('getswaphealth')['audit_head']
    save('restart taker and restore ordinary connectivity')
    a.stop();a.start('restart',*enabled);connected(a,b);until(mutual,30)
    assert a.rpc('getswaphealth')['audit_head']==audit
    oldseq=body['sequence'];assert b.rpc('publishswapprovider')['advertised']
    fresh=until(lambda: (e if (e:=env()) and e['body']['sequence']>oldseq else None),30)
    result['restart_mutual_admission']=True;result['fresh_sequence']=fresh['body']['sequence']
    for n in (a,b):
        assert n.rpc('listswaps')['swaps']==[]
        assert n.rpc('getswapnetworkinfo')['automatic_spend_atoms']=='0'
        assert n.rpc('getswaphealth')['sessions']==0
        assert n.rpc('getrawmempool')==[]
    result['no_swaps_or_funding']=True
    b.stop();b.start('disabled','-swapnet=0','-wallet=trader',*flags)
    try:b.rpc('getswapnetworkinfo')
    except RPCError as e:assert 'disabled' in str(e)
    else:raise AssertionError('disable after restart failed')
    result['disabled_after_restart']=True;result['status']='PASS';save('finished')

def terminate(*_):
    raise TimeoutError("outer test timeout")


signal.signal(signal.SIGTERM, terminate)
try:
    run()
except Exception as error:
    result.update(status="FAIL", error=f"{type(error).__name__}: {error}")
    save(result["stage"])
    raise
finally:
    failures = []
    for node in reversed(nodes):
        try:
            node.stop()
        except Exception as error:
            failures.append(f"{node.name}: {type(error).__name__}")
    result["cleanup_errors"] = failures
    save(result["stage"])
    if failures:
        raise RuntimeError(f"cleanup failed: {failures}")
result["status"] = "PASS"
save("settlement verified")
