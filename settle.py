"""Disposable native regtest run. Evidence omits transaction witnesses and keys."""
import base64
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
OUT = Path("records").resolve()
BTX = "521ad0951ed299e9c56aeb7db8188972772067560351b8e55adf71dbed532360"
BTC = "0f9188f13cb7b2c71f2a335e3a4fc328bf5beb436012afca590b1a11466e2206"
BTX_ID, BTC_ID = f"btx:{BTX}:0:native", f"btc:{BTC}:0:native"
HOME = ROOT / "home"
HOME.mkdir(mode=0o700)
FIXTURE_EPOCH = int(time.time()) - 1800
CASE = sys.argv[2]
assert CASE in {"restart", "refund"}
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
    assigned = iter(ports(7))
    btx_bin = Path("payload/bin/btxd").resolve()
    btc_bin = ROOT / "bitcoin-30.4/bin/bitcoind"
    a, b, x, y = [Node(name, binary, genesis, (18443 if name == "btc-b" else next(assigned), next(assigned)))
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
        for invalid in ("trader", "missing", "other-signer"):
            try:
                n.rpc("setswapassetpolicy", {"policy": {**policy, "watch_wallet": invalid}})
            except RPCError as error:
                assert "WATCH_WALLET:" in str(error), error
            else:
                raise AssertionError("invalid watch wallet accepted")
        policy["watch_wallet"] = "observer"
        n.rpc("setswapassetpolicy", {"policy": policy})
        assert {v["asset"] for v in n.rpc("listswapassets")["assets"] if v["ready"]} == {BTX_ID, BTC_ID}
    before = {n.name: balance(n) for n in nodes}
    result["before_atoms"] = before
    assert before[a.name] >= 20_000_000 and before[y.name] >= 40_000_000
    assert before[b.name] == before[x.name] == 0
    fee_cap = 300_000
    def mandate(n, asset, cap):
        return n.rpc("createswapmandate", {"mandate": {"principal": "owner:cookie",
                     "asset": asset, "max_total_atoms": str(cap), "max_trade_atoms": str(cap),
                     "max_fee_atoms": str(fee_cap), "expires_at": int(time.time()) + 900,
                     "nonce": secrets.token_hex(32)}})["mandate_id"]
    save("advertise maker and request exact quote")
    maker = mandate(b, BTC_ID, 50_000_000)
    taker = mandate(a, BTX_ID, 25_000_000)
    b.rpc("setswapmarket", {"market": {"sell_asset": BTX_ID, "buy_asset": BTC_ID,
          "numerator": "2", "denominator": "1", "maker_fee_atoms": "10000",
          "max_receive_network_fee_atoms": "10000", "max_input_atoms": "25000000",
          "expires_at": int(time.time()) + 600}, "mandate_id": maker,
          "max_local_fee_atoms": str(fee_cap), "refund_fee_atoms": "10000", "claim_fee_atoms": "18000"})
    until(lambda: a.rpc("listswapproviders")["providers"])
    rfq = a.rpc("requestswapquote", {"sell_asset": BTX_ID, "buy_asset": BTC_ID, "sell_atoms": "20000000"})
    quotes = until(lambda: a.rpc("getswapquotes", {"request_id": rfq["request_id"]})["quotes"], 40)
    quote = quotes[0]
    assert len(quotes) == 1 and quote["sell_atoms"] == "20000000" and quote["buy_atoms"] == "40000000"
    result["quote"] = {"id": quote["id"], "sell_atoms": quote["sell_atoms"], "buy_atoms": quote["buy_atoms"],
                       "maker_fee_atoms": quote["maker_fee_atoms"]}
    save("accept exact quote")
    accepted = a.rpc("acceptswapquote", {"quote_id": quote["id"], "mandate_id": taker,
                      "max_local_fee_atoms": str(fee_cap), "refund_fee_atoms": "18000",
                      "claim_fee_atoms": "10000"})
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
        assert BTC_ID not in n.rpc("getswapwalletinfo")["startup_errors"]
        assert {v["asset"] for v in n.rpc("listswapassets")["assets"] if v["ready"]} == {BTX_ID, BTC_ID}
    assert view(a)["refs"]["a"] == ref
    assert [op["txid"] for op in operations(a, "fund")] == [ref["txid"]]
    assert a.rpc("gettxout", ref["txid"], ref["vout"], False)["confirmations"] == 1
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
save(f"{CASE} verified")
