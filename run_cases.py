"""Verify retained bytes and run three named upstream tests without a build."""
import hashlib
import json
import os
import shutil
import signal
import subprocess
import sys
import tarfile
import tempfile
import time
import zipfile
from pathlib import Path

root = Path.cwd()
records = root / "records"
expected = json.loads((root / "expected.json").read_text())
archive = Path(sys.argv[1])
cases = {
    "feature_btx_block_capacity": ["--descriptors"],
    "feature_shielded_v2_multinode_validation": [],
    "p2p_shielded_relay": [],
}


def digest(path):
    with path.open("rb") as f:
        return hashlib.file_digest(f, "sha256").hexdigest()


def hashes(bindir):
    return {name: digest(bindir / name) for name in expected["binaries"]}


def run_case(name, args, env, config, data):
    started = time.monotonic()
    is_timeout = False
    log = records / f"{name}.log"
    command = [sys.executable, str(root / "product/test/functional" / f"{name}.py"),
               f"--configfile={config}", f"--tmpdir={data}", *args]
    with log.open("w") as out:
        process = subprocess.Popen(command, env=env, stdout=out, stderr=subprocess.STDOUT,
                                   start_new_session=True)
        try:
            code = process.wait(timeout=420)
        except subprocess.TimeoutExpired:
            is_timeout = True
            os.killpg(process.pid, signal.SIGTERM)
            try:
                code = process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                code = process.wait()
    text = log.read_text(errors="replace")
    if is_timeout:
        status = "timeout"
    elif code == 77 or "Test skipped" in text:
        status = "skip"
    elif code == 0 and "Tests successful" in text:
        status = "pass"
    else:
        status = "fail"
    return dict(status=status, exit_code=code, seconds=round(time.monotonic() - started, 2),
                arguments=args)


assert digest(archive) == expected["zip_sha256"]
with tempfile.TemporaryDirectory(prefix="btx-mac-fixture-") as scratch:
    scratch = Path(scratch)
    bindir = scratch / "bin"
    bindir.mkdir()
    package = scratch / "binaries.tar.gz"
    with zipfile.ZipFile(archive) as z:
        with z.open("mac-arm-7d65025b-shielded-fixture.tar.gz") as src, package.open("xb") as dest:
            shutil.copyfileobj(src, dest)
    assert digest(package) == expected["package_sha256"]
    with tarfile.open(package, "r:gz") as tar:
        for member in tar:
            name = member.name.removeprefix("./")
            if name in expected["binaries"]:
                assert member.isfile() and member.mode & 0o111
                path = bindir / name
                with tar.extractfile(member) as src, path.open("xb") as dest:
                    shutil.copyfileobj(src, dest)
                path.chmod(0o755)
    assert hashes(bindir) == expected["binaries"]
    for name in expected["binaries"]:
        assert subprocess.check_output(["lipo", "-archs", str(bindir / name)], text=True).strip() == "arm64"

    config = scratch / "config.ini"
    config.write_text(f"""[environment]
CLIENT_NAME=BTX
CLIENT_BUGREPORT=https://github.com/btxchain/btx/issues
SRCDIR={root / 'product'}
BUILDDIR={scratch}
EXEEXT=
RPCAUTH={root / 'product/share/rpcauth/rpcauth.py'}
[components]
ENABLE_WALLET=true
USE_SQLITE=true
ENABLE_CLI=true
ENABLE_BITCOIND=true
""")
    shimdir = scratch / "no-build"
    shimdir.mkdir()
    shim = shimdir / "cmake"
    shim.write_text('#!/bin/sh\nprintf "%s\\n" "$0" >> "$BTX_BUILD_ATTEMPTS"\nexit 125\n')
    shim.chmod(0o755)
    for name in ("ninja", "make"):
        (shimdir / name).symlink_to("cmake")
    env = dict(os.environ, PATH=f"{shimdir}:{os.environ['PATH']}", PYTHONUNBUFFERED="1",
               BTX_BUILD_ATTEMPTS=str(records / "build-attempts.log"))
    for name in ("BTXD", "BTXCLI", "BITCOIND", "BITCOINCLI", "BTX_RUN_UPSTREAM_BASE_SUITE"):
        env.pop(name, None)
    receipt = dict(source=expected["source"], artifact=expected["artifact"], binaries=expected["binaries"],
                   cases={}, status="running")
    for name, args in cases.items():
        result = run_case(name, args, env, config, scratch / name)
        receipt["cases"][name] = result
        print(name, result, flush=True)
        (records / "results.json").write_text(json.dumps(receipt, indent=2) + "\n")
    assert hashes(bindir) == expected["binaries"]
    receipt["build_attempts"] = (records / "build-attempts.log").exists()
    receipt["status"] = "pass" if all(r["status"] == "pass" for r in receipt["cases"].values()) and not receipt["build_attempts"] else "incomplete_or_failed"
    (records / "results.json").write_text(json.dumps(receipt, indent=2) + "\n")
    sys.exit(receipt["status"] != "pass")
