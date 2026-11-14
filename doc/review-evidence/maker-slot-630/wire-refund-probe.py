"""Observe a native BTX refund in the embedded SwapNet coordinator on regtest."""
import os
from pathlib import Path
import sys

root = Path(__file__).resolve().parent
send = root.parent / "wallet-sendall-acceptance"
functional = send / "source/test/functional"
package = "native-baseline-source" if sys.argv[1] == "baseline" else "source"
sys.path[:0] = [str(root/package/"contrib/swapnet"), str(root/"source/contrib/swapnet/tests")]
sys.path.insert(0, str(functional))

mode = sys.argv[1]
assert mode in {"baseline", "candidate"}
test_path = functional / "wallet_htlc_atomicswap.py"
runtime = root / "runtime" / (sys.argv[2] if len(sys.argv) > 2 else mode)
assert runtime.parent == root / "runtime"
runtime.parent.mkdir(exist_ok=True)
private_home = root / "runtime/home"
private_home.mkdir(exist_ok=True)
os.environ.update(
    HOME=str(private_home),
    BTXD=str(root / ("venv/bin/btxd-wire-stock" if mode == "baseline" else "venv/bin/btxd-wire-patched")),
    BTXCLI=str(send / "build/bin/btx-cli"),
    TEST_RUNNER_PORT_MIN="31100",
)
from test_framework.test_node import TestNode

start = TestNode.start
wait_for_rpc = TestNode.wait_for_rpc_connection

def start_local(self, extra_args=None, **kwargs):
    assert self.chain == "regtest"
    assert self.datadir_path.resolve().is_relative_to(runtime.resolve())
    assert self.bitcoinconf.read_text().splitlines()[0] == "regtest=1"
    args = list(self.extra_args if extra_args is None else extra_args)
    assert "bind=127.0.0.1" in self.bitcoinconf.read_text().splitlines()
    args = [arg for arg in args if arg != "-modelbind=off"]
    args.extend(("-regtest=1", "-listen=1", "-autoupdate=0", "-txindex=1"))
    return start(self, args, **kwargs)

def check_chain(self, *args, **kwargs):
    wait_for_rpc(self, *args, **kwargs)
    assert self.rpc.getblockchaininfo()["chain"] == "regtest"

TestNode.start = start_local
TestNode.wait_for_rpc_connection = check_chain
sys.argv = [str(test_path), f"--tmpdir={runtime}", "--nocleanup",
            f"--configfile={send / 'build/test/config.ini'}", "--randomseed=630", "--portseed=3"]


from dataclasses import asdict, replace
from decimal import Decimal
from hashlib import sha256
import secrets
import shutil
import subprocess
import time
from swapnet.errors import SwapError
from swapnet.journal import Journal
from swapnet.rpcclient import LocalRPC
from swapnet.store import Store
from swapnet.terms import Agreement, LegTerms
from test_execution_v2 import Pair
from wallet_htlc_atomicswap import WalletHtlcAtomicSwapTest, create_bridge_wallet, mine_block


def seeded_maker_state(self, node, long_leg, ref, bitcoin):
    """Seed the committed negotiation only; all chain observation runs in btxd."""
    folder = runtime / "fixture"
    folder.mkdir()
    pair = Pair(folder)
    try:
        pair.start()
        pair.deliver()
        _, state = pair.nodes["bob"][1].load(pair.sid)
        assert state["stage"] == "committed"
        agreement = Agreement.parse(state["agreement"])
        short_leg = replace(agreement.short_leg, asset=bitcoin["asset"], hashlock=long_leg.hashlock)
        agreement = replace(agreement, network=node.getblockhash(0), long_leg=long_leg, short_leg=short_leg)
        state.update(agreement=asdict(agreement), agreement_id=agreement.id, refs={"a":ref})
        sid = pair.sid
    finally:
        for name in pair.nodes:
            pair.close(name)
    destination = node.datadir_path / "regtest/swapnet"
    destination.mkdir(mode=0o700, exist_ok=True)
    shutil.copy2(folder/"bob/state.db", destination/"state.sqlite")
    store = Store(destination/"state.sqlite")
    try:
        journal = Journal(store)
        journal.set_setting("asset_policies", {bitcoin["asset"]:bitcoin})
        rev, _ = journal.load(sid)
        # Rebind the fixture grant to the exact agreement and local BTC asset.
        # This database is prepared with SwapNet disabled, before the daemon
        # starts observing the actual transaction or exercises the release.
        from swapnet.journal import local_dump, local_load
        from swapnet.authorization import Grant
        with store.transaction() as db:
            old_id = state["grant_id"]
            grant = local_load(db.execute("SELECT body FROM sn_grants WHERE id=?", (old_id,)).fetchone()[0])
            grant.update(agreement_id=agreement.id,asset=short_leg.asset)
            new_id = Grant(**grant).id
            db.execute("UPDATE sn_grants SET id=?,body=? WHERE id=?", (new_id,local_dump(grant),old_id))
            state["grant_id"] = new_id
            db.execute("UPDATE sn_negotiations SET revision=?,body=? WHERE id=?", (rev+1,local_dump(state),sid))
        store.verify_audit()
    finally:
        store.close()
    return sid, state["reservation_id"]


