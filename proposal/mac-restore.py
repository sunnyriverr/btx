"""Run the pinned default test runner against the saved native ARM build."""
import ast
from collections import Counter
import configparser
import csv
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import shutil
import signal
import subprocess
import sys
import tarfile
import tempfile
import time
import urllib.request
import zipfile

ROOT = Path(os.environ["GITHUB_WORKSPACE"])
PRODUCT = ROOT / "product"
BUILD = ROOT / "mac-config-build"
OUT = ROOT / "records"
OUT.mkdir(exist_ok=True)
PIN = "2c4da891f0089ebc0fb082e65d03a4efda4488a3"
ARTIFACT = 14703680085
ZIP_SHA = "bd1d38d3248fda0307f4a3010e4fb62726b1ae60317fe9b327958415c26f1a1d"
TAR_SHA = "2e73aa10042715b9f9399527e5a9c852146492075efb7de108dbd9a17fc1602c"
PYTHON = ROOT / "test-env/bin/python"
CONFIG = BUILD / "test/config.ini"
RUNNER = PRODUCT / "test/functional/test_runner.py"
CAP = 180 * 60
GIB = 1024**3
BASELINE = json.loads(Path(__file__).with_name("producer-build-result.json").read_text())


def sha(path):
    with path.open("rb") as f:
        return hashlib.file_digest(f, "sha256").hexdigest()


def record(name, value):
    path = OUT / name
    candidate = path.with_suffix(".tmp")
    candidate.write_text(json.dumps(value, indent=2) + "\n")
    candidate.replace(path)


def command(args, label, env=None, cwd=ROOT, timeout=180):
    print(label, flush=True)
    with (OUT / f"{label}.log").open("wb") as log:
        subprocess.run(args, cwd=cwd, env=env, stdout=log, stderr=subprocess.STDOUT,
                       timeout=timeout, check=True)
    return (OUT / f"{label}.log").read_text(errors="replace").strip()


def extract():
    request = urllib.request.Request(
        f"https://api.github.com/repos/sunnyriverr/btx/actions/artifacts/{ARTIFACT}/zip",
        headers={"User-Agent": "BTX Mac functional checkpoint"})
    request.add_unredirected_header("Authorization", "Bearer " + os.environ["GH_TOKEN"])
    with tempfile.TemporaryDirectory(prefix="btx-checkpoint-", dir=ROOT) as temp:
        outer = Path(temp) / "checkpoint.zip"
        try:
            with urllib.request.urlopen(request, timeout=85) as response, outer.open("wb") as f:
                shutil.copyfileobj(response, f, 1024**2)
        except Exception:
            raise RuntimeError("Checkpoint download failed") from None
        assert outer.stat().st_size == 284018992 and sha(outer) == ZIP_SHA
        archive = Path(temp) / "checkpoint.tar.gz"
        with zipfile.ZipFile(outer) as z:
            inv = json.loads(z.read("inventory.json"))
            receipt = json.loads(z.read("receipt.json"))
            with z.open("checkpoint.tar.gz") as src, archive.open("wb") as dest:
                shutil.copyfileobj(src, dest, 1024**2)
        assert archive.stat().st_size == receipt["bytes"] == 278893505
        assert sha(archive) == receipt["sha256"] == TAR_SHA
        assert not BUILD.exists()
        expected = {n for n in inv if n.startswith(BUILD.name + "/")}
        seen = set()
        with tarfile.open(archive) as tar:
            for item in tar:
                if item.name not in expected:
                    continue
                rel = Path(item.name)
                assert not rel.is_absolute() and ".." not in rel.parts and item.name not in seen
                dest = ROOT / rel
                assert dest.parent.resolve().is_relative_to(ROOT)
                meta = inv[item.name]
                if item.isdir():
                    assert meta["type"] == "dir"
                    dest.mkdir(parents=True, exist_ok=True)
                else:
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    if item.issym():
                        assert meta["type"] == "symlink" and item.linkname == meta["target"]
                        target = (dest.parent / item.linkname).resolve()
                        assert target.is_relative_to(ROOT) and ".git" not in target.relative_to(ROOT).parts
                        dest.symlink_to(item.linkname)
                    else:
                        assert item.isfile() and meta["type"] == "file"
                        with tar.extractfile(item) as src, dest.open("xb") as out:
                            shutil.copyfileobj(src, out, 1024**2)
                        assert dest.stat().st_size == meta["bytes"] and sha(dest) == meta["sha256"], item.name
                        dest.chmod(meta["mode"])
                        os.utime(dest, ns=(meta["mtime_ns"], meta["mtime_ns"]))
                seen.add(item.name)
        assert seen == expected
    return len(seen)


def verify_binaries():
    assert BASELINE["source"] == PIN and BASELINE["status"] == "PASS_17_TARGETS"
    assert len(BASELINE["binaries"]) == 17
    actual = {}
    for target, expected in BASELINE["binaries"].items():
        binary = BUILD / "bin" / target
        actual[target] = {"bytes": binary.stat().st_size, "sha256": sha(binary)}
        assert binary.is_file() and not binary.is_symlink() and os.access(binary, os.X_OK)
        assert actual[target] == expected, target
    return actual


