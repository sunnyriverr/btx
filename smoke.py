"""Start the hash-pinned Windows daemon in a disposable loopback-only regtest."""
import base64
import hashlib
import http.client
import io
import json
import os
from pathlib import Path
import platform
import re
import shutil
import socket
import struct
import subprocess
import sys
import tempfile
import time
import traceback
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parent
RECORDS = ROOT / "records"
BINARY = ROOT / "retained" / "btxd.exe"
EXPECTED_SHA = "393b2a2fc5fac5bda577a2b909f6c7d775a26d3e10ca2b8bcddd9eaee729afa1"
ARTIFACT_SHA = "b17a0cb0e3aea1618b7a2d6f00a2a83540e7997a9e4f8ca1713a6d00c02616d2"
ARTIFACT = 15259326017
CANDIDATE = "1332e7a6545c19af3fa04da329fd55845aa1981b"
BASE = "c2e71aafc48a41593277e335c8bc370e45599f01"
# Pinned CRegTestParams default-genesis assertion at the tested revision.
GENESIS = "521ad0951ed299e9c56aeb7db8188972772067560351b8e55adf71dbed532360"


def digest(data):
    return hashlib.sha256(data).hexdigest()


def save(name, result):
    (RECORDS / name).write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")


class ArtifactRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, message, headers, target):
        redirect = super().redirect_request(req, fp, code, message, headers, target)
        if redirect and urlsplit(target).netloc != "api.github.com":
            redirect.remove_header("Authorization")
        return redirect


def verify_exe(data):
    assert len(data) == 21731840 and digest(data) == EXPECTED_SHA
    offset = struct.unpack_from("<I", data, 60)[0]
    assert data[:2] == b"MZ" and data[offset:offset + 4] == b"PE\0\0"
    assert struct.unpack_from("<H", data, offset + 4)[0] == 0x8664
    assert struct.unpack_from("<H", data, offset + 24)[0] == 0x20b


def fetch():
    url = f"https://api.github.com/repos/sunnyriverr/btx/actions/artifacts/{ARTIFACT}/zip"
    req = Request(url, headers={"Authorization": "Bearer " + os.environ["GH_TOKEN"]})
    with build_opener(ArtifactRedirect()).open(req, timeout=60) as response:
        data = response.read(16 * 1024 * 1024)
    assert digest(data) == ARTIFACT_SHA
    with ZipFile(io.BytesIO(data)) as z:
        result = json.loads(z.read("link-result.json"))
        assert result["base"] == BASE and result["candidate"] == CANDIDATE and result["complete"]
        assert result["binary"]["sha256"] == EXPECTED_SHA and result["linked"]
        binary = z.read("btxd.exe")
    verify_exe(binary)
    BINARY.parent.mkdir()
    BINARY.write_bytes(binary)
    save("restore.json", {"artifact": ARTIFACT, "artifact_sha256": ARTIFACT_SHA,
                          "binary_sha256": digest(binary), "machine": "x64 PE32+",
                          "base": BASE, "candidate": CANDIDATE})


class RpcError(Exception):
    pass


class Node:
    def __init__(self, root, binary):
        self.root = root
        self.cookie = root / "regtest" / ".cookie"
        with socket.socket() as listener:
            listener.bind(("127.0.0.1", 0))
            self.port = listener.getsockname()[1]
        env = dict(os.environ)
        for name in ("PYTHONHOME", "PYTHONPATH", "GH_TOKEN", "GITHUB_TOKEN"):
            env.pop(name, None)
        system = Path(os.environ["SystemRoot"])
        env["PATH"] = os.pathsep.join((str(Path(sys.executable).parent), str(system / "System32"), str(system)))
        self.flags = [
            "-regtest", f"-datadir={root}", "-server=1", f"-rpcport={self.port}", "-rpcbind=127.0.0.1",
            "-rpcallowip=127.0.0.1", "-networkactive=0", "-connect=0", "-listen=0", "-dnsseed=0",
            "-discover=0", "-natpmp=0", "-upnp=0", "-autoupdate=0", "-swapnet=0", "-disablewallet",
            "-nosettings", "-dbcache=16", "-par=1", "-printtoconsole=1",
        ]
        with (RECORDS / "daemon-console.log").open("wb") as out:
            self.process = subprocess.Popen([str(binary), *self.flags], cwd=root, env=env,
                                            stdout=out, stderr=subprocess.STDOUT)

    def rpc(self, name, params=None):
        token = base64.b64encode(self.cookie.read_bytes().strip()).decode("ascii")
        payload = json.dumps({"jsonrpc": "1.0", "id": "smoke", "method": name, "params": params or []})
        connection = http.client.HTTPConnection("127.0.0.1", self.port, timeout=3)
        try:
            connection.request("POST", "/", body=payload, headers={
                "Authorization": "Basic " + token, "Content-Type": "application/json",
            })
            message = json.loads(connection.getresponse().read())
        finally:
            connection.close()
        if message.get("error"):
            raise RpcError(f"{name} returned {message['error']}")
        assert message["id"] == "smoke"
        return message["result"]

    def ready(self):
        until = time.monotonic() + 60
        while time.monotonic() < until and self.process.poll() is None:
            try:
                return self.rpc("getblockchaininfo")
            except (FileNotFoundError, ConnectionError, TimeoutError, RpcError):
                time.sleep(.25)
        raise RuntimeError(f"RPC did not become ready, process exit {self.process.poll()}")