def run_case(self, btc):
    node, taker = self.nodes
    sender, mine_addr = create_bridge_wallet(self, node, "refund_sender", Decimal("12"))
    node.createwallet("maker", descriptors=True)
    taker.createwallet("taker", descriptors=True)
    maker_wallet = node.get_wallet_rpc("maker")
    locktime = node.getblockcount() + 6
    lock_hash = sha256(b"regtest-only-refund").hexdigest()
    claim_key, refund_key = self.pq_pubkey(maker_wallet), self.pq_pubkey(sender)
    desc, addr = self.build_htlc_descriptor(node, lock_hash, claim_key, locktime, refund_key)
    assert sender.importdescriptors([{"desc":desc,"timestamp":"now","internal":False}])[0]["success"]
    txid, vout, value = self.fund_lock(sender, node, mine_addr, addr, Decimal("2"))
    recipient = sender.getnewaddress()
    terms = LegTerms("btx:"+node.getblockhash(0)+":0:native", str(int(value*10**8)), lock_hash,
                     claim_key, refund_key, maker_wallet.getnewaddress(), recipient,
                     "height", locktime, node.validateaddress(addr)["scriptPubKey"], "10000", "10000")
    ref = {"txid":txid,"vout":vout}
    refund = sender.buildhtlcrefund(desc, ref, recipient, locktime, 10000)
    assert refund["complete"]
    bitcoin = {"asset":"btc:"+btc("getblockhash",0)+":0:native",
               "rpc_url":btc.url,"cookie_path":str(btc.cookie_path),"wallet":"trade","watch_wallet":"maker_watch","confirmations":6}
    sid, rid = seeded_maker_state(self, node, terms, ref, bitcoin)
    args = [*self.extra_args[0][:-1],"-wallet=maker","-wallet=refund_sender","-swapnet=1","-swapnetwallet=maker"]
    self.restart_node(0, extra_args=args)
    assert node.getswapnetworkinfo()["in_process"] is True
    assert {a["asset"] for a in node.listswapassets()["assets"] if a["ready"]} == {terms.asset,bitcoin["asset"]}
    self.log.info("EMBEDDED_CHAINS ready=BTX,BTC bitcoin_height=%d", btc("getblockcount"))
    mine_block(self,node,mine_addr,locktime-node.getblockcount())
    tx = node.sendrawtransaction(refund["hex"])

    def view():
        return node.getswap({"swap_id": sid})

    def observed(conf):
        state = view()
        obs = state.get("observations",{}).get("a",{})
        return obs.get("refunded") is True and obs.get("confirmations") == conf and obs.get("canonical") is True

    self.wait_until(lambda: observed(0), timeout=10)
    assert view()["stage"] == "committed"
    self.log.info("EMBEDDED_REFUND_UNCONFIRMED committed")
    mine_block(self,node,mine_addr,19)
    self.wait_until(lambda: observed(19), timeout=10)
    assert view()["stage"] == "committed"
    self.log.info("EMBEDDED_REFUND_BELOW_THRESHOLD committed at 19 confirmations")
    self.restart_node(0, extra_args=args)
    self.wait_until(lambda: observed(19), timeout=10)
    assert view()["stage"] == "committed"
    mine_block(self,node,mine_addr,1)
    raw = node.getrawtransaction(tx,True)
    assert raw["confirmations"] == 20 and (raw["vin"][0]["txid"],raw["vin"][0]["vout"]) == (txid,vout)
    self.wait_until(lambda: observed(20),timeout=10)
    state = view()
    closes = mode == "candidate"
    assert state["stage"] == ("cancelled" if closes else "committed"), state["stage"]
    assert node.listswapoperations({"swap_id":sid})["operations"] == []
    self.log.info("WIRE_REFUND depth=20 maker_stage=%s",state["stage"])

    # Fill the other slots while the maker is shut down. Seed only the old
    # agreement and placeholder occupancy. Every part of the fresh agreement
    # below travels through the two native peers.
    self.stop_node(0)
    db_path = node.datadir_path/"regtest/swapnet/state.sqlite"
    filler = [f"{n:064x}" for n in range(1,128)]

    def occupancy(*, seed=False, free_one=False):
        store = Store(db_path)
        try:
            journal = Journal(store)
            if seed:
                for row in filler:
                    journal.save(row, {"stage":"committed","principal":"fixture","peer":"fixture"})
            if free_one:
                with store.transaction() as db:
                    db.execute("DELETE FROM sn_negotiations WHERE id=?", (filler[-1],))
            count = store.db.execute(
                "SELECT count(*) FROM sn_negotiations WHERE stage NOT IN ('complete','refunded','cancelled','rejected')"
            ).fetchone()[0]
            store.verify_audit()
            return count
        finally:
            store.close()

    active = occupancy(seed=True)
    assert active == (127 if closes else 128)
    self.log.info("WIRE_START_OCCUPANCY active=%d",active)
    self.start_node(0, extra_args=args)
    taker_args = [*self.extra_args[1][:-1],"-wallet=taker","-swapnet=1","-swapnetwallet=taker"]
    self.restart_node(1, extra_args=taker_args)
    taker.setswapassetpolicy({"policy":{**bitcoin, "wallet":"taker_trade", "watch_wallet":"taker_watch"}})

    def connect():
        # Use an outbound connection from the quote requester. The framework
        # configuration already specifies connect=0 once.
        self.connect_nodes(1,0)
        self.wait_until(lambda: all(peer.getswapbootstrapinfo()["admitted_peers"] == 1
                                   for peer in (node,taker)), timeout=15)
        self.sync_blocks(timeout=30)

    connect()
    for peer in (node,taker):
        assert peer.getswapnetworkinfo()["in_process"]
        assert {a["asset"] for a in peer.listswapassets()["assets"] if a["ready"]} == {terms.asset,bitcoin["asset"]}
    assert view()["stage"] == state["stage"]
    self.log.info("WIRE_PEERS admitted=1_per_node same_btx_tip=true")

    fee = "300000"
    def mandate(peer, asset, cap):
        return peer.createswapmandate({"mandate":{"principal":"owner:cookie","asset":asset,
            "max_total_atoms":cap,"max_trade_atoms":cap,"max_fee_atoms":fee,
            "expires_at":int(time.time())+900,"nonce":secrets.token_hex(32)}})["mandate_id"]

    maker_mid = mandate(node,bitcoin["asset"],"50000000")
    taker_mid = mandate(taker,terms.asset,"25000000")
    node.setswapmarket({"market":{"sell_asset":terms.asset,"buy_asset":bitcoin["asset"],
        "numerator":"2","denominator":"1","maker_fee_atoms":"10000",
        "max_receive_network_fee_atoms":"10000","max_input_atoms":"25000000",
        "expires_at":int(time.time())+600},"mandate_id":maker_mid,
        "max_local_fee_atoms":fee,"refund_fee_atoms":"10000","claim_fee_atoms":"18000"})
    assert node.publishswapprovider()["advertised"]
    self.wait_until(lambda:taker.listswapproviders()["providers"],timeout=10)
    rfq = taker.requestswapquote({"sell_asset":terms.asset,"buy_asset":bitcoin["asset"],"sell_atoms":"20000000"})
    def quotes():
        return taker.getswapquotes({"request_id":rfq["request_id"]})["quotes"]
    self.wait_until(quotes,timeout=10)
    quote, = quotes()
    assert (quote["sell_atoms"],quote["buy_atoms"]) == ("20000000","40000000")

    def wire_count(peer, direction):
        info, = peer.getpeerinfo()
        return info[direction].get("swterms",0)
    before = wire_count(node,"bytesrecv_per_msg")
    errors = node.getswapnetworkinfo()["packet_errors"]
    proposal = taker.acceptswapquote({"quote_id":quote["id"],"mandate_id":taker_mid,
        "max_local_fee_atoms":fee,"refund_fee_atoms":"18000","claim_fee_atoms":"10000"})
    fresh = proposal["swap_id"]
    assert fresh != sid and proposal["stage"] == "proposed"
    self.wait_until(lambda:wire_count(node,"bytesrecv_per_msg") > before,timeout=10)
    self.log.info("WIRE_PROPOSAL_RECEIVED swap=%s bytes=%d",fresh,wire_count(node,"bytesrecv_per_msg")-before)

    def lookup(peer):
        return next((s for s in peer.listswaps({"limit":512})["swaps"] if s["swap_id"] == fresh),None)

    if not closes:
        self.wait_until(lambda:node.getswapnetworkinfo()["packet_errors"] > errors,timeout=10)
        assert lookup(node) is None and lookup(taker)["stage"] == "proposed"
        self.log.info("WIRE_FULL_GATE received=true packet_error=true maker_record=absent taker_stage=proposed")
        # Restart after removing one placeholder while the same signed
        # proposal is pending. The taker's native outbox retries it.
        self.stop_node(0)
        assert occupancy(free_one=True) == 127
        self.start_node(0, extra_args=args)
        connect()

    self.wait_until(lambda:(lookup(node) or {}).get("stage") in {"offered","committed"},timeout=12)
    remote = lookup(node)
    self.wait_until(lambda:lookup(taker).get("agreement") == remote["agreement"],timeout=12)
    self.wait_until(lambda:(lookup(node) or {}).get("stage") == "committed",timeout=12)
    assert remote["role"] == "responder"
    assert lookup(taker)["agreement_id"] == remote["agreement_id"]
    assert view()["stage"] == state["stage"]
    self.log.info("WIRE_ACCEPTED swap=%s maker_stage=committed same_agreement=true stock_slot_control=%s",
                  fresh,not closes)
    self.stop_node(0)
    assert occupancy() == 128


