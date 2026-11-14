"""Run BTX's maintained sendall functional test with local-only node settings."""
import os
from pathlib import Path
import runpy
import sys

root = Path(__file__).resolve().parent
functional = root / "source/test/functional"
sys.path.insert(0, str(functional))

mode = sys.argv[1]
assert mode in {"baseline", "candidate", "funding-probe"}
test_path = (
    functional / "wallet_sendall.py" if mode != "candidate"
    else root / "candidate/wallet_sendall.py"
)
runtime = root / "runtime" / (sys.argv[2] if len(sys.argv) > 2 else mode)
assert runtime.parent == root / "runtime"
runtime.parent.mkdir(exist_ok=True)
private_home = root / "runtime/home"
private_home.mkdir(exist_ok=True)
os.environ.update(
    HOME=str(private_home),
    BTXD=str(root / ("baseline-bin/btxd" if mode == "baseline" else "build/bin/btxd")),
    BTXCLI=str(root / "build/bin/btx-cli"),
    TEST_RUNNER_PORT_MIN="31000",
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
    args.extend(("-regtest=1", "-listen=1", "-connect=0", "-autoupdate=0", "-swapnet=0"))
    return start(self, args, **kwargs)

def check_chain(self, *args, **kwargs):
    wait_for_rpc(self, *args, **kwargs)
    assert self.rpc.getblockchaininfo()["chain"] == "regtest"

TestNode.start = start_local
TestNode.wait_for_rpc_connection = check_chain
sys.argv = [str(test_path), f"--tmpdir={runtime}", "--nocleanup",
            f"--configfile={root / 'build/test/config.ini'}", "--randomseed=630", "--portseed=3"]

from test_framework.test_framework import BitcoinTestFramework

class SizingReview(BitcoinTestFramework):
    def add_options(self, parser):
        self.add_wallet_options(parser)

    def set_test_params(self):
        self.num_nodes = 1
        self.setup_clean_chain = True

    def run_test(self):
        node = self.nodes[0]
        node.createwallet("sizing", descriptors=True)
        wallet = node.get_wallet_rpc("sizing")
        self.generatetoaddress(node, 101, wallet.getnewaddress())
        inputs = wallet.listunspent()
        assert len(inputs) == 1, inputs
        recipient = wallet.getnewaddress()
        observed = []
        for preferred in (None, "slh_dsa_128s"):
            opts = {"add_to_wallet": False}
            if preferred:
                opts["preferred_pq_algo"] = preferred
            result = wallet.sendall([recipient], fee_rate=1, options=opts)
            assert result["complete"]
            tx = node.decoderawtransaction(result["hex"])
            assert len(tx["vin"]) == len(tx["vout"]) == 1
            assert tx["vin"][0]["txid"] == inputs[0]["txid"]
            assert tx["vout"][0]["scriptPubKey"]["address"] == recipient
            self.log.info("requested=%s fee=%s signed_vsize=%s witness_element_bytes=%s", preferred,
                          inputs[0]["amount"]-tx["vout"][0]["value"], tx["vsize"],
                          [len(item)//2 for item in tx["vin"][0]["txinwitness"]])
            observed.append((inputs[0]["amount"] - tx["vout"][0]["value"], tx["vsize"],
                             [len(item)//2 for item in tx["vin"][0]["txinwitness"]]))
        assert observed[0] == observed[1], observed

SizingReview(str(test_path)).main()
