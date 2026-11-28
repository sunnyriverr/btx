"""Exercise read, refuse, and retry of a disposable Windows LevelDB chainstate."""

from contextlib import contextmanager
import ctypes
from ctypes import wintypes
import hashlib
import io
import json
import os
from pathlib import Path
import platform
import re
import socket
import subprocess
import sys
import tempfile
import time
import traceback
from urllib.parse import urlsplit
from urllib.request import build_opener, HTTPRedirectHandler, Request
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parent
PINS = json.loads((ROOT / "pins.json").read_text(encoding="utf-8"))
RECORDS = ROOT / "records"
ARCHIVE = ROOT / "retained.zip"
FETCH_RECORD = RECORDS / "restore.json"
BURN_ADDRESS = "btxrt1qqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqdmjdx9"
READ = 0x80000000
SHARE_READ = 1
OPEN_EXISTING = 3
NORMAL = 0x80
IGNORE_MERGE_ERRORS = 2


def digest(data):
    return hashlib.sha256(data).hexdigest()


def save_json(path, result):
    path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")


class ArtifactRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, target):
        redirected = super().redirect_request(req, fp, code, msg, headers, target)
        if redirected and urlsplit(target).netloc != "api.github.com":
            redirected.remove_header("Authorization")
        return redirected


def fetch():
    url = f"https://api.github.com/repos/sunnyriverr/btx/actions/artifacts/{PINS['artifact_id']}/zip"
    request = Request(url, headers={"Authorization": "Bearer " + os.environ["GH_TOKEN"]})
    with build_opener(ArtifactRedirect()).open(request, timeout=45) as response:
        data = response.read(64 * 1024 * 1024)
    assert digest(data) == PINS["artifact_sha256"]
    with ZipFile(io.BytesIO(data)) as artifact:
        archives = [name for name in artifact.namelist() if name.endswith(".zip")]
        assert len(archives) == 1, archives
        raw_package = artifact.read(archives[0])
    assert digest(raw_package) == PINS["archive_sha256"]
    ARCHIVE.write_bytes(raw_package)
    save_json(FETCH_RECORD, {
        "artifact_id": PINS["artifact_id"], "artifact_sha256": digest(data),
        "archive_sha256": digest(raw_package), "input_member": archives[0],
    })


def unpack(scratch):
    assert FETCH_RECORD.exists() and digest(ARCHIVE.read_bytes()) == PINS["archive_sha256"]
    with ZipFile(ARCHIVE) as package:
        package.extractall(scratch)
    bins = [path.parent for path in scratch.rglob("btxd.exe")]
    assert len(bins) == 1, bins
    for exe, expected in PINS["executables"].items():
        assert digest((bins[0] / exe).read_bytes()) == expected, exe
    return bins[0]


def native_files():
    api = ctypes.WinDLL("kernel32", use_last_error=True)
    api.CreateFileW.argtypes = [
        wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD, wintypes.LPVOID,
        wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE,
    ]
    api.CreateFileW.restype = wintypes.HANDLE
    api.CloseHandle.argtypes = [wintypes.HANDLE]
    api.CloseHandle.restype = wintypes.BOOL
    api.ReplaceFileW.argtypes = [
        wintypes.LPCWSTR, wintypes.LPCWSTR, wintypes.LPCWSTR, wintypes.DWORD,
        wintypes.LPVOID, wintypes.LPVOID,
    ]
    api.ReplaceFileW.restype = wintypes.BOOL
    return api


@contextmanager
def reader(api, path):
    handle = api.CreateFileW(str(path), READ, SHARE_READ, None, OPEN_EXISTING, NORMAL, None)
    if handle == ctypes.c_void_p(-1).value:
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        yield
    finally:
        if not api.CloseHandle(handle):
            raise ctypes.WinError(ctypes.get_last_error())


