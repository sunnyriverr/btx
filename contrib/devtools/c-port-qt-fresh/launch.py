"""Require a native window from the exact extracted shipping Qt launcher."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time

package, probe, evidence = map(Path, sys.argv[1:])
with tempfile.TemporaryDirectory(prefix="c-port-qt-") as temp:
    env = {"HOME": temp, "TMPDIR": temp, "PATH": "/usr/bin:/bin",
           "CFFIXED_USER_HOME": temp, "DYLD_PRINT_LIBRARIES": "1"}
    args = [package / "bin/btx-qt", "-regtest", "-datadir=" + temp,
            "-disablewallet", "-modelnet=0", "-splash=0", "-server=0",
            "-listen=0", "-networkactive=0", "-connect=0", "-dnsseed=0",
            "-discover=0", "-natpmp=0"]
    log = evidence / "qt-dyld.log"
    with log.open("w") as output:
        process = subprocess.Popen(args, env=env, cwd=temp, stdout=output,
                                   stderr=subprocess.STDOUT)
        try:
            for _ in range(80):
                if process.poll() is not None:
                    raise RuntimeError(f"Packaged Qt exited {process.returncode}")
                windows = json.loads(subprocess.check_output([probe, str(process.pid)], timeout=5))
                for window in windows:
                    bounds = window.get("kCGWindowBounds", {})
                    if window.get("kCGWindowLayer") == 0 and bounds.get("Width", 0) > 600 and bounds.get("Height", 0) > 400:
                        print("Packaged Qt main window visible", bounds, flush=True)
                        time.sleep(2)
                        assert process.poll() is None
                        break
                else:
                    time.sleep(.5)
                    continue
                break
            else:
                raise RuntimeError("Packaged Qt main window never appeared")
        finally:
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=15)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()
    assert process.returncode == 0, f"Qt shutdown exit {process.returncode}"
    assert not any("/opt/homebrew/" in line or "/usr/local/opt/" in line
                   for line in log.read_text().splitlines() if line.startswith("dyld["))
    print("Qt clean shutdown", process.returncode)
