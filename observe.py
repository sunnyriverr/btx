"""Native Qt test launcher. Reuses the existing stale-backup wallet fixture."""
import configparser
import hashlib
import json
import os
import shutil
import subprocess
from pathlib import Path

w = Path(os.environ["GITHUB_WORKSPACE"])
out = w/"native-records"
out.mkdir()
source = w/"accepted-source"
case = source/"test/functional/qt_recovery_fixture.py"
shutil.copyfile(w/"qt_recovery_fixture.py", case)
expected = json.loads((w/"verified-build/result.json").read_text())
assert expected["source"] == "dac9aee53520bd49ed320ec7a49b9072fc7d88d9" and expected["phase"] == "built"
library = w/"scan-delay.so"
subprocess.run(["cc","-Wall","-Wextra","-Werror","-fPIC","-shared",w/"scan-delay.c","-o",library,"-ldl"],
               check=True, timeout=30)
result = {"source": expected["source"], "patch_sha256": expected["patch_sha256"], "cases": {}}
def sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()

def run(variant, qt):
    records = out/variant
    records.mkdir()
    env = dict(os.environ, RECOVERY_QT=str(qt), RECOVERY_VARIANT=variant, RECOVERY_RECORDS=str(records),
               RECOVERY_DELAY_LIBRARY=str(library))
    for path in (qt, w/"candidate/bin/btxd", w/"candidate/bin/btx-cli"):
        path.chmod(0o755)
    ini = configparser.ConfigParser()
    ini["environment"] = {"CLIENT_NAME":"BTX","CLIENT_BUGREPORT":"https://github.com/btxchain/btx/issues",
                          "SRCDIR":str(source),"BUILDDIR":str(w/"candidate"),"EXEEXT":"",
                          "RPCAUTH":str(source/"share/rpcauth/rpcauth.py")}
    ini["components"] = {
        "ENABLE_WALLET": "true", "USE_SQLITE": "true", "USE_BDB": "false",
        "ENABLE_ZMQ": "true", "ENABLE_MODELNET": "true",
        "ENABLE_EXTERNAL_SIGNER": "true", "ENABLE_CLI": "true",
        "ENABLE_BITCOIND": "true", "ENABLE_WALLET_TOOL": "false",
        "ENABLE_BITCOIN_UTIL": "false", "ENABLE_USDT_TRACEPOINTS": "false",
    }
    config = records/"config.ini"
    with config.open("w") as f:
        ini.write(f)
    tmp = w/f"isolated-{variant}"
    cmd = ["dbus-run-session","--","xvfb-run","-a","-s","-screen 0 1440x1000x24 -nolisten tcp",
           "sh","-ec", 'openbox >/dev/null 2>&1 & exec /usr/bin/python3 "$@"', "sh", str(case),
           "--descriptors", "--configfile="+str(config),"--tmpdir="+str(tmp),"--nocleanup"]
    with (records/"test.log").open("wb") as log:
        process = subprocess.Popen(cmd, env=env, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
        try:
            code = process.wait(timeout=220)
        except subprocess.TimeoutExpired:
            import signal
            os.killpg(process.pid, signal.SIGTERM)
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                process.wait()
            raise
        finally:
            if tmp.is_dir():
                for filename in ("test_framework.log", "node0/regtest/debug.log"):
                    path = tmp/filename
                    if path.is_file():
                        shutil.copyfile(path, records/Path(filename).name)
                shutil.rmtree(tmp)
    result["cases"][variant] = {"exit":code,"qt_sha256":sha(qt)}
    assert code == 0, variant
    log = (records/"test.log").read_text(errors="replace")
    if variant == "baseline":
        assert "BASELINE: Transactions tab renders and has no recovery action" in log
    else:
        assert "CANDIDATE: active scan cancelled, reservation released, wallet relocked" in log
        assert "CANDIDATE: retry recovered both exact outpoints at the same tip and relocked" in log
        assert "CONTROL: action preserved an existing unlock and its RPC relock policy" in log
        assert "CONTROL: direct RPC rescan still reaches the same tip and preserves both receipts" in log

try:
    baseline = w/"prior-binaries/baseline/bin/btx-qt"
    candidate = w/"candidate/bin/btx-qt"
    assert sha(baseline) == expected["baseline_binaries"]["btx-qt"]
    assert sha(candidate) == expected["candidate_qt"]
    assert all(sha(w/"candidate/bin"/n) == expected["baseline_binaries"][n] for n in ("btxd","btx-cli"))
    package_paths = subprocess.check_output(["dpkg-query", "-L", "qt6-qpa-plugins"], text=True, timeout=15)
    (qpa,) = [Path(x) for x in package_paths.splitlines() if x.endswith("/platforms/libqxcb.so")]
    result["fixture_sha256"] = sha(case)
    for label, path in {
        "baseline-qt": baseline, "candidate-qt": candidate,
        "daemon": w/"candidate/bin/btxd", "cli": w/"candidate/bin/btx-cli",
        "qt-xcb": qpa,
    }.items():
        assert path.is_file(), path
        loaded = subprocess.check_output(["ldd", path], text=True, timeout=20)
        (out/(label+"-ldd.log")).write_text(loaded)
        assert "not found" not in loaded, label
    prior = w/"verified-baseline/result.json"
    if prior.exists():
        saved = json.loads(prior.read_text())
        assert saved["source"] == expected["source"]
        assert saved["fixture_sha256"] == "1d619c2079758d955de3f05a777ce0268d3d4bd02481a9cea36c6cb31925e58b"
        assert saved["patch_sha256"] == expected["patch_sha256"]
        baseline_log = (prior.parent/"baseline/test.log").read_text()
        assert "BASELINE: Transactions tab renders and has no recovery action" in baseline_log
        assert "Tests successful" in baseline_log
        result["baseline_fixture_sha256"] = saved["fixture_sha256"]
        assert saved["cases"]["baseline"] == {"exit":0,"qt_sha256":sha(baseline)}
        result["cases"]["baseline"] = dict(saved["cases"]["baseline"], reused=True)
    else:
        run("baseline", baseline)
    if os.environ.get("RECOVERY_BASELINE_ONLY") == "1":
        result["verdict"] = "BASELINE_PASS"
    else:
        run("candidate", candidate)
        result["verdict"] = "PASS"
except Exception as exc:
    result["error"] = repr(exc)
    raise
finally:
    (out/"result.json").write_text(json.dumps(result, indent=2)+"\n")
