"""Test-only adaptation of Repch1c's #472 real-helper fixture."""
import base64
from contextlib import closing
import hashlib
import hmac
import http.client
import json
import os
from pathlib import Path
import shutil
import signal
import socket
import struct
import subprocess
import tempfile
import time

HERE = Path(os.environ.get("BTX472_OUTPUT", str(Path(__file__).resolve().parent)))
PACKAGE = Path(os.environ.get("BTX472_PACKAGE", "/private/tmp/btx472-package"))
RESERVE = 1280 * 1024**2
AMOUNT = 2_000_000
TARGET = 5_000_000
NO_WALLET = (False, 0, "OBSERVED_NETWORK_STATE")
OWN_WALLET = (True, AMOUNT, "CHAIN_OBSERVATION")
READS = ("getmodelreleaseeconomics", "getfundablemodels")
USERS = {"no_wallet": "-", "owner": "pub", "unrelated": "wa"}
FIELDS = ("wallet_local_state", "confirmed_funded_atoms", "funding_source")
MATMUL_OFF = [
    "-regtestmatmulbindingheight=2147483647",
    "-regtestmatmulproductdigestheight=2147483647",
    "-regtestmatmulv4height=2147483647",
    "-regtestmatmulrequireproductpayload=0",
]


class RPCError(RuntimeError):
    def __init__(self, user, method, error):
        super().__init__(user, method, error)
        self.error = error


def rpcauth(user, password, restriction):
    salt = os.urandom(16).hex()
    digest = hmac.new(salt.encode(), password.encode(), "sha256").hexdigest()
    return f"rpcauth={user}:{salt}${digest}:{restriction}"


def write_model(path, value=0.0):
    header = json.dumps({"__metadata__": {"format": "pt"},
                         "w": {"dtype": "F32", "shape": [1], "data_offsets": [0, 4]}}).encode()
    path.parent.mkdir(exist_ok=True)
    path.write_bytes(struct.pack("<Q", len(header)) + header + struct.pack("<f", value))


def release(card):
    return card.get("release", card)


