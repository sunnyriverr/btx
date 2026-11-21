"""Gate the incremental build on the exact approved Mac Ninja plan."""
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import time

root = Path(os.environ["GITHUB_WORKSPACE"])
records = root / "records"
build = root / "mac-config-build"
targets = ["btxd", "btx-cli"]
pin = "63c0475d4a8b11e80f727688c5c6d203a0ab938f"
admission = json.loads((records / "result.json").read_text())
assert admission["source"] == pin and admission["checkpoint"] == 14703680085
assert admission["status"] == "PASS_DRY_RUN" and admission["binary_hashes_unchanged"]
assert admission["functional_profile_targets"] == targets
expected = (root / "proposal/expected-plan.txt").read_text().splitlines()
observed = (records / "planned-actions.txt").read_text().splitlines()
assert len(expected) == 11 and Counter(expected) == Counter(observed)
target_paths = [build / "bin" / name for name in targets]


def hashes():
    result = {}
    for path in target_paths:
        with path.open("rb") as f:
            result[path.name] = hashlib.file_digest(f, "sha256").hexdigest()
    return result


before = hashes()
started = time.monotonic()
command = ["ninja", "-C", str(build), "-j2", *targets]
env = dict(os.environ, NINJA_STATUS="[%f/%t] ",
           BTX_OPENSSL="/opt/homebrew/opt/openssl@3/bin/openssl")
with (records / "build.log").open("wb") as log:
    with subprocess.Popen(command, env=env, stdout=log, stderr=subprocess.STDOUT,
                          start_new_session=True) as proc:
        try:
            proc.wait(timeout=720)
        except subprocess.TimeoutExpired:
            os.killpg(proc.pid, signal.SIGTERM)
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                os.killpg(proc.pid, signal.SIGKILL)
                proc.wait(timeout=5)
rows = re.findall(r"(?m)^\[\d+/\d+\] (.*)$", (records / "build.log").read_text(errors="replace"))
exit_code = proc.returncode
result = dict(source=pin, checkpoint=14703680085, targets=targets, planned=len(expected),
              executed=len(rows), exit=exit_code, seconds=round(time.monotonic()-started, 2))
try:
    assert exit_code == 0 and not (Counter(rows) - Counter(expected))
    assert "Linking CXX executable bin/btxd" in rows
    assert any(row.endswith("/rpc/backup.cpp.o") for row in rows)
    for path in target_paths:
        assert subprocess.check_output(["lipo", "-archs", str(path)], text=True).strip() == "arm64"
    after = hashes()
    assert after["btxd"] != before["btxd"]
    result.update(status="PASS", before_binary_sha256=before, binary_sha256=after, actions=rows)
finally:
    (records / "build-result.json").write_text(json.dumps(result, indent=2)+"\n")
