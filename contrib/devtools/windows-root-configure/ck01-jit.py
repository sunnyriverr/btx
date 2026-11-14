"""Verify the native checkpoint, then configure and dry-run the exact repair tree."""
import json
import os
import re
import shutil
from pathlib import Path

import checkpoint
import restore_support as existing

s = existing.s
evidence = existing.E
build = existing.B
source = existing.SOURCE
root = existing.ROOT
existing.prepare()
marker = json.loads((build / "btx-checkpoint.json").read_text())
profile = marker["profile"]
base = "88c9b49cb16360fc8fbf3f84003b8b54c29e6db5"

s.need("release-fetch", ["git", "fetch", "--no-tags", "--depth=1",
                        "https://github.com/btxchain/btx.git", base], 180)
s.need("release-checkout", ["git", "checkout", "--detach", base], 90)
patch = Path(__file__).with_name("ck01-jit.patch")
s.need("apply-tested-deltas", ["git", "apply", "--index", str(patch)], 120)
expected_tree = Path(__file__).with_name("ck01-jit-tree.txt").read_text().strip()
s.need("candidate-tree", ["git", "write-tree"], 60)
assert (evidence / "candidate-tree.log").read_text().strip() == expected_tree
# Verify the index and working files agree before planning.
s.need("candidate-worktree", ["git", "diff", "--exit-code"], 90)

os.environ.update(VCPKG_ROOT=str(root / "vcpkg"), VCPKG_DISABLE_METRICS="1",
                  VCPKG_MAX_CONCURRENCY="2",
                  VCPKG_BINARY_SOURCES=f"clear;files,{root / 'binary-cache'},read")
args = profile["actual_configure"]
assert args[0] == "cmake"
assert "-DVCPKG_INSTALL_OPTIONS=--only-binarycaching" in args
assert all(flag in args for flag in ("-DWITH_MODELNET=ON", "-DBUILD_TESTS=ON"))
s.need("candidate-configure", args, 900)
glob_check = build / "CMakeFiles/VerifyGlobs.cmake"
if glob_check.exists():
    s.need("candidate-verify-globs", ["cmake", "-P", str(glob_check)], 120, cwd=build)
manifest = evidence / "candidate-manifest.ninja"
shutil.copyfile(build / "build.ninja", manifest)
s.need("candidate-dry-run", ["ninja", "-C", str(build), "-f", str(manifest),
                             "-n", "-d", "explain", "test_btx"], 180, cwd=build)
plan = (evidence / "candidate-dry-run.log").read_text(errors="replace")
actions = re.findall(r"^\[\d+/\d+\] (.+)$", plan, re.M)
objects = {key: info for key, info in marker["files"].items() if key.endswith(".obj")}
assert len(objects) == 5901
assert all(checkpoint.digest(root / key) == info["sha256"] for key, info in objects.items())
result = {
    "base": base, "candidate_tree": expected_tree, "verified_objects_unchanged": len(objects),
    "actions": len(actions), "compile_actions": sum("Building CXX object" in x or
                                                    "Building C object" in x for x in actions),
    "stale_dependencies": plan.count("stored deps info out of date"),
    "regeneration_only": bool(re.search("Re-running CMake|Re-checking globbed", plan)),
    "product_compiled": False,
}
(evidence / "cport-checkpoint-plan.json").write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps(result), flush=True)
assert actions and not result["regeneration_only"]

# Refuse to turn this bounded test repair into an accidental cold build.
assert result["actions"] <= 450 and result["stale_dependencies"] == 0, result
s.need("candidate-unit-build", ["ninja", "-C", str(build), "-j", "3", "test_btx"],
       2400, cwd=build)
binary = build / "bin/test_btx.exe"
assert binary.is_file()
s.need("built-candidate-tree", ["git", "write-tree"], 60)
assert (evidence / "built-candidate-tree.log").read_text().strip() == expected_tree
s.need("built-candidate-worktree", ["git", "diff", "--exit-code"], 90)
(evidence / "linked-binary-sha256.txt").write_text(checkpoint.digest(binary) + "\n")

suite = "modelnet_jit_tests"
test_temp = root / "focused-tests-temp"
test_temp.mkdir(exist_ok=True)
os.environ.update(TEMP=str(test_temp), TMP=str(test_temp))
status = s.run(suite, [str(binary), "--run_test=" + suite,
                       "--color_output=no", "--log_level=all"], 150, cwd=build)
lines = (evidence / (suite + ".log")).read_text(errors="replace").splitlines()
entered = re.findall(r'Entering test case "([^"]+)"', "\n".join(lines))
exited = re.findall(r'Leaving test case "([^"]+)"', "\n".join(lines))
# Boost reports out-of-filter suites as disabled. Check skips within this suite only.
skips = [line for line in lines if 'Test case "' in line and 'is skipped' in line]
checks = {str(n): any(re.search(rf"modelnet_jit_tests.cpp\({n}\): info: .* has passed", line)
                       for line in lines) for n in (872, 880, 881, 882, 887, 889, 890)}
verdict = dict(suite=suite, exit=status, entered=entered, exited=exited,
               skips=skips, checks=checks, head_tree=expected_tree,
               binary_sha256=checkpoint.digest(binary),
               compiler=profile.get("baseline_profile"),
               runner_os=os.environ.get("RUNNER_OS"))
(evidence / "ck01-jit-result.json").write_text(json.dumps(verdict, indent=2) + "\n")
assert "Running 11 test cases..." in lines, verdict
assert len(entered) == len(set(entered)) == 11 and entered == exited, verdict
assert entered.count("jit_map_range_mat_load") == 1 and not skips, verdict
assert all(checks.values()) and status == 0, verdict
assert any(line.strip().rstrip(".") == "*** No errors detected" for line in lines), verdict
