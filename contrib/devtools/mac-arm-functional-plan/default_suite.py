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
PIN = "26d5d2ddb0a27827b5b603a004177582747c294c"
ARTIFACT = 14584973761
ZIP_SHA = "580566e1888f7eeed13e0490c2f56fdd77b464189e463d389124bb0bb6ecbb86"
TAR_SHA = "5a6541e24160cea0445c33e6e03aa62a9bc39cecac2036ec0168e9a96ba6d05f"
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
        assert outer.stat().st_size == 283270770 and sha(outer) == ZIP_SHA
        archive = Path(temp) / "checkpoint.tar.gz"
        with zipfile.ZipFile(outer) as z:
            inv = json.loads(z.read("inventory.json"))
            receipt = json.loads(z.read("receipt.json"))
            with z.open("checkpoint.tar.gz") as src, archive.open("wb") as dest:
                shutil.copyfileobj(src, dest, 1024**2)
        assert archive.stat().st_size == receipt["bytes"]
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


PROGRESS = re.compile(r"^(\d+)/(\d+) (?:-|–) (.+?) (passed|failed|skipped)(.*)$")
STATUS = {"passed": "Passed", "failed": "Failed", "skipped": "Skipped"}


def partial(log, cases):
    found = {}
    for line in log.read_text(errors="replace").splitlines():
        m = PROGRESS.fullmatch(line)
        if m and m[3] in cases and int(m[2]) == len(cases):
            found[m[3]] = {"status": STATUS[m[4]], "detail": m[5].strip()}
    return found


def collect(log, results, cases):
    progress = partial(log, cases)
    if not results.is_file():
        return progress, False
    with results.open(newline="") as f:
        rows = list(csv.DictReader(f))
    found = {}
    for row in rows:
        name, status = row["test"], row["status"]
        if name == "ALL":
            continue
        assert name in cases and name not in found and status in STATUS.values(), row
        found[name] = dict(status=status, duration_seconds=int(row["duration(seconds)"]))
        if name in progress:
            assert progress[name]["status"] == status, name
            found[name]["detail"] = progress[name]["detail"]
    return found, set(found) == set(cases)


def stop_group(process):
    for sig in (signal.SIGTERM, signal.SIGKILL):
        try:
            os.killpg(process.pid, sig)
        except ProcessLookupError:
            break
        if sig == signal.SIGTERM:
            try:
                process.wait(timeout=8)
            except subprocess.TimeoutExpired:
                pass
    process.wait()


def retain_cache_logs(scratch):
    selected = []
    for candidate in scratch.glob("test_runner_*/cache_setup/test_framework.log"):
        selected.append(candidate)
    for candidate in scratch.glob("test_runner_*/cache/node*/**/*"):
        if candidate.name == "debug.log" or candidate.parent.name in {"stderr", "stdout"}:
            selected.append(candidate)
    with (OUT / "cache-startup-diagnostics.log").open("w") as report:
        for candidate in sorted(selected)[:25]:
            if not candidate.is_file() or candidate.is_symlink():
                continue
            report.write(f"\n--- {candidate.relative_to(scratch)} ---\n")
            with candidate.open("rb") as f:
                f.seek(max(0, candidate.stat().st_size - 128 * 1024))
                report.write(f.read().decode(errors="replace"))


def test():
    admitted = json.loads((OUT/"restore-result.json").read_text())
    assert admitted["status"] == "VERIFIED" and admitted["binaries"] == verify_binaries()
    cases = inventory()
    assert cases == json.loads((OUT/"default-inventory.json").read_text())
    shim_dir = ROOT / "no-build"
    shim_dir.mkdir()
    shim = shim_dir / "cmake"
    shim.write_text("#!/bin/sh\nprintf '%s: %s\\n' \"$0\" \"$*\" >> \"$NO_BUILD_LOG\"\n"
                    "echo 'BTX checkpoint policy: build tool invocation refused' >&2\nexit 125\n")
    shim.chmod(0o755)
    for tool in ("ninja", "make"):
        (shim_dir/tool).symlink_to(shim.name)
    env = runtime_env()
    attempts = OUT/"build-attempts.log"
    env["NO_BUILD_LOG"] = str(attempts)
    log = OUT/"functional.log"
    results = OUT/"native-results.csv"
    started = time.monotonic()
    last_notice = started
    reason = None
    with tempfile.TemporaryDirectory(prefix="btf-", dir="/tmp") as temp:
        scratch = Path(temp)
        env["TMPDIR"] = str(scratch)
        args = [PYTHON, RUNNER, "--jobs=4", f"--configfile={CONFIG}",
                f"--resultsfile={results}", f"--tmpdirprefix={scratch}", "--combinedlogslen=100"]
        record("runner-command.json", [str(arg) for arg in args])
        with log.open("wb") as f:
            p = subprocess.Popen(args, cwd=PRODUCT, env=env, stdout=f,
                                 stderr=subprocess.STDOUT, start_new_session=True)
            try:
                while p.poll() is None:
                    current = time.monotonic()
                    if current-started >= CAP-10:
                        reason = "180-minute suite cap"
                        break
                    if shutil.disk_usage(scratch).free < 5 * GIB:
                        reason = "5 GiB storage reserve"
                        break
                    if current-last_notice >= 30:
                        done = partial(log, cases)
                        record("progress.json", done)
                        print(f"{len(done)}/{len(cases)} terminal after {current-started:.0f}s", flush=True)
                        last_notice = current
                    time.sleep(2)
            finally:
                if p.poll() is None or reason:
                    stop_group(p)
        if p.returncode and not results.is_file():
            retain_cache_logs(scratch)
    found, complete = collect(log, results, cases)
    assert verify_binaries() == admitted["binaries"]
    assert sha(CONFIG) == admitted["config_sha256"]
    counts = {k: 0 for k in STATUS.values()}
    counts.update(Counter(x["status"] for x in found.values()))
    failed = sorted(n for n, x in found.items() if x["status"] == "Failed")
    blocked_pattern = "BTX checkpoint policy: build tool invocation refused"
    output = log.read_text(errors="replace")
    failed_blocks = re.split(r"(?m)^(?=\d+/\d+ - )", output)
    no_build_failures = sorted({m[3] for block in failed_blocks if blocked_pattern in block
                                if (m := PROGRESS.fullmatch(block.splitlines()[0]))
                                and m[3] in failed})
    record("suite-result.json", {"status": "COMPLETE" if complete else "INCOMPLETE",
           "source": PIN, "checkpoint": ARTIFACT, "runner_exit": p.returncode,
           "seconds": round(time.monotonic()-started, 2), "stop_reason": reason,
           "expected": len(cases), "counts": counts, "failures": failed,
           "failed_with_build_refusal": no_build_failures,
           "blocked_build_calls": attempts.read_text().splitlines() if attempts.exists() else [],
           "missing": [n for n in cases if n not in found], "cases": found,
           "binary_manifest_unchanged": True})
    print(f"Default suite: {counts}; complete={complete}; runner_exit={p.returncode}", flush=True)
    return 0 if complete and not failed and p.returncode == 0 else 1


if __name__ == "__main__":
    try:
        if sys.argv[1] == "restore":
            restore()
        elif sys.argv[1] == "test":
            sys.exit(test())
        else:
            raise ValueError("Expected restore or test")
    except Exception as exc:
        record(f"{sys.argv[1]}-exception.json", {"type": type(exc).__name__, "error": str(exc)})
        raise
