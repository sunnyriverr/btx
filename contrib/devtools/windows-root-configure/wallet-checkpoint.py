"""Exercise only the standalone Windows wallet link against the restored profile."""
import json
import os
from pathlib import Path
import re
import shutil
import tempfile

import checkpoint
import cport_wallet_smoke as smoke
import restore_support as existing

files = Path(__file__).resolve().parent
s = existing.s
evidence, build, root = existing.E, existing.B, existing.ROOT
existing.prepare()
profile = json.loads((build / "btx-checkpoint.json").read_text())["profile"]
base = "88c9b49cb16360fc8fbf3f84003b8b54c29e6db5"
s.need("release-fetch", ["git", "fetch", "--no-tags", "--depth=1",
                        "https://github.com/btxchain/btx.git", base], 180)
s.need("release-checkout", ["git", "checkout", "--detach", base], 90)
os.environ.update(VCPKG_ROOT=str(root / "vcpkg"), VCPKG_DISABLE_METRICS="1",
                  VCPKG_MAX_CONCURRENCY="2",
                  VCPKG_BINARY_SOURCES=f"clear;files,{root / 'binary-cache'},read")
configure = profile["actual_configure"]
assert configure[0] == "cmake"
assert "-DVCPKG_INSTALL_OPTIONS=--only-binarycaching" in configure
assert "-DVCPKG_MANIFEST_FEATURES=wallet;tests;zeromq" in configure
target = ["ninja", "-C", str(build), "-j", "3", "btx-wallet"]

def configure_tree(label, patch):
    s.need(f"{label}-patch", ["git", "apply", "--index", str(files / patch)], 120)
    s.need(f"{label}-tree", ["git", "write-tree"], 60)
    expected = (files / f"wallet-checkpoint-{label}.txt").read_text().strip()
    assert (evidence / f"{label}-tree.log").read_text().strip() == expected
    s.need(f"{label}-worktree", ["git", "diff", "--exit-code"], 90)
    s.need(f"{label}-configure", configure, 900)
    config_log = (evidence / f"{label}-configure.log").read_text(errors="replace")
    assert re.search(r"btx-wallet +\.+ +ON", config_log)
    glob_check = build / "CMakeFiles/VerifyGlobs.cmake"
    if glob_check.exists():
        s.need(f"{label}-globs", ["cmake", "-P", str(glob_check)], 120, cwd=build)
    manifest = evidence / f"{label}-manifest.ninja"
    shutil.copyfile(build / "build.ninja", manifest)
    s.need(f"{label}-plan", ["ninja", "-C", str(build), "-f", str(manifest),
                            "-n", "-d", "explain", "btx-wallet"], 180, cwd=build)
    plan = (evidence / f"{label}-plan.log").read_text(errors="replace")
    actions = re.findall(r"^\[\d+/\d+\]", plan, re.M)
    assert 0 < len(actions) <= 500, len(actions)
    assert not re.search("Re-running CMake|Re-checking globbed", plan)
    return expected

before = configure_tree("before", "wallet-checkpoint-prerequisite.patch")
baseline_rc = s.run("wallet-baseline-link", target, 2400, cwd=build)
baseline_log = (evidence / "wallet-baseline-link.log").read_text(errors="replace")
assert baseline_rc and "lld-link: error: undefined symbol:" in baseline_log
assert "GetTransactionSigOpCost" in baseline_log and "g_weight_per_data_byte" in baseline_log
after = configure_tree("after", "wallet-link.patch")
s.need("wallet-candidate-link", target, 900, cwd=build)
exe = build / "bin/btx-wallet.exe"
assert exe.is_file()
with tempfile.TemporaryDirectory(prefix="wallet-smoke-", dir=root) as scratch:
    smoke.wallet(exe, evidence, Path(scratch))
(evidence / "wallet-checkpoint-result.json").write_text(json.dumps({
    "release": base, "before_tree": before, "after_tree": after,
    "baseline_link_exit": baseline_rc, "candidate_link_exit": 0,
    "create_and_reopen": "pass", "binary_sha256": checkpoint.digest(exe),
}, indent=2) + "\n")
