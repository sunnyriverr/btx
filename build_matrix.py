"""Verify the portable checkpoint and build only the wallet change in the existing native graph."""
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

import checkpoint

ROOT = Path("D:/btx-native-035")
BUILD = ROOT / "project-build"
WORKSPACE = Path(os.environ["GITHUB_WORKSPACE"])
SOURCE = WORKSPACE / "btx"
RECORDS = WORKSPACE / "pr470-records"
MARKER = "2482100da1abb82abda529df0223f815ee8f498fd8cfb470f0803f865db4bdec"
BASE = "dac9aee53520bd49ed320ec7a49b9072fc7d88d9"
PR_HEAD = "a369752d7738af32e5ec9ca33e13bdd13314f5ea"
BASE_EXE = "095647294208a3c534e84f8c399b73d1a5f8daa8e4e9f0b5426d6f899cf775f4"
APPLIED_BLOB = "6ed173b54b4c53e392962cebe68747d0238adbf3"
WALLET_FILE = "src/wallet/rpc/labels.cpp"
BIN = BUILD / "bin/btxd.exe"
state = {"source": BASE, "upstream_pr_head": PR_HEAD, "checkpoint": MARKER, "status": "RESTORING"}
RECORDS.mkdir(exist_ok=True)


def save():
    (RECORDS / "build.json").write_text(json.dumps(state, indent=2) + "\n")


def command(name, argv, cwd, timeout=120):
    out = subprocess.run(argv, cwd=cwd, text=True, encoding="utf-8", errors="replace",
                         stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=timeout)
    (RECORDS / (name + ".txt")).write_text(out.stdout, encoding="utf-8")
    if out.returncode:
        raise RuntimeError(f"{name} exited {out.returncode}")
    return out.stdout.strip()


def main():
    marker = BUILD / "btx-checkpoint.json"
    assert checkpoint.digest(marker) == MARKER
    saved = json.loads(marker.read_text())
    assert saved["profile"]["source"] == BASE and saved["source_catalog"]["head"] == BASE
    assert command("baseline-source", ["git","rev-parse","HEAD"], SOURCE) == BASE
    assert not command("baseline-status", ["git","status","--porcelain","-uno"], SOURCE)
    profile = saved["profile"]["baseline_profile"]
    for name, identity in profile["tools"].items():
        assert checkpoint.digest(Path(identity["path"])) == identity["sha256"], f"{name} differs"
    for key in ("VCToolsVersion", "WindowsSDKVersion", "INCLUDE", "LIB", "LIBPATH"):
        assert os.environ.get(key) == profile["environment"][key], f"{key} differs"
    state["runner_image"] = os.environ.get("ImageVersion")
    state["verified_tool_hashes"] = {name: x["sha256"] for name,x in profile["tools"].items()}
    state["restore"] = checkpoint.restore(ROOT, SOURCE, saved["profile"], saved["source_catalog"])
    assert state["restore"]["files_verified"] == 12858 and checkpoint.digest(BIN) == BASE_EXE
    baseline = Path(os.environ["RUNNER_TEMP"]) / "pr470-baseline/btxd.exe"
    baseline.parent.mkdir(exist_ok=False)
    shutil.copyfile(BIN, baseline)
    state["baseline_sha256"] = checkpoint.digest(baseline)
    assert state["baseline_sha256"] == BASE_EXE
    state["status"] = "BASELINE_VERIFIED"
    save()
    command("apply-check", ["git","apply","--check",str(WORKSPACE / "wallet-only.patch")], SOURCE)
    command("apply", ["git","apply",str(WORKSPACE / "wallet-only.patch")], SOURCE)
    assert command("candidate-blob", ["git","hash-object",WALLET_FILE], SOURCE) == APPLIED_BLOB
    assert command("candidate-file-list", ["git","diff","--name-only"], SOURCE) == WALLET_FILE
    state["candidate_product_blob"] = APPLIED_BLOB
    state["status"] = "CHECKING_INCREMENTAL_PLAN"
    save()
    ninja = profile["tools"]["ninja"]["path"]
    glob = BUILD / "CMakeFiles/VerifyGlobs.cmake"
    if glob.exists():
        assert "GLOB mismatch!" not in command(
            "verify-globs", [profile["tools"]["cmake"]["path"],"-P",str(glob)], BUILD
        )
    # A Ninja dry run treats CMake's forced glob-check input as dirty
    # even after its standalone check passed. Use an unedited copy of
    # the verified graph so its self-regeneration edge does not mask
    # the actual plan for this one .cpp change.
    manifest = RECORDS / "pr470-build.ninja"
    shutil.copyfile(BUILD / "build.ninja", manifest)
    state["manifest_sha256"] = checkpoint.digest(manifest)
    assert state["manifest_sha256"] == "d5c9f1da48829c4f5d8321730897b0eda9265579ea9de11b374d4992329d7348"
    plan = command("candidate-plan", [ninja,"-f",str(manifest),"-n","-d","explain","btxd"], BUILD)
    actions = re.findall(r"^\[\d+/\d+\].*",plan,re.M)
    state["planned_actions"] = actions
    save()
    assert 3 <= len(actions) <= 12 and any("labels.cpp.obj" in row for row in actions)
    assert any("bitcoin_wallet.lib" in row for row in actions) and any("btxd.exe" in row for row in actions)
    allowed_objects = ("labels.cpp.obj", "clientversion.cpp.obj", "matmul_v4_rc_production_canary.cpp.obj")
    assert all(any(name in row for name in allowed_objects)
               for row in actions if "Building" in row), actions
    assert all(any(name in row for name in ("bitcoin_wallet.lib", "bitcoin_common.lib",
                                           "bitcoin_clientversion.lib", "btxd.exe"))
               for row in actions if "Linking" in row), actions
    assert all("Generating bitcoin-build-info.h" in row or "Building CXX object" in row
               or "Linking CXX" in row for row in actions), actions
    assert "stored deps info out of date" not in plan and "Re-running CMake" not in plan
    state["status"] = "INCREMENTAL_RELINK"
    save()
    command("candidate-build", [ninja,"-f",str(manifest),"-j2","-k1","btxd"], BUILD, timeout=420)
    state["candidate_sha256"] = checkpoint.digest(BIN)
    assert state["candidate_sha256"] != BASE_EXE
    assert checkpoint.digest(baseline) == BASE_EXE
    manifest.unlink()
    state["status"] = "INCREMENTAL_BUILD_COMPLETE"
    save()


try:
    main()
except BaseException as error:
    state["error"] = repr(error)
    save()
    raise