def smoke(result):
    first_read = BINARY.read_bytes()
    verify_exe(first_read)
    assert json.loads((RECORDS / "restore.json").read_text())["binary_sha256"] == EXPECTED_SHA
    result["binary_hash_before"] = digest(first_read)
    started = time.monotonic()
    with tempfile.TemporaryDirectory(prefix="btx-msvc959-") as tmp:
        scratch = Path(tmp)
        node = Node(scratch, BINARY)
        public_flags = [flag for flag in node.flags if not flag.startswith("-datadir=")]
        result["flags"] = public_flags
        clean = False
        try:
            chain = node.ready()
            result["rpc_ready_seconds"] = round(time.monotonic() - started, 3)
            assert chain["chain"] == "regtest" and chain["blocks"] == chain["headers"] == 0
            assert node.rpc("getblockcount") == 0
            assert node.rpc("getblockhash", [0]) == chain["bestblockhash"] == GENESIS
            net = node.rpc("getnetworkinfo")
            assert net["networkactive"] is False and net["connections"] == 0
            assert node.rpc("getpeerinfo") == []
            result["rpc"] = {"chain": chain["chain"], "blocks": chain["blocks"], "headers": chain["headers"],
                             "bestblockhash": chain["bestblockhash"], "networkactive": net["networkactive"],
                             "connections": net["connections"], "peers": []}
            result["stop_reply"] = node.rpc("stop")
            result["exit_code"] = node.process.wait(timeout=30)
            assert result["exit_code"] == 0
            assert not node.cookie.exists(), "RPC cookie persisted after shutdown"
            result["rpc_cookie_removed"] = True
            clean = True
        finally:
            if node.process.poll() is None:
                try:
                    node.rpc("stop")
                    node.process.wait(timeout=8)
                except Exception:
                    node.process.kill()
                    node.process.wait(timeout=10)
            result["process_exited"] = node.process.poll() is not None
            result["clean_stop"] = clean
            debug = scratch / "regtest" / "debug.log"
            if debug.is_file():
                shutil.copyfile(debug, RECORDS / "debug.log")
    output = (RECORDS / "daemon-console.log").read_text(encoding="utf-8", errors="replace")
    assert "Done loading" in output and "Shutdown: done" in output
    assert not re.search(r"\b(?:rpcauth|rpcpassword)=\S+", output, re.I)
    result["startup_and_shutdown_markers"] = True
    result["scratch_removed"] = not scratch.exists()
    result["binary_hash_after"] = digest(BINARY.read_bytes())
    assert result["scratch_removed"] and result["binary_hash_after"] == EXPECTED_SHA
    result["complete"] = True
    print("SHA-256, genesis-only offline RPC, clean shutdown and scratch cleanup passed", flush=True)


if __name__ == "__main__":
    RECORDS.mkdir(exist_ok=True)
    if sys.argv[1:] == ["fetch"]:
        fetch()
    elif sys.argv[1:] == ["smoke"]:
        assert sys.platform == "win32"
        result = {"base": BASE, "candidate": CANDIDATE, "platform": platform.platform(),
                  "python": platform.python_version(), "complete": False, "builds": 0}
        try:
            smoke(result)
        except Exception:
            (RECORDS / "exception.txt").write_text(traceback.format_exc(), encoding="utf-8")
            raise
        finally:
            save("result.json", result)
    else:
        sys.exit("Use fetch or smoke")
