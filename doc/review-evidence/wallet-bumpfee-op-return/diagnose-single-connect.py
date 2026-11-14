import inspect
import json
import os
import runpy
import sys
from pathlib import Path

root = Path(__file__).resolve().parent
run = root / sys.argv[1]
profile = sys.argv[2] if len(sys.argv) == 3 else "default"
assert profile in {"default", "plain-relay", "no-filter"}
plain_relay = profile != "default"
assert run.parent == root and not run.exists()
os.environ.update(
    HOME=str(root / "home"), BTXD=str(root / "bin/btxd"),
    BTXCLI=str(root / "bin/btx-cli"), TEST_RUNNER_PORT_MIN="32000",
)
from test_framework.test_framework import BitcoinTestFramework
from test_framework.test_node import TestNode

start = TestNode.start
wait_rpc = TestNode.wait_for_rpc_connection
sync = BitcoinTestFramework.sync_mempools


def start_local(self, extra_args=None, **kwargs):
    assert self.chain == "regtest" and self.datadir_path.resolve().is_relative_to(run)
    args = list(self.extra_args if extra_args is None else extra_args)
    args.extend(("-regtest=1", "-listen=1", "-autoupdate=0",
                 "-swapnet=0", "-debug=mempool", "-debug=mempoolrej", "-debug=net"))
    if plain_relay:
        args.append("-dandelion=0")
    if profile == "no-filter":
        args.append("-feefilter=0")
    return start(self, args, **kwargs)


def checked_rpc(self, *args, **kwargs):
    wait_rpc(self, *args, **kwargs)
    assert self.getblockchaininfo()["chain"] == "regtest"


def observe_sync(self, nodes=None, *args, **kwargs):
    peers = nodes or self.nodes
    callers = [f"{f.function}:{f.lineno}" for f in inspect.stack()[1:4]]
    self.log.info("Observed sync call %s", callers)
    try:
        return sync(self, nodes, *args, **kwargs)
    except AssertionError:
        snap = {"callers": callers, "nodes": [], "missing": []}
        pools = [set(node.getrawmempool()) for node in peers]
        for node, pool in zip(peers, pools):
            chain = node.getblockchaininfo()
            snap["nodes"].append({"index": node.index, "height": chain["blocks"],
                                  "tip": chain["bestblockhash"], "txids": sorted(pool),
                                  "mempool": node.getmempoolinfo(),
                                  "peers": node.getpeerinfo()})
        for i, sender in enumerate(peers):
            for j, receiver in enumerate(peers):
                if i == j:
                    continue
                missing = pools[i] - pools[j]
                for txid in sorted(missing):
                    entry = {"txid": txid, "sender": sender.index, "receiver": receiver.index}
                    try:
                        entry["entry"] = sender.getmempoolentry(txid)
                        raw = sender.getrawtransaction(txid)
                        entry["decoded"] = sender.decoderawtransaction(raw)
                        entry["admission"] = receiver.testmempoolaccept([raw])
                        ancestors = sender.getmempoolancestors(txid)
                        if ancestors:
                            missing_package = [x for x in ancestors if x in missing] + [txid]
                            if len(missing_package) <= 25:
                                entry["package_admission"] = receiver.testmempoolaccept(
                                    [sender.getrawtransaction(x) for x in missing_package])
                    except Exception as error:
                        entry["probe_error"] = str(error)
                    snap["missing"].append(entry)
        (run / "first-sync-failure.json").write_text(json.dumps(snap, default=str, indent=2))
        raise


TestNode.start = start_local
TestNode.wait_for_rpc_connection = checked_rpc
BitcoinTestFramework.sync_mempools = observe_sync
target = root / "wallet_bumpfee.py"
sys.argv = [str(target), f"--tmpdir={run}", "--nocleanup",
            f"--configfile={root / 'config.ini'}", f"--cachedir={root / 'cache'}",
            "--randomseed=630", f"--portseed={11 if plain_relay else 10}"]
runpy.run_path(str(target), run_name="__main__")
