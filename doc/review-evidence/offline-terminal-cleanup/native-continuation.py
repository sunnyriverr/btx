"""Disposable native regtest run. Evidence omits transaction witnesses and keys."""
import base64
from decimal import Decimal
import json
import os
from pathlib import Path
import secrets
import signal
import sqlite3
import shutil
import socket
import subprocess
import sys
import time
from urllib.error import HTTPError
from urllib.request import Request, urlopen

ROOT = Path(sys.argv[1]).resolve()
OUT = ROOT.parent / (ROOT.name + "-records")
OUT.mkdir(exist_ok=True)
TASK = Path(__file__).resolve().parents[2]
BTX = "521ad0951ed299e9c56aeb7db8188972772067560351b8e55adf71dbed532360"
BTC = "0f9188f13cb7b2c71f2a335e3a4fc328bf5beb436012afca590b1a11466e2206"
BTX_ID, BTC_ID = f"btx:{BTX}:0:native", f"btc:{BTC}:0:native"
HOME = ROOT / "home"
HOME.mkdir(mode=0o700,exist_ok=True)
FIXTURE_EPOCH = int(time.time()) - 1800
CASE = sys.argv[2]
assert CASE in {"candidate", "restart"}
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
        self.data.mkdir(mode=0o700,exist_ok=True)
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
                 "-discover=0", "-txindex=1", *(("-autoupdate=0",) if self.genesis == BTX else ()), *args], stdout=stream, stderr=stream,
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
        assert Path(subprocess.check_output(["ps", "-p", str(self.process.pid), "-o", "comm="], text=True).strip()).resolve() == self.binary.resolve()

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
            if index % 100 == 0:
                free = shutil.disk_usage(TASK).free // 2**20
                assert free >= 1280, f"Disk reserve reached: {free} MiB"
                assert shutil.disk_usage(ROOT).free >= 24*2**20, "Temporary RAM volume reserve reached"
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
    assigned = iter([36136,31136,36137,31137,36236,31236,31237])
    btx_bin = TASK / "venv/bin/btxd-current-cleanup"
    btc_bin = TASK / "embedded-runtime/bitcoin-30.4/bin/bitcoind"
    a, b, x, y = [Node(name, binary, genesis, (36237 if name == "btc-b" else next(assigned), next(assigned)))
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
    if CASE in {"baseline", "candidate"}:
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
    # Native setup failure: remove only the maker's disposable observer wallet.
    # The signing wallet stays loaded, so readiness/key setup succeeds and
    # descriptor import is the failing boundary.
    before_packet_errors = b.rpc("getswapnetworkinfo")["packet_errors"]
    y.rpc("unloadwallet", "observer", False)
    save("accept quote while maker watch wallet is unloaded")
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

    until(lambda: b.rpc("getswapnetworkinfo")["packet_errors"] > before_packet_errors, 20)
    assert not view(b) and view(a)["stage"] == "proposed"
    def budget_snapshot():
        dbpath = b.data / "regtest/swapnet/state.sqlite"
        with sqlite3.connect("file:"+str(dbpath)+"?mode=ro", uri=True) as db:
            return {
                "mandate": list(db.execute("SELECT held,used FROM mandates WHERE id=?", (maker,)).fetchone()),
                "reservations": db.execute("SELECT count(*) FROM reservations").fetchone()[0],
                "claims": db.execute("SELECT count(*) FROM sn_claimed_quotes").fetchone()[0],
                "sessions": db.execute("SELECT count(*) FROM sn_negotiations").fetchone()[0],
            }
    expected_empty = {"mandate":["0","0"],"reservations":0,"claims":0,"sessions":0}
    assert budget_snapshot() == expected_empty, budget_snapshot()
    b.stop()
    assert budget_snapshot() == expected_empty
    y.rpc("loadwallet", "observer")
    b.start("setup-retry", "-swapnet=1", "-wallet=trader", "-swapnetwallet=trader", *flags)
    result["failed_watch_setup"] = {"reached_packet_error":True,"before_restart":expected_empty,
                                    "after_restart":budget_snapshot(),"same_proposal_retry":sid}
    assert budget_snapshot() == expected_empty
    connected(a,b)
    save("watch failure left no reservation; retry after restart")
    save("wait for durable long-leg funding")
    funded = until(lambda: (v if (v := view(a)).get("funding_broadcast") else None), 45)
    assert budget_snapshot() == {"mandate":["40290000","0"],"reservations":1,"claims":1,"sessions":1}, budget_snapshot()
    result["setup_retry_budget"] = budget_snapshot()
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

    if CASE in {"baseline", "candidate"}:
        # Block only terminal budget settlement, leaving the prior refunded
        # stage write durable. Trigger exists only in this disposable fixture.
        dbpath = a.data / "regtest/swapnet/state.sqlite"
        with sqlite3.connect(dbpath) as db:
            db.execute("CREATE TRIGGER fixture_cleanup_stop BEFORE UPDATE OF state ON reservations WHEN NEW.state='closed' BEGIN SELECT RAISE(ABORT,'fixture terminal cleanup interruption'); END")
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
        assert y.rpc("getrawmempool") == [] and x.rpc("getrawmempool") == []
        assert balance(x) == before[x.name] and balance(y) == before[y.name]
        x.stop()
        y.stop()
        result["btc_stopped_at_btx_height"] = a.rpc("getblockcount")
        assert result["btc_stopped_at_btx_height"] == funded_height

        def prove_down():
            for node in (x, y):
                assert node.process.poll() == 0
                with socket.socket() as sock:
                    sock.settimeout(1)
                    assert sock.connect_ex(("127.0.0.1", node.port)) != 0

        prove_down()
        try:
            a.rpc("refundswap", {"swap_id": sid})
        except RPCError as error:
            assert "REFUND_EARLY:" in str(error), error
        else:
            raise AssertionError("early refund accepted with Bitcoin RPC down")
        result["early_refund_offline_rejected"] = True
        save("Bitcoin RPC offline before BTX maturity")
        a.mine(maturity - 1 - funded_height, sinks[a])
        assert a.rpc("getblockcount") == maturity - 1
        assert refund_txid not in a.rpc("getrawmempool")
        assert a.rpc("gettxout", ref["txid"], ref["vout"], True)
        result["refund_early_rejected_at"] = funded_height
        save("mine to contractual maturity with counterparty offline")
        a.mine(1, sinks[a])
        def observation():
            prove_down()
            state = view(a)
            return {"height": a.rpc("getblockcount"), "stage": state["stage"],
                    "last_error": state.get("last_error"), "secret_exposed": state["secret_exposed"],
                    "original_unspent": a.rpc("gettxout", ref["txid"], ref["vout"], True) is not None,
                    "refund_in_mempool": refund_txid in a.rpc("getrawmempool"),
                    "operations": {kind: [op["txid"] for op in operations(a, kind)]
                                   for kind in ("fund", "refund", "claim")}}

        result["at_maturity"] = observation()
        save("observed maturity with Bitcoin offline")
        try:
            until(lambda: refund_txid in a.rpc("getrawmempool"), 15)
            result["broadcast_with_btc_down"] = True
        except TimeoutError:
            result["broadcast_with_btc_down"] = False
        prove_down()
        result["mature_witness"] = observation()
        if result["broadcast_with_btc_down"]:
            result["refund_first_seen_height"] = a.rpc("getblockcount")
            assert result["refund_first_seen_height"] == maturity
        else:
            a.mine(20, sinks[a])
            time.sleep(12)
            witness = observation()
            assert witness["height"] == maturity + 20 and not witness["secret_exposed"]
            assert witness["operations"] == {"fund": [ref["txid"]], "refund": [refund_txid], "claim": []}
            result["maturity_plus_20"] = witness
            save("verified Bitcoin still offline at maturity plus 20")
            assert witness["original_unspent"] and not witness["refund_in_mempool"], "expected baseline refund blockage was not reproduced"
            assert witness["last_error"]["code"] in {"RPC_COOKIE","RPC_UNAVAILABLE"}, witness
            try:
                a.rpc("refundswap", {"swap_id": sid})
            except RPCError as error:
                code = witness["last_error"]["code"]
                assert f"{code}:" in str(error), error
                result["manual_refund_error"] = code
            else:
                raise AssertionError("manual refund did not fail")
            prove_down()
            x.start("rpc-restored", "-wallet=trader", "-wallet=observer", "-wallet=other-signer")
            y.start("rpc-restored", "-wallet=trader", "-wallet=observer", "-wallet=other-signer")
            result["btc_restored_at_btx_height"] = a.rpc("getblockcount")
            save("Bitcoin restored; waiting for original refund")
            until(lambda: refund_txid in a.rpc("getrawmempool"), 30)
            result["refund_first_seen_height"] = a.rpc("getblockcount")
            assert result["refund_first_seen_height"] == maturity + 20
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
        verify_funding_outputs(a, funded_height, terms["lock_commitment"], ref)
        result["refund"] = {"txid": refund_txid, "lock_height": maturity, "payout": destination,
                            "owner_wallet": "trader", "returned_atoms": paid, "funding_fee_atoms": fund_fee,
                            "refund_fee_atoms": refund_fee, "wallet_delta_atoms": balance(a)-before[a.name],
                            "confirmations": tx["confirmations"], "btc_balances_unchanged": True}
        save("refund and wallet ownership verified")
        try:
            until(lambda: view(a)["stage"] == "refunded", 300)
            result["reported_swap_stage"] = "refunded"
        except TimeoutError:
            result["terminal_state_pending"] = True
        assert result.get("reported_swap_stage") == "refunded", "refund did not reach terminal"
        if result["broadcast_with_btc_down"]:
            prove_down()
            def reservation_state():
                with sqlite3.connect("file:"+str(dbpath)+"?mode=ro",uri=True) as db:
                    return db.execute("SELECT state FROM reservations").fetchone()[0]
            assert reservation_state() == "funded"
            assert view(a)["stage"] == "refunded"
            # Exact persisted gap is established by SQLite abort. Abruptly kill
            # the native process, then restart from the same on-disk journal.
            # Persist chainstate/block index too, so abrupt restart tests
            # cleanup rather than accidentally discarding the refund block.
            a.rpc("gettxoutsetinfo")
            flushed_tip = a.rpc("getbestblockhash")
            flushed_height = a.rpc("getblockcount")
            a.process.kill()
            assert a.process.wait(timeout=15) == -9
            result["interruption"] = {"fault":"SQLite terminal update abort, followed by native SIGKILL",
                "stage":"refunded","reservation":"funded","bitcoin_down":True}
            # Saved BTC driver qualification requires Bitcoin available at boot.
            # Keep the cleanup trigger active throughout qualification, then
            # stop Bitcoin again before permitting cleanup to execute.
            x.start("restart-qualification", "-wallet=trader", "-wallet=observer", "-wallet=other-signer")
            y.start("restart-qualification", "-wallet=trader", "-wallet=observer", "-wallet=other-signer")
            a.start("cleanup-restart", "-swapnet=1", "-wallet=trader", "-swapnetwallet=trader", *flags)
            assert a.rpc("getbestblockhash") == flushed_tip
            assert a.rpc("getblockcount") == flushed_height
            assert a.rpc("getrawtransaction",refund_txid,True)["confirmations"] >= 20
            result["flushed_restart_tip"] = {"hash":flushed_tip,"height":flushed_height}
            assert reservation_state() == "funded"
            x.stop();y.stop();prove_down()
            with sqlite3.connect(dbpath) as db:
                db.execute("DROP TRIGGER fixture_cleanup_stop")
            until(lambda: reservation_state() == "closed", 20)
            prove_down()
            assert view(a)["stage"] == "refunded"
            assert [op["txid"] for op in operations(a,"fund")] == [ref["txid"]]
            assert [op["txid"] for op in operations(a,"refund")] == [refund_txid]
            assert not operations(a,"claim")
            with sqlite3.connect("file:"+str(dbpath)+"?mode=ro",uri=True) as db:
                budget = db.execute("SELECT held,used FROM mandates").fetchall()
                grants = db.execute("SELECT consumed FROM sn_grants").fetchall()
            assert budget and all(held=="0" and int(used)>0 for held,used in budget)
            assert grants == [(1,)]
            time.sleep(3)
            assert reservation_state()=="closed"
            result["cleanup_restart"] = {"stage":"refunded","reservation":"closed",
                "bitcoin_down_at_cleanup":True,"bitcoin_available_during_boot":True,
                "mandate_budget":budget,"grant_consumed":grants,"same_funding_refund_ops":True}
            save("native interruption/restart cleanup verified with Bitcoin stopped again")
            result["refunded_with_btc_down"] = True
            save("wallet refund confirmed while Bitcoin RPC still down")
            x.start("rpc-restored", "-wallet=trader", "-wallet=observer", "-wallet=other-signer")
            y.start("rpc-restored", "-wallet=trader", "-wallet=observer", "-wallet=other-signer")
        assert all(balance(n) == before[n.name] for n in (x, y))
        assert result["broadcast_with_btc_down"] == (CASE == "candidate"), result["mature_witness"]
        result["verdict"] = "REFUNDED_OFFLINE" if result["broadcast_with_btc_down"] else "BLOCKED_UNTIL_RESTORE"
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



# Continue the same genuinely negotiated native swap after the resource pause.
a=Node('btx-a',TASK/'venv/bin/btxd-current-cleanup',BTX,(36136,31136))
x=Node('btc-a',TASK/'embedded-runtime/bitcoin-30.4/bin/bitcoind',BTC,(36236,31236))
y=Node('btc-b',TASK/'embedded-runtime/bitcoin-30.4/bin/bitcoind',BTC,(36237,31237))
flags=('-autoshieldcoinbase=0','-regtestmatmulbindingheight=2147483647','-regtestmatmulproductdigestheight=2147483647','-regtestmatmulv4height=2147483647','-regtestmatmulrequireproductpayload=0')
dbpath=a.data/'regtest/swapnet/state.sqlite'
result={'status':'INCOMPLETE','scope':'continuation of actual negotiated current-head swap after disk reserve pause'}
def snapshot():
 with sqlite3.connect('file:'+str(dbpath)+'?mode=ro',uri=True) as db:
  sid,raw=db.execute('SELECT id,body FROM sn_negotiations').fetchone()
  body=json.loads(raw)
  return {'sid':sid,'body':body,'reservation':db.execute('SELECT state FROM reservations').fetchone()[0],
   'budget':db.execute('SELECT held,used FROM mandates').fetchall(),'consumed':db.execute('SELECT consumed FROM sn_grants').fetchall(),
   'operations':db.execute('SELECT kind,txid FROM sn_operations ORDER BY kind').fetchall()}
try:
 for n in (x,y):n.start('continuation-qualification','-wallet=trader','-wallet=observer','-wallet=other-signer')
 a.start('continuation-confirm','-swapnet=1','-wallet=trader','-swapnetwallet=trader',*flags)
 original=snapshot();assert original['reservation']=='funded'
 assert [kind for kind,tx in original['operations']]==['fund','refund']
 refund=dict(original['operations'])['refund'];fund=dict(original['operations'])['fund']
 assert original['body']['refs']['a']['txid']==fund
 x.stop();y.stop()
 until(lambda:a.rpc('getrawtransaction',refund,True).get('confirmations',0)>0 or refund in a.rpc('getrawmempool'),20)
 tip=a.rpc('getblock',a.rpc('getbestblockhash'),2)
 sink=next(v['scriptPubKey']['address'] for v in tip['tx'][0]['vout'] if v['value']>0 and 'address' in v['scriptPubKey'])
 assert not a.wallet('getaddressinfo',sink)['ismine']
 conf=a.rpc('getrawtransaction',refund,True).get('confirmations',0)
 a.mine(max(0,20-conf),sink)
 until(lambda:snapshot()['body']['stage']=='refunded',20)
 before=snapshot();assert before['reservation']=='funded'
 # Trigger must still block closure, proving this is the persisted retry gap.
 with sqlite3.connect(dbpath) as db:assert db.execute("SELECT 1 FROM sqlite_master WHERE type='trigger' AND name='fixture_cleanup_stop'").fetchone()
 a.rpc('gettxoutsetinfo');flushed_tip=a.rpc('getbestblockhash')
 assert a.rpc('getrawtransaction',refund,True)['confirmations']>=20
 a.process.kill();assert a.process.wait(timeout=15)==-9
 for n in (x,y):n.start('restart-qualification','-wallet=trader','-wallet=observer','-wallet=other-signer')
 a.start('cleanup-restart','-swapnet=1','-wallet=trader','-swapnetwallet=trader',*flags)
 assert a.rpc('getbestblockhash')==flushed_tip
 assert a.rpc('getrawtransaction',refund,True)['confirmations']>=20
 assert snapshot()['reservation']=='funded'
 x.stop();y.stop()
 with sqlite3.connect(dbpath) as db:db.execute('DROP TRIGGER fixture_cleanup_stop')
 until(lambda:snapshot()['reservation']=='closed',20)
 after=snapshot();assert after['body']['stage']=='refunded'
 assert after['operations']==before['operations']
 assert all(held=='0' and int(used)>0 for held,used in after['budget'])
 assert after['consumed']==[(1,)]
 time.sleep(3)
 assert snapshot()['budget']==after['budget'] and snapshot()['operations']==after['operations']
 assert all(n.process.poll()==0 for n in (x,y))
 tx=a.rpc('getrawtransaction',refund,True);terms=after['body']['agreement']['long_leg'];ref=after['body']['refs']['a']
 assert (tx['vin'][0]['txid'],tx['vin'][0]['vout'])==(ref['txid'],ref['vout'])
 assert tx['vout'][0]['scriptPubKey']['address']==terms['refund_payout']
 assert a.wallet('getaddressinfo',terms['refund_payout'])['ismine']
 result.update(status='PASS',base='cb823a94',flushed_tip=flushed_tip,native_sigkill_exit=-9,
   before={'stage':before['body']['stage'],'reservation':before['reservation']},
   after={'stage':after['body']['stage'],'reservation':after['reservation'],'budget':after['budget'],'consumed':after['consumed']},
   operations=after['operations'],refund_confirmations=tx['confirmations'],payout_owner=True,
   bitcoin_available_at_boot=True,bitcoin_stopped_before_cleanup=True)
 save('current-head native cleanup interruption/restart verified')
except Exception as error:
 result.update(status='FAIL',error=f'{type(error).__name__}: {error}');save('continuation failed');raise
finally:
 errors=[]
 for n in reversed(nodes):
  try:n.stop()
  except Exception as error:errors.append(str(error))
 result['cleanup_errors']=errors
 (OUT/'continuation-result.json').write_text(json.dumps(result,indent=2,default=str)+'\n')
