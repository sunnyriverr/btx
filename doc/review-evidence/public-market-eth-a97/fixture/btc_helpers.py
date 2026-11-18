"""Disposable native regtest run. Evidence omits transaction witnesses and keys."""
import base64
import hashlib
import platform
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

ROOT = OUT = TEST_HOME = None
BTX = "521ad0951ed299e9c56aeb7db8188972772067560351b8e55adf71dbed532360"
BTC = "0f9188f13cb7b2c71f2a335e3a4fc328bf5beb436012afca590b1a11466e2206"
BTX_ID, BTC_ID = f"btx:{BTX}:0:native", f"btc:{BTC}:0:native"
CASE = None
FIXTURE_EPOCH = None
result = {}
nodes = []
MANIFEST = None


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(1048576), b''):
            h.update(block)
    return h.hexdigest()


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
        if method in MANIFEST['swapnet_methods']:
            assert self.genesis == BTX
            wallet = 'trader' if wallet is None else wallet
            assert wallet == 'trader', 'Every market call must use the same signing-wallet context'
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
        env = {**os.environ, "HOME": str(TEST_HOME)}
        for key in ("LD_PRELOAD", "DYLD_INSERT_LIBRARIES", "PYTHONPATH", "PYTHONHOME", "GH_TOKEN", "GITHUB_TOKEN"):
            env.pop(key, None)
        with log.open("wb") as stream:
            self.process = subprocess.Popen(
                [str(self.binary), "-regtest", f"-datadir={self.data}",
                 f"-rpcport={self.port}", f"-port={self.p2p}", "-rpcbind=127.0.0.1",
                 "-bind=127.0.0.1", "-listen=1", "-connect=0", "-dnsseed=0",
                 "-discover=0", "-txindex=1", *(["-autoupdate=0"] if self.genesis == BTX else []), *args], stdout=stream, stderr=stream,
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
        assert self.process.poll() is None
        expected = MANIFEST['btx'] if self.genesis == BTX else MANIFEST['bitcoin']
        assert self.binary.resolve() == Path(expected['path']).resolve()
        assert sha(self.binary) == expected['sha256']
        result.setdefault('node_starts', []).append({'name': self.name, 'stage': suffix,
            'pid': self.process.pid, 'binary_sha256': expected['sha256'], 'regtest_genesis': self.genesis})

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
    assigned = iter(ports(8))
    btx_bin = Path(MANIFEST['btx']['path']).resolve()
    btc_bin = Path(MANIFEST['bitcoin']['path']).resolve()
    a, b, x, y = [Node(name, binary, genesis, (next(assigned), next(assigned)))
                  for name, binary, genesis in (("btx-a", btx_bin, BTX), ("btx-b", btx_bin, BTX),
                                                ("btc-a", btc_bin, BTC), ("btc-b", btc_bin, BTC))]
    flags = ("-autoshieldcoinbase=0", "-regtestmatmulbindingheight=2147483647",
             "-regtestmatmulproductdigestheight=2147483647", "-regtestmatmulv4height=2147483647",
             "-regtestmatmulrequireproductpayload=0")
    save("boot and preload distinct wallets")
    for n in (a, b, x, y):
        n.start("setup", *(("-swapnet=0", *flags) if n in (a, b) else ()))
        assert n.rpc("createwallet", "trader")["name"] == "trader"
    sinks = {}
    for n, address_type in ((a, "p2mr"), (y, "bech32")):
        n.rpc("createwallet", "miner")
        sinks[n] = n.rpc("getnewaddress", "", address_type, wallet="miner")
        n.rpc("unloadwallet", "miner", False)
    for n in (x, y):
        n.rpc("createwallet", "observer", True, True)
        n.rpc("createwallet", "other-signer")
    connected(a, b)
    connected(x, y)
    save("fund and mature test coins")
    for n, peer, addr_type in ((a, b, "p2mr"), (y, x, "bech32")):
        spacing = 1
        n.mine(3, n.wallet("getnewaddress", "", addr_type), spacing)
        n.mine(105, sinks[n], spacing)
        synced(n, peer)
    if CASE == "refund":
        # Give the deadline estimator a short, slower history without mining
        # the wallet coinbases before the wallet birth time.
        a.mine(24, sinks[a], 60)
        synced(a, b)
    for n in (a, b):
        n.stop()
        n.start("swapnet", "-swapnet=1", "-wallet=trader", "-swapnetwallet=trader", *flags)
        assert n.rpc("listwallets") == ["trader"]
    connected(a, b)
    until(lambda: all(n.rpc("getswapbootstrapinfo")["admitted_peers"] == 1 for n in (a, b)))
    save("bind regtest Bitcoin wallet policies")
    for n, foreign in ((a, x), (b, y)):
        policy = {"asset": BTC_ID, "rpc_url": foreign.url,
                  "cookie_path": str(foreign.cookie), "wallet": "trader", "confirmations": 6}
        policy["watch_wallet"] = "observer"
        n.rpc("setswapassetpolicy", {"policy": policy})
        assert {v["asset"] for v in n.rpc("listswapassets")["assets"] if v["ready"]} == {BTX_ID, BTC_ID}
    before = {n.name: balance(n) for n in nodes}
    result["before_atoms"] = before
    assert before[a.name] >= 20_000_000 and before[y.name] >= 40_000_000
    assert before[b.name] == before[x.name] == 0
    fee_cap = 300_000
    def mandate(n, asset, cap):
        return n.rpc("createswapmandate", {"mandate": {"principal": n.rpc('getswapauthinfo')['principal'],
                     "asset": asset, "max_total_atoms": str(cap), "max_trade_atoms": str(cap),
                     "max_fee_atoms": str(fee_cap), "expires_at": int(time.time()) + 900,
                     "nonce": secrets.token_hex(32)}})["mandate_id"]
    save("publish one firm offer through native peers")
    # A mode grants no wallet authority. Only the maker receives an explicit
    # finite mandate here; the taker has no mandate until owner confirmation.
    assert a.rpc('getswapmode')['mode'] == 'taker'
    assert a.rpc('getswapmode')['automatic_spend_atoms'] == '0'
    b.rpc('setswapmode', {'mode': 'maker'})
    assert b.rpc('getswapmode')['mode'] == 'maker'
    maker = mandate(b, BTC_ID, 50_000_000)
    assert a.rpc('listswapmandates')['mandates'] == []
    b.rpc("setswapmarket", {"market": {"sell_asset": BTX_ID, "buy_asset": BTC_ID,
          "numerator": "2", "denominator": "1", "maker_fee_atoms": "10000",
          "max_receive_network_fee_atoms": "10000", "max_input_atoms": "25000000",
          "expires_at": int(time.time()) + 600}, "mandate_id": maker,
          "max_local_fee_atoms": str(fee_cap), "refund_fee_atoms": "10000", "claim_fee_atoms": "18000"})
    published = b.rpc('publishswapoffer', {'sell_asset': BTX_ID, 'buy_asset': BTC_ID,
                    'sizes': ['20000000'], 'kind': 'firm', 'slots': 1, 'ttl': 300})
    offer = published['offer']['body']
    assert published['advertised'] is True and published['remote_liquidity_guaranteed'] is False
    assert offer['kind'] == 'firm' and len(offer['tiers']) == 1 and offer['tiers'][0]['slots'] == 1
    assert offer['network'] == BTX and offer['sell_asset'] == BTX_ID and offer['buy_asset'] == BTC_ID
    assert offer['tiers'][0]['sell_atoms'] == '20000000' and offer['tiers'][0]['buy_atoms'] == '40000000'
    def capacity():
        return [row for row in b.rpc('getswapmakercapacity')['slots'] if row['offer_id'] == offer['offer_id']]
    assert capacity() == [{'offer_id': offer['offer_id'], 'tier': 0, 'state': 'available', 'count': 1}]
    def discovered_offer():
        offers = a.rpc('listswappublicoffers', {'sell_asset': BTX_ID, 'buy_asset': BTC_ID})['offers']
        matching = [row for row in offers if row['body']['provider'] == offer['provider']
                    and row['body']['offer_id'] == offer['offer_id']]
        return matching[0] if len(matching) == 1 else None
    discovered = until(discovered_offer, 40)
    assert discovered == published['offer'], 'Offer must arrive via native signed discovery, not database seeding'
    assert all(n.rpc('listswaps')['swaps'] == [] for n in (a, b))
    mempools = {n.name: sorted(n.rpc('getrawmempool')) for n in nodes}
    locks = {n.name: n.wallet('listlockunspent') for n in nodes}
    assert all(not pool for pool in mempools.values())
    rfq = a.rpc('requestpublicswapquote', {'provider': offer['provider'], 'offer_id': offer['offer_id'], 'tier': 0})
    assert rfq['provider'] == offer['provider'] and rfq['spending_authority'] is False
    def public_quotes():
        reply = a.rpc('getswapquotes', {'request_id': rfq['request_id']})
        if reply.get('declined'):
            raise AssertionError('Public quote refused: ' + str(reply['declined']))
        return reply['quotes']
    quotes = until(public_quotes, 40)
    quote = quotes[0]
    assert len(quotes) == 1 and quote["sell_atoms"] == "20000000" and quote["buy_atoms"] == "40000000"
    assert quote['provider'] == offer['provider']
    assert quote['sell_asset'] == BTX_ID and quote['buy_asset'] == BTC_ID
    net_floor = int(quote['buy_atoms']) - int(quote['maker_fee_atoms']) - int(quote['max_receive_network_fee_atoms'])
    assert capacity() == [{'offer_id': offer['offer_id'], 'tier': 0, 'state': 'quoted', 'count': 1}]
    result['public_entry'] = {'offer_id': offer['offer_id'], 'provider': offer['provider'],
        'request_id': rfq['request_id'], 'tier': 0, 'signed_native_offer_arrival': True}
    result["quote"] = {"id": quote["id"], "sell_atoms": quote["sell_atoms"], "buy_atoms": quote["buy_atoms"],
                       "maker_fee_atoms": quote["maker_fee_atoms"]}
    save("review public quote without creating taker spending authority")
    auth = a.rpc('getswapauthinfo')
    assert auth['owner'] is True and auth['wallet'] == 'trader' and auth['principal']
    result['public_entry']['rpc_wallet'] = auth['wallet']
    preview = a.rpc('previewswap', {'quote_id': quote['id'], 'max_local_fee_atoms': str(fee_cap),
                    'refund_fee_atoms': '18000', 'claim_fee_atoms': '10000', 'min_receive_atoms': str(net_floor)})
    assert preview['requires_owner_confirmation'] is True and preview['funds_reserved'] is False
    assert preview['sell_asset'] == BTX_ID and preview['buy_asset'] == BTC_ID
    assert preview['sell_atoms'] == '20000000' and preview['maximum_send_atoms'] == str(20_000_000 + fee_cap)
    assert preview['net_receive_floor_atoms'] == preview['minimum_receive_atoms'] == str(net_floor)
    assert preview['max_local_fee_atoms'] == str(fee_cap) and preview['refund_fee_atoms'] == '18000' and preview['claim_fee_atoms'] == '10000'
    assert preview['provider'] == offer['provider'] and int(time.time()) < preview['expires_at'] <= quote['expires_at']
    assert a.rpc('listswapmandates')['mandates'] == []
    assert all(n.rpc('listswaps')['swaps'] == [] for n in (a, b))
    assert {n.name: balance(n) for n in nodes} == before
    assert {n.name: sorted(n.rpc('getrawmempool')) for n in nodes} == mempools
    assert {n.name: n.wallet('listlockunspent') for n in nodes} == locks
    result['public_entry']['preview_nonfunding_verified'] = True
    save("explicit owner confirmation creates one original trade")
    accepted = a.rpc('confirmswap', {'preview_id': preview['preview_id']})
    taker_rows = a.rpc('listswapmandates')['mandates']
    assert len(taker_rows) == 1
    taker = taker_rows[0]['id']
    one_shot = taker_rows[0]['mandate']
    assert one_shot['principal'] == auth['principal'] and one_shot['asset'] == BTX_ID
    assert one_shot['max_trade_atoms'] == '20000000' and one_shot['max_total_atoms'] == str(20_000_000 + fee_cap)
    assert one_shot['max_fee_atoms'] == str(fee_cap) and one_shot['expires_at'] <= quote['expires_at']
    assert a.rpc('confirmswap', {'preview_id': preview['preview_id']})['swap_id'] == accepted['swap_id']
    assert [row['id'] for row in a.rpc('listswapmandates')['mandates']] == [taker]
    result['public_entry'].update(preview_id=preview['preview_id'], taker_mandate_id=taker,
        one_shot_created_once=True, same_confirmation_retry_same_swap=True)
    sid = accepted["swap_id"]
    result["swap_id"] = sid
    def view(node):
        return next((sw for sw in node.rpc("listswaps")["swaps"] if sw["swap_id"] == sid), {})

    def operations(node, kind):
        return [row for row in node.rpc("listswapoperations", {"swap_id": sid})["operations"]
                if row["kind"] == kind]

    save("wait for durable long-leg funding")
    funded = until(lambda: (v if (v := view(a)).get("funding_broadcast") else None), 45)
    ref = funded["refs"]["a"]
    terms = funded["agreement"]["long_leg"]
    assert not funded["secret_exposed"] and funded["recovery_ready"]
    assert a.rpc("getswaprecoveryinfo", {"swap_id": sid})["refund_transaction_ready"]
    assert [op["txid"] for op in operations(a, "fund")] == [ref["txid"]]
    assert view(b) and not operations(b, "fund")
    assert capacity() == [{'offer_id': offer['offer_id'], 'tier': 0, 'state': 'reserved', 'count': 1}]
    result['public_entry']['maker_slot_transferred_once'] = True
    assert a.rpc("gettxout", ref["txid"], ref["vout"], True)["confirmations"] == 0
    a.mine(1, sinks[a])
    synced(a, b)
    funded_height = a.rpc("getblockcount")
    assert all(n.rpc("gettxout", ref["txid"], ref["vout"], False)["confirmations"] == 1 for n in (a, b))
    result["initial_funding"] = {"outpoint": ref, "height": funded_height, "confirmed": True,
                                 "counterparty_funded": False, "durable_refund": True}
    save("stop both SwapNet nodes after first funding confirmation")
    a.stop()
    b.stop()
    for n in ((a, b) if CASE == "restart" else (a,)):
        n.start("funded-restart", "-swapnet=1", "-wallet=trader", "-swapnetwallet=trader", *flags)
        assert n.rpc('getswapmode')['mode'] == ('taker' if n is a else 'maker')
        assert BTC_ID not in n.rpc("getswapwalletinfo")["startup_errors"]
        assert {v["asset"] for v in n.rpc("listswapassets")["assets"] if v["ready"]} == {BTX_ID, BTC_ID}
    assert view(a)["refs"]["a"] == ref
    assert [op["txid"] for op in operations(a, "fund")] == [ref["txid"]]
    assert a.rpc("gettxout", ref["txid"], ref["vout"], False)["confirmations"] == 1
    assert a.rpc('confirmswap', {'preview_id': preview['preview_id']})['swap_id'] == sid
    assert [row['id'] for row in a.rpc('listswapmandates')['mandates']] == [taker]
    assert [op['txid'] for op in operations(a, 'fund')] == [ref['txid']]
    result['public_entry']['confirmation_retry_after_restart_same_swap'] = True
    result["restart_preserved_original"] = True

    def verify_funding_outputs(node, first_height, script, expected_ref):
        found = []
        for height in range(first_height, node.rpc("getblockcount") + 1):
            block = node.rpc("getblock", node.rpc("getblockhash", height), 2)
            for tx in block["tx"]:
                found.extend({"txid": tx["txid"], "vout": out["n"]} for out in tx["vout"]
                             if out["scriptPubKey"]["hex"] == script)
        for txid in node.rpc("getrawmempool"):
            tx = node.rpc("getrawtransaction", txid, True)
            found.extend({"txid": txid, "vout": out["n"]} for out in tx["vout"]
                         if out["scriptPubKey"]["hex"] == script)
        result["funding_outputs"] = found
        assert found == [expected_ref]

    if CASE == "refund":
        save("refuse the refund before maturity")
        assert terms["lock_domain"] == "height"
        maturity = terms["lock_value"]
        assert funded_height < maturity <= funded_height + 6500
        refund_txid, = [op["txid"] for op in operations(a, "refund")]
        try:
            a.rpc("refundswap", {"swap_id": sid})
        except RPCError as error:
            assert "REFUND_EARLY:" in str(error), error
        else:
            raise AssertionError("refund accepted early")
        a.mine(maturity - 1 - funded_height, sinks[a])
        assert a.rpc("getblockcount") == maturity - 1
        try:
            a.rpc('refundswap', {'swap_id': sid})
        except RPCError as error:
            assert 'REFUND_EARLY:' in str(error), error
        else:
            raise AssertionError('Refund accepted at maturity minus one')
        assert refund_txid not in a.rpc("getrawmempool")
        assert a.rpc("gettxout", ref["txid"], ref["vout"], True)
        result["refund_early_rejected_at"] = funded_height
        save("mine to contractual maturity with counterparty offline")
        a.mine(1, sinks[a])
        until(lambda: refund_txid in a.rpc("getrawmempool"), 30)
        result["refund_first_seen_height"] = a.rpc("getblockcount")
        assert result["refund_first_seen_height"] == maturity
        def observed_refund():
            v = view(a)
            return v.get("observations", {}).get("a", {}).get("refunded", False)
        # Let the daemon observe the unconfirmed spend before the next block
        # so the bounded historical scan is not its first observation path.
        try:
            until(observed_refund, 15)
            result["saw_mempool_refund"] = True
        except TimeoutError:
            result["saw_mempool_refund"] = False
        a.mine(20, sinks[a])
        settled = view(a)
        result["reported_swap_stage"] = settled.get("stage")
        result["reported_last_error"] = settled.get("last_error")
        result["reported_long_leg"] = settled.get("observations", {}).get("a")

        assert [op["txid"] for op in operations(a, "fund")] == [ref["txid"]]
        assert [op["txid"] for op in operations(a, "refund")] == [refund_txid]
        assert not operations(a, "claim") and not view(a)["secret_exposed"]
        tx = a.rpc("getrawtransaction", refund_txid, True)
        assert tx["confirmations"] >= 20 and tx["locktime"] == maturity
        assert len(tx["vin"]) == len(tx["vout"]) == 1
        vin, payout = tx["vin"][0], tx["vout"][0]
        assert (vin["txid"], vin["vout"]) == (ref["txid"], ref["vout"])
        destination = terms["refund_payout"]
        assert payout["scriptPubKey"]["address"] == destination
        assert a.wallet("getaddressinfo", destination)["ismine"]
        assert not a.wallet("getaddressinfo", terms["payout"])["ismine"]
        assert terms["payout"] != destination
        funding = a.rpc("getrawtransaction", ref["txid"], True)
        locked = atoms(funding["vout"][ref["vout"]]["value"])
        assert locked == int(terms["amount_atoms"])
        fund_fee = sum(atoms(a.rpc("getrawtransaction", v["txid"], True)["vout"][v["vout"]]["value"])
                       for v in funding["vin"]) - sum(atoms(v["value"]) for v in funding["vout"])
        paid = atoms(payout["value"])
        refund_fee = locked - paid
        assert 0 < refund_fee <= int(terms["max_refund_fee_atoms"])
        assert 0 < fund_fee and fund_fee + refund_fee <= fee_cap
        assert balance(a) - before[a.name] == -fund_fee - refund_fee
        assert all(balance(n) == before[n.name] for n in (x, y))
        verify_funding_outputs(a, funded_height, terms["lock_commitment"], ref)
        result["refund"] = {"txid": refund_txid, "lock_height": maturity, "payout": destination,
                            "owner_wallet": "trader", "returned_atoms": paid, "funding_fee_atoms": fund_fee,
                            "refund_fee_atoms": refund_fee, "wallet_delta_atoms": balance(a)-before[a.name],
                            "confirmations": tx["confirmations"], "btc_balances_unchanged": True}
        save("refund and wallet ownership verified")
        try:
            until(lambda: view(a)["stage"] == "refunded", 40)
            result["reported_swap_stage"] = "refunded"
        except TimeoutError:
            result["terminal_state_pending"] = True
            raise
        budget_before_terminal_restart = a.rpc('listswapmandates')['mandates']
        assert budget_before_terminal_restart[0]['held_atoms'] == '0'
        oldops=a.rpc('listswapoperations',{'swap_id':sid})['operations']
        a.stop();a.start('terminal-restart','-swapnet=1','-wallet=trader','-swapnetwallet=trader',*flags)
        assert view(a)['stage']=='refunded'
        assert a.rpc('listswapoperations',{'swap_id':sid})['operations']==oldops
        assert a.rpc('listswapmandates')['mandates'] == budget_before_terminal_restart
        result['terminal_restart_preserved']=True
        return

    connected(a, b)
    until(lambda: all(n.rpc("getswapbootstrapinfo")["admitted_peers"] == 1 for n in (a, b)))
    y.mine(20, sinks[y])
    synced(y, x)
    a.mine(19, sinks[a])
    synced(a, b)
    save("observe funding and claims")
    deadline = time.monotonic() + 100
    states = []
    while time.monotonic() < deadline:
        states = [n.rpc("listswaps")["swaps"] for n in (a, b)]
        views = [{k: sw[k] for k in ("stage", "last_action", "last_error", "refs", "observations") if k in sw}
                 for items in states for sw in items if sw["swap_id"] == sid]
        if views != result.get("last_states"):
            result["last_states"] = views
            save("observe funding and claims")
        if len(views) == 2 and all(v["stage"] == "complete" for v in views):
            break
        # Mine confirmations only after seeing a pending tx. Extra blocks go to
        # the unloaded miner wallet, whose rewards never enter trader balances.
        if a.rpc("getrawmempool"):
            # Advance the short chain first. The long-chain depth must not
            # consume the full safety margin while the short tip stands still.
            y.mine(20, sinks[y])
            synced(y, x)
            a.mine(20, sinks[a])
            synced(a, b)
        elif y.rpc("getrawmempool"):
            y.mine(6, sinks[y])
            synced(y, x)
        time.sleep(0.8)
    else:
        result["after_atoms"] = {n.name: balance(n) for n in nodes}
        result["mempool_counts"] = {n.name: len(n.rpc("getrawmempool")) for n in nodes}
        raise TimeoutError("candidate failed to settle; see last_states")
    first, second = (items[0] for items in states)
    assert first["swap_id"] == second["swap_id"] == sid and first["agreement"] == second["agreement"]
    ops = sum((n.rpc("listswapoperations", {"swap_id": sid})["operations"] for n in (a, b)), [])
    long = check_leg(first["agreement"]["long_leg"], first["refs"]["a"], ops, a, b, fee_cap)
    short = check_leg(first["agreement"]["short_leg"], first["refs"]["b"], ops, y, x, fee_cap)
    assert long["locked_atoms"] == int(quote["sell_atoms"])
    assert short["locked_atoms"] == int(quote["buy_atoms"]) - int(quote["maker_fee_atoms"])
    btc_lock = y.rpc("getrawtransaction", short["funding_txid"], True)["vout"][short["funding_vout"]]["scriptPubKey"]["address"]
    for n in (x, y):
        assert n.rpc("getaddressinfo", btc_lock, wallet="observer")["ismine"]
        assert not n.rpc("getwalletinfo", wallet="observer")["private_keys_enabled"]
        assert not n.wallet("getaddressinfo", btc_lock)["ismine"]
        assert n.wallet("getwalletinfo")["private_keys_enabled"]
    result["btc_observer_isolation"] = True
    after = {n.name: balance(n) for n in nodes}
    expected = {a.name: -long["locked_atoms"]-long["funding_fee_atoms"], b.name: long["paid_atoms"],
                y.name: -short["locked_atoms"]-short["funding_fee_atoms"], x.name: short["paid_atoms"]}
    actual = {name: after[name]-before[name] for name in before}
    result.update(legs={"btx": long, "btc": short}, after_atoms=after,
                  expected_delta_atoms=expected, actual_delta_atoms=actual)
    save("reconcile both chains and all balances")
    assert actual == expected
    assert first["refs"]["a"] == ref
    verify_funding_outputs(a, funded_height, terms["lock_commitment"], ref)
    terminal_budgets = {n.name: n.rpc('listswapmandates')['mandates'] for n in (a,b)}
    assert all(row['held_atoms'] == '0' for rows in terminal_budgets.values() for row in rows)
    oldops={n.name:n.rpc('listswapoperations',{'swap_id':sid})['operations'] for n in (a,b)}
    for n in (a,b):
        n.stop();n.start('terminal-restart','-swapnet=1','-wallet=trader','-swapnetwallet=trader',*flags)
        assert view(n)['stage']=='complete'
        assert n.rpc('listswapoperations',{'swap_id':sid})['operations']==oldops[n.name]
        assert n.rpc('listswapmandates')['mandates'] == terminal_budgets[n.name]
    result['terminal_restart_preserved']=True


def terminate(*_):
    raise TimeoutError("outer test timeout")


def main():
    global ROOT, OUT, TEST_HOME, CASE, FIXTURE_EPOCH, MANIFEST
    assert os.environ.get('BTX_PUBLIC_MARKET_EXECUTE') == 'disposable-regtest-only', 'Runtime execution not authorized by this preparation'
    assert platform.system() == 'Darwin' and platform.machine() == 'arm64'
    MANIFEST = json.loads(Path(__file__).with_name('manifest.json').read_text())
    ROOT = Path(sys.argv[1]).resolve()
    OUT = Path(os.environ['BTX_PUBLIC_MARKET_RECORDS']).resolve()
    work = Path(__file__).resolve().parent
    assert ROOT.is_relative_to(work / 'execution') and OUT.is_relative_to(work / 'execution')
    assert ROOT.is_dir() and not any(ROOT.iterdir()) and not ROOT.is_symlink()
    OUT.mkdir(parents=True, exist_ok=False)
    TEST_HOME = ROOT / 'home'
    TEST_HOME.mkdir(mode=0o700)
    CASE = sys.argv[2]
    assert CASE in {'restart', 'refund'}
    FIXTURE_EPOCH = int(time.time()) - 1800
    result.update(status='INCOMPLETE', stage='initialize', case=CASE, source=MANIFEST['source'])
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
    save(f"{CASE} verified")


if __name__ == '__main__':
    main()