def measure_native_error(api, scratch):
    old = scratch / "old-pointer.txt"
    new = scratch / "new-pointer.txt"
    old.write_bytes(b"previous")
    new.write_bytes(b"replacement")
    with reader(api, old):
        ok = api.ReplaceFileW(str(old), str(new), None, IGNORE_MERGE_ERRORS, None, None)
        code = ctypes.get_last_error()
        assert not ok and code, code
    assert old.read_bytes() == b"previous" and new.read_bytes() == b"replacement"
    assert api.ReplaceFileW(str(old), str(new), None, IGNORE_MERGE_ERRORS, None, None)
    assert old.read_bytes() == b"replacement" and not new.exists()
    return {"code": code, "message": ctypes.FormatError(code).strip()}


def pointer_state(current):
    raw = current.read_bytes()
    name = raw.decode("ascii").strip()
    assert re.fullmatch(r"MANIFEST-[0-9]+", name), name
    manifest = current.parent / name
    return {"current_sha256": digest(raw), "manifest": name, "manifest_sha256": digest(manifest.read_bytes())}


class Node:
    def __init__(self, bins, datadir):
        self.bins = bins
        self.datadir = datadir
        self.env = dict(os.environ)
        self.env["PATH"] = str(Path(os.environ["SystemRoot"]) / "System32")
        for key in ("PYTHONHOME", "PYTHONPATH"):
            self.env.pop(key, None)
        self.process = None

    def spawn(self, label):
        assert self.process is None or self.process.poll() is not None
        with socket.socket() as port:
            port.bind(("127.0.0.1", 0))
            self.port = port.getsockname()[1]
        flags = [
            f"-datadir={self.datadir}", "-regtest", "-server=1", "-disablewallet", "-modelnet=0",
            "-swapnet=0", "-autoupdate=0", "-connect=0", "-listen=0", "-dnsseed=0", "-discover=0",
            "-upnp=0", "-natpmp=0", f"-rpcport={self.port}", "-rpcbind=127.0.0.1",
            "-rpcallowip=127.0.0.1", "-dbcache=16", "-par=1", "-nosettings", "-printtoconsole=1",
        ]
        self.log = RECORDS / f"{label}.log"
        with self.log.open("wb") as handle:
            self.process = subprocess.Popen(
                [str(self.bins / "btxd.exe"), *flags], stdout=handle, stderr=subprocess.STDOUT,
                cwd=self.bins, env=self.env,
            )

    def rpc(self, method, *args, timeout=10):
        p = subprocess.run(
            [str(self.bins / "btx-cli.exe"), "-regtest", f"-datadir={self.datadir}",
             f"-rpcport={self.port}", f"-rpcclienttimeout={timeout}", method, *map(str, args)],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            cwd=self.bins, env=self.env, timeout=timeout + 3,
        )
        if p.returncode:
            raise RuntimeError(f"{method} failed ({p.returncode}) {p.stderr.strip()}")
        try:
            return json.loads(p.stdout)
        except json.JSONDecodeError:
            return p.stdout.strip()

    def ready(self):
        deadline = time.monotonic() + 40
        while self.process.poll() is None and time.monotonic() < deadline:
            try:
                info = self.rpc("getblockchaininfo", timeout=2)
                assert info["chain"] == "regtest", info
                return info
            except (RuntimeError, subprocess.TimeoutExpired):
                time.sleep(.25)
        raise RuntimeError(f"RPC not ready, node exit {self.process.poll()}, see {self.log.name}")

    def stop(self):
        self.rpc("stop")
        assert self.process.wait(timeout=25) == 0

    def cleanup(self):
        if self.process and self.process.poll() is None:
            try:
                self.stop()
            except Exception:
                self.process.kill()
                self.process.wait(timeout=10)
                return "forced"
        return "all exited"


