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
    BTXD=str(root / "build/bin/btxd"),
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
if mode != "funding-probe":
    runpy.run_path(str(test_path), run_name="__main__")
else:
    from wallet_sendall import SendallTest

    def record_funding(self, amounts):
        info = self.nodes[0].getblockchaininfo()
        self.log.info("Funding preflight: height=%s tip=%s trusted=%s requested=%s",
                      info["blocks"], info["bestblockhash"],
                      self.def_wallet.getbalances()["mine"]["trusted"], amounts)
        for amount in amounts:
            before = self.def_wallet.getbalances()["mine"]["trusted"]
            try:
                txid = self.def_wallet.sendtoaddress(self.wallet.getnewaddress(), amount)
            except Exception:
                self.log.exception("First funding error: trusted=%s requested=%s", before, amount)
                raise
            self.log.info("Funding send: trusted_before=%s amount=%s fee=%s",
                          before, amount, self.def_wallet.gettransaction(txid)["fee"])
        self.generate(self.nodes[0], 1)
        balance = self.wallet.getbalances()["mine"]["trusted"]
        assert balance > 0
        return balance

    SendallTest.add_utxos = record_funding
    SendallTest(str(test_path)).main()
