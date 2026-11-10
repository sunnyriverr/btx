"""Run both BCP/1 commands against an unchanged accepted Linux node in private regtest."""
import base64
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import socket
import subprocess
import tarfile
import tempfile
import time
import urllib.error
import urllib.request

SOURCE = "dac9aee53520bd49ed320ec7a49b9072fc7d88d9"
ARCHIVE = "0caaa7d2d762d51bde262bff0bfb3965f58cc09bb1726b034783608930d3d633"
NODE_WRAPPER = "bdd9273c2dcbf804a717e16bdcc4c08288f16c31cde59726f01924178487cb83"
METHODS = ("createexchangebatch", "createconsolidationtx")


def sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def main():
    workspace = Path(os.environ["GITHUB_WORKSPACE"])
    out = workspace / "bcp1-records"
    out.mkdir(exist_ok=True)
    runtime = Path(tempfile.mkdtemp(prefix="bcp1-lock-"))
    state = {"source": SOURCE, "archive_sha256": ARCHIVE, "commands": {}, "cleanup_signals": []}
    node = None
    output = None
    cookie_path = runtime / "node/regtest/.cookie"
    password = "disposable-regtest-fixture"
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        port = listener.getsockname()[1]

    def save():
        (out / "result.json").write_text(json.dumps(state, indent=2) + "\n")

    def wire(method, params=None, wallet=None, timeout=25):
        path = "/wallet/" + wallet if wallet else "/"
        auth = base64.b64encode(cookie_path.read_bytes().strip()).decode()
        body = json.dumps({"jsonrpc": "2.0", "id": "bcp1", "method": method, "params": params or []}).encode()
        req = urllib.request.Request(f"http://127.0.0.1:{port}{path}", data=body,
                                     headers={"Authorization": "Basic " + auth, "Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=timeout) as response:
                return json.load(response)
        except urllib.error.HTTPError as error:
            return json.load(error)

    def rpc(method, params=None, wallet=None, timeout=25):
        reply = wire(method, params, wallet, timeout)
        assert not reply.get("error"), (method, reply.get("error"))
        return reply["result"]

    def package_reply(method, params, wallet, expected):
        reply = wire(method, params, wallet)
        if reply.get("error"):
            return {"error": reply["error"]}
        package = reply["result"]
        decoded = rpc("decodepsbt", [package["psbt"]])
        inputs = [(item["txid"], item["vout"]) for item in decoded["tx"]["vin"]]
        assert inputs == [expected], (method, inputs, expected)
        assert package["broadcast"] is False and package["complete"] is False
        assert all(not any(key.startswith("final_") for key in item) for item in decoded["inputs"])
        return {"error": None, "broadcast": False, "complete": False, "inputs": inputs,
                "outputs": len(decoded["tx"]["vout"]), "fee_atoms": package["fee_atoms"]}

    try:
        assert shutil.disk_usage(runtime).free > 3 * 1024**3
        archive = workspace / "candidate-input/btx-linux-gui-candidate.tar.gz"
        assert sha(archive) == ARCHIVE
        provenance = json.loads((workspace / "candidate-input/provenance.json").read_text())
        assert SOURCE in json.dumps(provenance["source"])
        extracted = runtime / "archive"
        extracted.mkdir()
        with tarfile.open(archive) as tar:
            assert sum(member.size for member in tar.getmembers()) < 2 * 1024**3
            tar.extractall(extracted, filter="data")
        wrappers = list(extracted.rglob("bin/btxd"))
        assert len(wrappers) == 1 and sha(wrappers[0]) == NODE_WRAPPER
        wrapper = wrappers[0]
        real = wrapper.parent.parent / "libexec/btxd.real"
        real_hash = sha(real)
        assert real_hash == provenance["candidate_files"]["libexec/btxd.real"]["sha256"]
        state["node_sha256"] = {"wrapper": NODE_WRAPPER, "real": real_hash}
        home = runtime / "home"
        home.mkdir(mode=0o700)
        datadir = runtime / "node"
        datadir.mkdir(mode=0o700)
        args = [
            "-regtest", f"-datadir={datadir}", "-server=1", "-rpcbind=127.0.0.1",
            "-rpcallowip=127.0.0.1", f"-rpcport={port}", "-listen=0", "-connect=0",
            "-dnsseed=0", "-discover=0", "-natpmp=0", "-modelnet=0", "-autoshieldcoinbase=0",
            "-keypool=4", "-dbcache=32", "-fallbackfee=0.0002",
            "-regtestmatmulbindingheight=2147483647", "-regtestmatmulproductdigestheight=2147483647",
            "-regtestmatmulv4height=2147483647", "-regtestmatmulrequireproductpayload=0",
            "-matmulvalidation=economic",
        ]
        state["regtest_flags"] = [arg for arg in args if not arg.startswith(("-datadir=", "-rpcport="))]
        output = (out / "node.log").open("wb")
        node = subprocess.Popen([str(wrapper), *args], env=dict(os.environ, HOME=str(home)),
                                stdout=output, stderr=subprocess.STDOUT, start_new_session=True)
        deadline = time.monotonic() + 45
        while True:
            try:
                chain = rpc("getblockchaininfo", timeout=3)
                break
            except Exception:
                if node.poll() is not None or time.monotonic() > deadline:
                    raise
                time.sleep(.3)
        assert chain["chain"] == "regtest" and chain["blocks"] == 0 and rpc("getconnectioncount") == 0
        rpc("createwallet", {"wallet_name": "miner", "descriptors": True})
        rpc("createwallet", {"wallet_name": "payer", "descriptors": True, "passphrase": password})
        rpc("createwallet", {"wallet_name": "watch", "descriptors": True, "disable_private_keys": True, "blank": True})
        miner = rpc("getnewaddress", ["", "p2mr"], "miner")
        payer = rpc("getnewaddress", ["", "p2mr"], "payer")
        recipient = rpc("getnewaddress", ["", "p2mr"], "miner")
        pubkey = rpc("getaddressinfo", [miner], "miner")["pubkey"]
        assert len(bytes.fromhex(pubkey)) == 1312
        [watch] = rpc("deriveaddresses", [f"mr({pubkey})", None, {"require_checksum": False}])
        rpc("importdepositpool", [[{"index": 0, "label": "deposit/0", "pubkey": pubkey}]], "watch")
        assert rpc("getwalletinfo", [], "watch")["private_keys_enabled"] is False
        assert rpc("getaddressinfo", [watch], "watch")["solvable"] is True
        assert len(rpc("generatetoaddress", [110, miner], timeout=150)) == 110
        funding = rpc("sendmany", ["", {payer: 5, watch: 5}], "miner")
        assert len(rpc("generatetoaddress", [1, miner], timeout=60)) == 1
        assert rpc("getblockcount") == 111 and rpc("getrawmempool") == []
        state["funding"] = {"txid": funding, "blocks": 111, "peers": 0}
        [coin] = rpc("listunspent", [1], "payer")
        [observed] = rpc("listunspent", [1], "watch")
        assert coin["amount"] == observed["amount"] == 5 and coin["txid"] == observed["txid"] == funding
        assert observed["solvable"] is True
        assert rpc("getwalletinfo", [], "payer")["unlocked_until"] == 0
        state["wallet_controls"] = {
            "locked": {k: coin[k] for k in ("txid", "vout", "amount", "solvable", "spendable")},
            "watch_only": {k: observed[k] for k in ("txid", "vout", "amount", "solvable", "spendable")},
        }
        def requests(change):
            return ([[{"address": recipient, "amount": 1}], {"change_address": change}],
                    [{"change_address": change, "max_inputs": 10, "target_utxo_count": 1}])
        expected = (coin["txid"], coin["vout"])
        plan = rpc("planconsolidation", [{"max_inputs": 10}], "payer")
        assert [(x["txid"], x["vout"]) for x in plan["inputs"]] == [expected]
        state["locked_plan_visible"] = True
        for method, params in zip(METHODS, requests(payer)):
            state["commands"][method] = {"locked": package_reply(method, params, "payer", expected)}
        save()
        rpc("walletpassphrase", [password, 180], "payer")
        assert rpc("getwalletinfo", [], "payer")["unlocked_until"] > 0
        for method, params in zip(METHODS, requests(payer)):
            state["commands"][method]["unlocked"] = package_reply(method, params, "payer", expected)
        rpc("walletlock", [], "payer")
        assert rpc("getwalletinfo", [], "payer")["unlocked_until"] == 0
        state["relocked"] = True
        for method, params in zip(METHODS, requests(watch)):
            state["commands"][method]["watch_only"] = package_reply(method, params, "watch", (observed["txid"], observed["vout"]))
        assert rpc("getrawmempool") == [] and rpc("getblockcount") == 111
        assert all(rpc("listunspent", [1], w)[0]["amount"] == 5 for w in ("payer", "watch"))
        state["no_broadcast_or_input_consumption"] = True
        state["comparison_complete"] = all(
            all(row[mode]["error"] is None for mode in ("unlocked", "watch_only"))
            for row in state["commands"].values()
        )
    except Exception as error:
        state["error"] = repr(error)
    finally:
        if node:
            if node.poll() is None:
                try:
                    rpc("stop", timeout=8)
                    node.wait(timeout=20)
                except Exception:
                    state["cleanup_signals"].append("SIGKILL")
                    os.killpg(node.pid, signal.SIGKILL)
                    node.wait(timeout=10)
            state["clean_node_exit"] = node.returncode == 0 and not state["cleanup_signals"]
        if output:
            output.close()
        if node is None or node.poll() is not None:
            shutil.rmtree(runtime)
        state["runtime_removed"] = not runtime.exists()
        save()
    return 0 if state.get("comparison_complete") and state.get("clean_node_exit") and state["runtime_removed"] and "error" not in state else 1


if __name__ == "__main__":
    raise SystemExit(main())