def main():
    assert shutil.disk_usage(HERE).free >= RESERVE + 24 * 1024**2, "Insufficient runtime disk reserve"
    identity = json.loads((HERE / "mac-baseline-identity.json").read_text())
    for file, digest in identity["members"].items():
        assert hashlib.sha256((PACKAGE / file).read_bytes()).hexdigest() == digest, file
    result = {"source": identity["source"], "artifact": identity["artifact"],
              "platform": subprocess.check_output(["sw_vers", "-productVersion"], text=True).strip(),
              "architecture": os.uname().machine, "phase": "startup", "observations": {}, "controls": {}}
    credentials = {user: os.urandom(16).hex() for user in (*USERS, "operator")}
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        port = listener.getsockname()[1]

    def rpc(method, params=(), user="operator", path="/", timeout=10):
        payload = json.dumps({"jsonrpc": "1.0", "id": 1, "method": method, "params": params})
        auth = base64.b64encode(f"{user}:{credentials[user]}".encode()).decode()
        headers = {"Authorization": "Basic " + auth, "Content-Type": "application/json"}
        with closing(http.client.HTTPConnection("127.0.0.1", port, timeout=timeout)) as conn:
            conn.request("POST", path, payload, headers)
            response = conn.getresponse()
            body = response.read()
            if response.status == 401:
                raise RuntimeError(f"RPC authentication failed for {user}")
        obj = json.loads(body)
        if obj["error"] is not None:
            raise RPCError(user, method, obj["error"])
        assert response.status == 200, response.status
        return obj["result"]

    def views(phase, user, release_id, methods=READS):
        assert shutil.disk_usage(HERE).free >= RESERVE, "Runtime exceeded disk reserve"
        reports = result["observations"].setdefault(phase, {})
        for method in methods:
            if method == READS[0]:
                card = rpc(method, [release_id], user)
            else:
                cards = rpc(method, [{"limit": 10}], user)["results"]
                matches = [item for item in cards if release(item).get("release_id") == release_id]
                assert len(matches) == 1, (method, user, phase, len(matches))
                card = matches[0]
            exposed = release(card)
            projection = tuple(exposed.get(key) for key in FIELDS)
            public = {"release_id": exposed.get("release_id"), "target_atoms": exposed.get("target_atoms")}
            assert public["release_id"] == release_id, (method, user, phase, public)
            assert int(public["target_atoms"]) == TARGET, (method, user, phase, public)
            reports[method] = {"funding": projection, "public": public,
                               "nested": {key: {field: release(card[key]).get(field) for field in FIELDS}
                                          for key in ("entry", "economy") if isinstance(card.get(key), dict)}}
        return reports

    def control(name, observed, expected):
        result["controls"][name] = all(row["funding"] == expected for row in observed.values())
        assert result["controls"][name], (name, observed)

    def denied(user, path):
        try:
            rpc("getwalletinfo", user=user, path=path)
        except RPCError as error:
            assert error.error["code"] == -18, error.error
            return True
        raise AssertionError(f"{user} reached a wallet that should be inaccessible")

    with tempfile.TemporaryDirectory(prefix="btx472-", dir="/private/tmp") as directory:
        runtime = Path(directory)
        cfg = runtime / "btx.conf"
        cfg.write_text(
            "\n".join(["rpcuser=operator", f"rpcpassword={credentials['operator']}",
                       *(rpcauth(user, credentials[user], scope) for user, scope in USERS.items())]) + "\n"
        )
        cfg.chmod(0o600)
        args = [str(PACKAGE / "bin/btxd"), "-regtest", f"-datadir={runtime}", f"-conf={cfg}",
                "-server=1", "-listen=0", "-networkactive=0", "-connect=0", "-dnsseed=0", "-discover=0",
                "-natpmp=0", "-rpcbind=127.0.0.1", "-rpcallowip=127.0.0.1", f"-rpcport={port}",
                "-modelnet=1", "-modelbind=off", "-modelseed=off", "-modelfollowpeers=0",
                "-modellandiscovery=0", "-modelstorage=8MiB", "-printtoconsole=1", *MATMUL_OFF]
        result["arguments_without_ephemeral_paths"] = [arg for arg in args[1:] if not arg.startswith(
            ("-datadir=", "-conf=", "-rpcport="))]
        env = {key: val for key, val in os.environ.items()
               if key not in {"BTX_MODELD", "BTX_MODELHELPER", "LD_LIBRARY_PATH", "LD_PRELOAD", "DYLD_LIBRARY_PATH",
                              "DYLD_INSERT_LIBRARIES"}}
        with (runtime / "console.log").open("wb") as output:
            node = subprocess.Popen(args, cwd=runtime, env=env, stdout=output, stderr=subprocess.STDOUT, start_new_session=True)
            try:
                end = time.monotonic() + 45
                while time.monotonic() < end:
                    assert node.poll() is None, f"Node exited with {node.returncode}"
                    try:
                        info = rpc("getmodelnetworkinfo", timeout=2)
                        if info.get("helper_ready") and info.get("helper_managed_by_btxd"):
                            break
                    except (OSError, RPCError):
                        pass
                    time.sleep(0.25)
                else:
                    raise RuntimeError("Node-owned helper did not become ready")
                result["controls"]["node_owned_helper_ready"] = True
                result["phase"] = "funding setup"
                for wallet in ("wa", "pub"):
                    rpc("createwallet", [wallet])
                pub = "/wallet/pub"
                assert rpc("getwalletinfo", user="owner", path=pub)["walletname"] == "pub"
                result["controls"]["owner_wallet_access"] = True
                result["controls"]["no_wallet_denied_wallet_rpc"] = denied("no_wallet", pub)
                result["controls"]["unrelated_denied_funding_wallet"] = denied("unrelated", pub)
                mine = rpc("getnewaddress", path=pub)
                rpc("generatetoaddress", [110, mine], timeout=90)
                height = rpc("getblockcount")
                releases = {}
                for index in range(2):
                    model_path = runtime / "model" / ("toy" + str(index) + ".safetensors")
                    write_model(model_path, float(index))
                    hosted = rpc("hostmodel", [str(model_path)], timeout=20)
                    secret = hashlib.sha256(("r6-obs-" + str(index)).encode()).digest()
                    card = rpc("createmodelrelease", [{"uri": hosted["uri"], "secret32_hex": secret.hex(),
                               "refund_height": height + 20, "target_atoms": TARGET, "display_name": "R6 obs"}])
                    releases[card["release_id"]] = (card, secret)
                public_order = [release(item)["release_id"] for item in
                                rpc("getfundablemodels", [{"limit": 10}], user="no_wallet")["results"]]
                assert len(public_order) == 2 and set(public_order) == set(releases), public_order
                release_id = public_order[-1]
                card, secret = releases[release_id]
                result["public_initial_order"] = public_order
                keys = [rpc("exportpqkey", [rpc("getnewaddress", path=pub)], path=pub)["pubkey"] for _ in range(2)]
                frozen = rpc("preparefundmodelrelease", [release_id, {
                    "key_hash": card.get("key_hash") or hashlib.sha256(secret).hexdigest(),
                    "claimant": keys[0], "refund_pubkey": keys[1], "refund_height": height + 20,
                    "amount_atoms": str(AMOUNT), "fee_cap_atoms": "1000000",
                    "auto_pay": False, "automatic_spend_atoms": "0"}], path=pub)
                assert frozen["plan_stage"] == "WALLET_PREPARED"
                signed = rpc("signmodelfunding", [frozen["unsigned_hex"], frozen], path=pub)
                rpc("submitmodelfunding", [signed["hex"], frozen], path=pub)
                rpc("generatetoaddress", [2, mine], timeout=30)
                result["phase"] = "wallet view controls"
                control("public_before_operator", views("public_before_owner", "no_wallet", release_id), NO_WALLET)
                control("own_wallet_before_operator", views("owner_before_operator", "owner", release_id), OWN_WALLET)
                control("own_wallet_read_does_not_prime_cache", views("public_after_owner", "no_wallet", release_id), NO_WALLET)
                control("operator_primes_cache", views("operator", "operator", release_id, READS[:1]), OWN_WALLET)
                after = views("public_after_operator", "no_wallet", release_id)
                unrelated = views("unrelated_after_operator", "unrelated", release_id)
                result["controls"]["unrelated_top_level_no_wallet_state"] = all(
                    not row["funding"][0] for row in unrelated.values())
                assert result["controls"]["unrelated_top_level_no_wallet_state"], unrelated
                control("own_wallet_after_operator", views("owner_after_operator", "owner", release_id), OWN_WALLET)
                control("operator_list", views("operator_list", "operator", release_id, READS[1:]), OWN_WALLET)
                result["controls"]["public_metadata_stable"] = all(
                    row["public"] == result["observations"]["public_before_owner"][method]["public"]
                    for method, row in after.items())
                assert result["controls"]["public_metadata_stable"]
                public_after = rpc("getfundablemodels", [{"limit": 10}], user="no_wallet")
                public_after_order = [release(item)["release_id"] for item in public_after["results"]]
                public_top = rpc("getfundablemodels", [{"limit": 1}], user="no_wallet")
                public_top_ids = [release(item)["release_id"] for item in public_top["results"]]
                operator_top = rpc("getfundablemodels", [{"limit": 1}])
                operator_top_ids = [release(item)["release_id"] for item in operator_top["results"]]
                result["controls"]["operator_ranking_uses_funding"] = operator_top_ids == [release_id]
                assert result["controls"]["operator_ranking_uses_funding"], operator_top
                result["public_after_order"] = public_after_order
                result["public_after_top"] = public_top_ids
                result["operator_top"] = operator_top_ids
                result["phase"] = "regression assertion"
                result["regression"] = {method: row["funding"] == NO_WALLET for method, row in after.items()}
                result["regression"]["public_list_order"] = public_after_order == public_order
                result["regression"]["public_limit_one"] = public_top_ids == public_order[:1]
                result["matches_reported_failure"] = all(row["funding"] == OWN_WALLET for row in after.values())
                result["regression_passed"] = all(result["regression"].values())
            except (Exception, KeyboardInterrupt) as error:
                result["error"] = str(error)
                raise
            finally:
                if node.poll() is None:
                    try:
                        rpc("stop", timeout=5)
                    except (OSError, RPCError, ValueError):
                        pass
                    try:
                        node.wait(12)
                    except subprocess.TimeoutExpired:
                        os.killpg(node.pid, signal.SIGTERM)
                        try:
                            node.wait(5)
                        except subprocess.TimeoutExpired:
                            os.killpg(node.pid, signal.SIGKILL)
                            node.wait(5)
                result["node_exit"] = node.returncode
                if "error" in result:
                    with (runtime / "console.log").open("rb") as console:
                        console.seek(max(0, (runtime / "console.log").stat().st_size - 16000))
                        (HERE / "mac-runtime-diagnostic.log").write_bytes(console.read())
                (HERE / "mac-regression-result.json").write_text(json.dumps(result, indent=2) + "\n")
    result["disposable_runtime_removed"] = not runtime.exists()
    (HERE / "mac-regression-result.json").write_text(json.dumps(result, indent=2) + "\n")
    assert result["node_exit"] == 0 and result["disposable_runtime_removed"]
    return 0 if result["regression_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
