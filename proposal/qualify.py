"""Bounded retained-cache build and an identical contact test before and after."""
import json
import os
from pathlib import Path
import shutil
import subprocess

from checkpoint import sha

workspace = Path(os.environ["GITHUB_WORKSPACE"])
recipe = workspace / "proposal"
records = workspace / "records"
product = workspace / "product"
build = workspace / "gui-pilot-runtime/qtbuild"
source = product / "src/modelnet"
retained = workspace / "retained-binaries"
result = {"complete": False, "steps": []}


def read(path):
    return json.loads(path.read_text())


def save():
    (records / "qualification.json").write_text(json.dumps(result, indent=2) + "\n")


def run(args, label, seconds, expected=0, cwd=workspace):
    print(label, flush=True)
    with (records / (label + ".log")).open("wb") as log:
        child = subprocess.run([str(arg) for arg in args], cwd=cwd, stdout=log,
                               stderr=subprocess.STDOUT, timeout=seconds)
    result["steps"].append({"label": label, "exit_code": child.returncode})
    save()
    assert child.returncode == expected, (label, child.returncode)


def native(label, executable, exit_code):
    run(["python3", "-B", recipe / "observe.py", "--helper", executable,
         "--expected-helper-sha", sha(executable), "--out", records / label],
        label, 150, expected=exit_code)
    observed = read(records / label / "result.json")
    assert observed["complete"] and observed["runtime_removed"]
    result[label] = {"binary_sha256": sha(executable), "test_sha256": sha(recipe / "observe.py"),
                     "verdict": observed["verdict"]}
    save()


try:
    stage = read(records / "staging.json")
    baseline = read(records / "current-binary.json")
    assert stage["complete"] and baseline["complete"]
    keep = workspace / "current-helper/btx-modeld"
    hashes = read(recipe / "source-hashes.json")
    assert sha(keep) == baseline["helper_sha256"]
    assert sha(source / "helper.cpp") == "fd04902a617283e0514378d9bccf9b105bc1feb981bf48374a0d54d7917edf46"
    os.environ["BTX_OPENSSL"] = str(workspace / "gui-pilot-runtime/openssl/bin/openssl")
    run([os.environ["BTX_OPENSSL"], "version"], "openssl", 30)
    native("before", keep, 2)
    run(["git", "apply", "-R", "--directory=product", recipe / "cached-helper-overlay.patch"],
        "restore-release-helper-source", 45)
    assert all(sha(source / name) == value for name, value in hashes["baseline"].items())
    run(["git", "apply", "--check", "--directory=product", recipe / "fix.patch"], "check-patch", 45)
    run(["git", "apply", "--directory=product", recipe / "fix.patch"], "apply-patch", 45)
    assert all(sha(source / name) == value for name, value in hashes["candidate"].items())
    run(["/usr/local/bin/cmake", "-S", product, "-B", build], "configure", 150)
    run(["ninja", "-n", "btx-modeld"], "build-plan", 90, cwd=build)
    plan = (records / "build-plan.log").read_text()
    count = sum(line.startswith("[") for line in plan.splitlines())
    result["scheduled_actions"] = count
    save()
    assert 0 < count <= 140 and "helper.cpp.o" in plan and "catalog.cpp.o" in plan
    assert shutil.disk_usage(workspace).free > 3 * 1024**3
    run(["ninja", "-j2", "btx-modeld"], "candidate-build", 1800, cwd=build)
    retained.mkdir()
    executable = retained / "btx-modeld"
    shutil.copy2(build / "bin/btx-modeld", executable)
    native("after", executable, 0)
    assert result["before"]["test_sha256"] == result["after"]["test_sha256"]
    result["complete"] = True
finally:
    save()