def coin_output(node, block_hash):
    transactions = node.rpc("getblock", block_hash, 2)["tx"]
    assert len(transactions) == 1
    coin = transactions[0]
    for output in coin["vout"]:
        record = node.rpc("gettxout", coin["txid"], output["n"], "false")
        if record:
            return {"txid": coin["txid"], "n": output["n"],
                    "value": record["value"], "script": record["scriptPubKey"]["hex"],
                    "coinbase": record["coinbase"]}
    raise AssertionError("No chainstate output for the generated block")


def recover(result, scratch):
    bins = unpack(scratch)
    result["binary_hashes_verified"] = PINS["executables"]
    datadir = scratch / "db"
    datadir.mkdir()
    current = datadir / "regtest" / "chainstate" / "CURRENT"
    node = Node(bins, datadir)
    api = native_files()
    try:
        node.spawn("seed")
        assert node.ready()["blocks"] == 0
        blocks = node.rpc("generatetoaddress", 2, BURN_ADDRESS, timeout=90)
        assert len(blocks) == 2 and node.rpc("getbestblockhash") == blocks[-1]
        seeded = [coin_output(node, block) for block in blocks]
        result["seeded_chainstate_records"] = seeded
        result["seeded_block_hashes"] = blocks
        node.stop()

        node.spawn("healthy-reopen")
        assert node.ready()["bestblockhash"] == blocks[-1]
        assert [coin_output(node, block) for block in blocks] == seeded
        node.stop()
        result["healthy_reopen"] = True

        result["native_pair_control"] = measure_native_error(api, scratch)
        before = pointer_state(current)
        result["before"] = before
        with reader(api, current):
            node.spawn("replacement-refused")
            result["startup_exit"] = node.process.wait(timeout=45)
        log = node.log.read_text(encoding="utf-8", errors="replace")
        fault_lines = [
            line for line in log.splitlines()
            if "Fatal LevelDB error" in line and re.search(r"chainstate[/\\]\d+\.dbtmp", line)
        ]
        result["first_leveldb_error"] = next(iter(fault_lines), None)
        assert result["startup_exit"] == 1 and fault_lines, f"Target replacement was not observed: {result}"
        assert "Error opening coins database" in log
        result["same_error_as_pair_control"] = result["native_pair_control"]["message"] in fault_lines[0]
        result["immediately_after"] = pointer_state(current)
        assert result["immediately_after"] == before

        node.spawn("same-database-retry")
        assert node.ready()["bestblockhash"] == blocks[-1]
        assert [coin_output(node, block) for block in blocks] == seeded
        result["same_database_records_recovered"] = True
        new_blocks = node.rpc("generatetoaddress", 1, BURN_ADDRESS, timeout=90)
        assert len(new_blocks) == 1 and node.rpc("getblockcount") == 3
        result["new_block"] = new_blocks[0]
        result["new_chainstate_record"] = coin_output(node, new_blocks[0])
        node.stop()

        node.spawn("new-write-reopen")
        assert node.ready()["bestblockhash"] == result["new_block"]
        assert [coin_output(node, block) for block in blocks] == seeded
        assert coin_output(node, result["new_block"]) == result["new_chainstate_record"]
        node.stop()
        result["new_write_persisted"] = True
    finally:
        result["cleanup"] = node.cleanup()


if __name__ == "__main__":
    RECORDS.mkdir(exist_ok=True)
    if sys.argv[1:] == ["fetch"]:
        fetch()
    elif sys.argv[1:] == ["recover"]:
        assert sys.platform == "win32"
        report = {"pins": PINS, "platform": platform.platform(), "python": platform.python_version(),
                  "complete": False}
        try:
            with tempfile.TemporaryDirectory(prefix="btx-leveldb-recovery-") as temp:
                recover(report, Path(temp))
            report["complete"] = True
        except Exception:
            (RECORDS / "exception.txt").write_text(traceback.format_exc(), encoding="utf-8")
            raise
        finally:
            save_json(RECORDS / "result.json", report)
    else:
        sys.exit("Use fetch or recover")