def native_refund(self):
    btcdata = runtime/"btc"
    btcdata.mkdir(mode=0o700)
    binary = root/"embedded-runtime/bitcoin-30.4/bin/bitcoind"
    with (runtime/"bitcoin-core.log").open("w") as log:
        process = subprocess.Popen([str(binary),"-regtest=1",f"-datadir={btcdata}",
            "-rpcport=36236","-port=31236","-listen=0","-connect=0","-dnsseed=0",
            "-fallbackfee=0.0002"],stdout=log,stderr=log)
        btc = LocalRPC("http://127.0.0.1:36236",cookie_path=btcdata/"regtest/.cookie")
        try:
            for _ in range(80):
                assert process.poll() is None
                try:
                    if btc("getblockchaininfo")["chain"] == "regtest":
                        break
                except SwapError:
                    time.sleep(0.1)
            else:
                raise RuntimeError("Bitcoin Core regtest startup timed out")
            btc("createwallet","trade")
            btc("createwallet","maker_watch",True,True)
            btc("createwallet","taker_trade")
            btc("createwallet","taker_watch",True,True)
            wallet = LocalRPC(btc.url+"/wallet/trade",cookie_path=btc.cookie_path)
            btc("generatetoaddress",108,wallet("getnewaddress"))
            assert btc("getblockchaininfo")["initialblockdownload"] is False
            run_case(self, btc)
        finally:
            if process.poll() is None:
                try:
                    btc("stop")
                    process.wait(timeout=15)
                except (SwapError,subprocess.TimeoutExpired):
                    process.terminate()
                    process.wait(timeout=15)

set_single_node_params = WalletHtlcAtomicSwapTest.set_test_params

def set_two_node_params(self):
    set_single_node_params(self)
    self.num_nodes = 2
    self.extra_args = [[*self.extra_args[0], "-swapnet=0"] for _ in range(2)]

def disconnected_setup(self):
    self.setup_nodes()

WalletHtlcAtomicSwapTest.set_test_params = set_two_node_params
WalletHtlcAtomicSwapTest.setup_network = disconnected_setup
WalletHtlcAtomicSwapTest.run_test = native_refund
WalletHtlcAtomicSwapTest(str(functional/"wallet_htlc_atomicswap.py")).main()
