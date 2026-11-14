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
assert mode in {"baseline", "candidate", "candidate-durable"}
test_path = functional / "wallet_htlc_atomicswap.py"
runtime = root / "runtime" / (sys.argv[2] if len(sys.argv) > 2 else mode)
assert runtime.parent == root / "runtime"
runtime.parent.mkdir(exist_ok=True)
private_home = root / "runtime/home"
private_home.mkdir(exist_ok=True)
os.environ.update(
    HOME=str(private_home),
    BTXD=str(root / ("venv/bin/btxd-baseline" if mode == "baseline" else "venv/bin/btxd-embedded-candidate")),
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
    args.extend(("-regtest=1", "-listen=1", "-connect=0", "-autoupdate=0", "-txindex=1"))
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
        if mode == "candidate-durable":
            # Seed a prepared record without session flags to model an
            # interruption after operation insertion but before state update.
            journal.prepare(sid, short_leg.asset, "fund", "88" * 32, "00")
        store.verify_audit()
    finally:
        store.close()
    return sid, state["reservation_id"]


def run_case(self, btc):
    node = self.nodes[0]
    sender, mine_addr = create_bridge_wallet(self, node, "refund_sender", Decimal("12"))
    node.createwallet("maker", descriptors=True)
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
               "rpc_url":btc.url,"cookie_path":str(btc.cookie_path),"wallet":"trade","confirmations":6}
    sid, rid = seeded_maker_state(self, node, terms, ref, bitcoin)
    args = [*self.extra_args[0],"-wallet=maker","-wallet=refund_sender","-swapnet=1","-swapnetwallet=maker"]
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
    ops = node.listswapoperations({"swap_id": sid})["operations"]
    assert [op["kind"] for op in ops] == (["fund"] if mode == "candidate-durable" else [])
    assert not state["funding_prepared"] and not state["funding_broadcast"]
    self.log.info("EMBEDDED_REFUND_AFTER_RESTART depth=20 stage=%s action=%s maker_operations=%d",
                  state["stage"],state["last_action"],len(ops))
    if mode == "candidate":
        # Restart again and remove the refund block and all descendants. The
        # old agreement must stay inert even after the actual chain rewinds.
        self.restart_node(0, extra_args=args)
        assert view()["stage"] == "cancelled"
        node.invalidateblock(raw["blockhash"])
        assert node.getblockheader(raw["blockhash"])["confirmations"] == -1
        node.resumeswap({"swap_id": sid})
        assert view()["stage"] == "cancelled"
        assert node.listswapoperations({"swap_id": sid})["operations"] == []
        self.log.info("EMBEDDED_REORG_AFTER_SECOND_RESTART stage=cancelled maker_operations=0")

    # Query the real admission gate against the database after clean shutdown.
    # This verifies capacity through embedded recovery. No peer proposal is sent.
    self.stop_node(0)
    store = Store(node.datadir_path/"regtest/swapnet/state.sqlite")
    try:
        journal = Journal(store)
        reservation = store.db.execute("SELECT state FROM reservations WHERE id=?",(rid,)).fetchone()[0]
        assert reservation == ("closed" if closes else "held")
        grant = store.db.execute("SELECT consumed,revoked FROM sn_grants WHERE id=?",
                                 (state["grant_id"],)).fetchone()
        assert grant == (0, int(closes))
        assert store.verify_audit()
        self.log.info("EMBEDDED_DURABLE_STATE reservation=%s grant_consumed=%d grant_revoked=%d",
                      reservation, *grant)
        for n in range(1,128):
            journal.save(f"{n:064x}", {"stage":"committed","principal":"fixture","peer":"fixture"})
        try:
            journal.ensure_capacity()
        except SwapError as e:
            assert not closes and e.code == "ACTIVE_LIMIT"
            self.log.info("EMBEDDED_RECOVERY_CAPACITY ACTIVE_LIMIT")
        else:
            assert closes
            self.log.info("EMBEDDED_RECOVERY_CAPACITY available")
    finally:
        store.close()


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
            wallet = LocalRPC(btc.url+"/wallet/trade",cookie_path=btc.cookie_path)
            btc("generatetoaddress",2,wallet("getnewaddress"))
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

WalletHtlcAtomicSwapTest.run_test = native_refund
WalletHtlcAtomicSwapTest(str(functional/"wallet_htlc_atomicswap.py")).main()