def runtime_env():
    env = os.environ.copy()
    for key in ("BTX_RUN_UPSTREAM_BASE_SUITE", "BTXD", "BTXCLI", "BITCOIND", "BITCOINCLI",
                "BTXWALLET", "BTXUTIL", "BTXTX", "BITCOINWALLET", "BITCOINUTIL", "BITCOINTX",
                "PREVIOUS_RELEASES_DIR", "XDG_RUNTIME_DIR", "CI_FAILFAST_TEST_LEAVE_DANGLING"):
        env.pop(key, None)
    ssl = "/opt/homebrew/opt/openssl@3/bin"
    env["BTX_OPENSSL"] = f"{ssl}/openssl"
    env["PATH"] = f"{ROOT / 'no-build'}:{PYTHON.parent}:{ssl}:" + env["PATH"]
    env["PYTHONUNBUFFERED"] = "1"
    return env


def inventory():
    parsed = ast.parse(RUNNER.read_text())
    for statement in parsed.body:
        if isinstance(statement, ast.Assign) and any(
            isinstance(x, ast.Name) and x.id == "BTX_BASE_SCRIPTS" for x in statement.targets
        ):
            cases = ast.literal_eval(statement.value)
            assert len(cases) == len(set(cases)) == 232
            return cases
    raise AssertionError("Default case list not found")


def restore():
    assert platform.system() == "Darwin" and platform.machine() == "arm64"
    assert shutil.disk_usage(ROOT).free >= 15 * GIB
    assert command(["git", "-C", PRODUCT, "rev-parse", "HEAD"], "source") == PIN
    assert not command(["git", "-C", PRODUCT, "status", "--porcelain", "--untracked-files=no"], "source-tracked-before")
    assert "Xcode 16.4" in command(["xcodebuild", "-version"], "xcode")
    assert command(["xcrun", "--sdk", "macosx", "--show-sdk-version"], "sdk") == "15.5"
    entries = extract()
    print(f"Verified and restored {entries} build entries", flush=True)
    verified = verify_binaries()
    assert all(command(["lipo", "-archs", BUILD/"bin"/n], "arch-"+n) == "arm64" for n in verified)
    cfg = configparser.ConfigParser()
    cfg.read(CONFIG)
    expected_env = {"SRCDIR": str(PRODUCT), "BUILDDIR": str(BUILD), "EXEEXT": ""}
    assert all(cfg["environment"][k] == v for k, v in expected_env.items())
    assert all(cfg["components"].getboolean(k) for k in
               ("ENABLE_BITCOIND", "ENABLE_WALLET", "ENABLE_MODELNET", "ENABLE_ZMQ", "USE_SQLITE"))
    assert (BUILD/"test/functional/test_runner.py").resolve() == RUNNER or (
        sha(BUILD/"test/functional/test_runner.py") == sha(RUNNER))
    assert sha(BUILD/"test/functional/create_cache.py") == sha(PRODUCT/"test/functional/create_cache.py")
    shutil.copy2(CONFIG, OUT/"test-config.ini")
    record("default-inventory.json", inventory())
    command(["brew", "install", "--force-bottle", "boost@1.85", "libevent", "zeromq",
             "libomp", "qt", "qrencode", "librsvg", "libicns", "python@3.12", "openssl@3"],
            "brew-dependencies", timeout=600)
    command(["brew", "list", "--versions"], "dependency-versions")
    python = "/opt/homebrew/opt/python@3.12/bin/python3.12"
    linked = command(["otool", "-L", BUILD/"bin/btxd"], "btxd-native-dependencies")
    assert re.search(r"(?:Python\.framework/Versions/3\.12/|libpython3\.12\.dylib)", linked), linked
    cache = (BUILD/"CMakeCache.txt").read_text()
    assert "_Python3_LIBRARY_RELEASE:INTERNAL=/opt/homebrew/opt/python@3.12/" in cache
    imports = "import cryptography, sqlite3; from cryptography.hazmat.primitives.ciphers.aead import AESGCM; print(cryptography.__version__, cryptography.__file__)"
    try:
        command([python, "-I", "-c", imports], "framework-crypto-before")
    except subprocess.CalledProcessError:
        assert "No module named 'cryptography'" in (OUT/"framework-crypto-before.log").read_text()
    command([python, "-m", "pip", "install", "--only-binary=:all:",
             "--break-system-packages", "cryptography==46.0.4"], "framework-crypto-install")
    assert command([python, "-I", "-c", imports], "framework-crypto-after").startswith("46.0.4 ")
    command([python, "-m", "venv", PYTHON.parent.parent], "venv")
    command([PYTHON, "-m", "pip", "install", "--only-binary=:all:",
             "cryptography==46.0.4", "pyzmq==27.1.0"], "pip-runtime")
    env = runtime_env()
    command([PYTHON, "-c", "import zmq, cryptography"], "python-imports", env)
    command([Path(env["BTX_OPENSSL"]), "version"], "openssl-runtime", env)
    for binary in ("btxd", "btx-cli"):
        command([BUILD/"bin"/binary, "--version"], binary+"-version", env)
    record("restore-result.json", {"status": "VERIFIED", "source": PIN, "artifact": ARTIFACT,
            "restore_entries": entries, "binaries": verified, "image": os.environ.get("ImageVersion"),
            "arch": platform.machine(), "macos": platform.mac_ver()[0], "zip_sha256": ZIP_SHA,
            "archive_sha256": TAR_SHA, "runner_sha256": sha(RUNNER), "config_sha256": sha(CONFIG)})


if __name__ == "__main__":
    restore()
