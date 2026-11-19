"""Same cloud-status regression on release and #861 before/after the diagnostic."""
import json
import os
from pathlib import Path
import shutil
import subprocess

from checkpoint import sha
from results import validate as validate_liveness

workspace = Path(os.environ["GITHUB_WORKSPACE"])
recipe = workspace / "proposal"
records = workspace / "records"
product = workspace / "product"
build = workspace / "gui-pilot-runtime/qtbuild"
helper = build / "bin/btx-modeld"
source = product / "src/modelnet/helper.cpp"
pool = workspace / "retained-binaries"
pool.mkdir()
result = {"complete": False, "steps": []}


def read(path):
    return json.loads(path.read_text())


def save():
    (records / "qualification.json").write_text(json.dumps(result, indent=2) + "\n")


def run(args, label, seconds, expected=0, cwd=workspace):
    with (records / (label + ".log")).open("wb") as log:
        completed = subprocess.run([str(arg) for arg in args], cwd=cwd,
                                   stdout=log, stderr=subprocess.STDOUT, timeout=seconds)
    result["steps"].append({"label": label, "exit_code": completed.returncode})
    save()
    assert completed.returncode == expected, (label, completed.returncode)


def native(name, binary, exit_code):
    run(["python3", "-B", recipe / "observe.py", "--helper", binary,
         "--expected-helper-sha", sha(binary), "--out", records / name],
        name, 120, expected=exit_code)
    observed = read(records / name / "result.json")
    assert observed["complete"] and observed["restored_probe"]["probe_ok"]
    result[name] = {"helper_sha256": sha(binary), "verdict": observed["verdict"],
                    "status_test_sha256": sha(recipe / "observe.py")}
    save()


def compile_variant(name, expected_source_hash):
    assert sha(source) == expected_source_hash
    run(["ninja", "-n", "btx-modeld"], name + "-plan", 90, cwd=build)
    plan = (records / (name + "-plan.log")).read_text()
    actions = [line for line in plan.splitlines() if line.startswith("[")]
    assert 0 < len(actions) <= 36 and any("helper.cpp.o" in line for line in actions), plan
    run(["ninja", "-j2", "btx-modeld"], name + "-build", 900, cwd=build)
    binary = pool / (name + "-btx-modeld")
    shutil.copy2(helper, binary)
    return binary


try:
    staging = read(records / "staging.json")
    current = read(records / "current-binary.json")
    assert staging["complete"] and current["complete"]
    assert sha(helper) == staging["helper_sha256"]
    assert sha(source) == "fd04902a617283e0514378d9bccf9b105bc1feb981bf48374a0d54d7917edf46"
    original_source = source.read_bytes()
    os.environ["BTX_OPENSSL"] = str(workspace / "gui-pilot-runtime/openssl/bin/openssl")
    run([os.environ["BTX_OPENSSL"], "version"], "openssl", 30)
    original = workspace / "current-helper/btx-modeld"
    assert sha(original) == current["helper_sha256"]
    native("release-before", original, 2)
    native("pr861-before", helper, 2)

    # Configure the exactly restored tree and change only the helper source.
    run(["/usr/local/bin/cmake", "-S", product, "-B", build], "configure", 150)
    run(["git", "apply", "--check", "--directory=product", recipe / "composition.patch"], "compose-check", 30)
    run(["git", "apply", "--directory=product", recipe / "composition.patch"], "compose-apply", 30)
    composed = compile_variant("composed", "7910dc39025a98b32145843ee975fb3ab042dc5f67967731d8b8ef91ad87eff4")
    native("pr861-after", composed, 0)
    run(["python3", "-B", recipe / "regression.py", "--helper", composed,
         "--out", records / "pr861-liveness"], "pr861-liveness", 120)
    validate_liveness(read(records / "pr861-liveness/result.json"), "candidate")
    result["pr861_liveness_verified"] = True
    save()

    # Change the sole tracked source difference back to release plus this fix.
    source.write_bytes(original_source)
    run(["git", "apply", "-R", "--directory=product", recipe / "pr861.patch"], "remove-pr861", 30)
    assert sha(source) == "2299c260ee277ef798846538b166a4fc41741440a011b5d09ab95e2a641adf11"
    run(["git", "apply", "--directory=product", recipe / "fix.patch"], "release-apply", 30)
    candidate = compile_variant("release", "bad79ad7df02031a5072717de57f569a65d7096c27df7a60f95eb4d076457118")
    native("release-after", candidate, 0)
    assert len({result[name]["status_test_sha256"] for name in
                ("release-before", "pr861-before", "pr861-after", "release-after")}) == 1
    result["complete"] = True
finally:
    save()
