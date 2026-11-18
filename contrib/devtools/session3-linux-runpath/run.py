#!/usr/bin/env python3
"""Bounded inert Linux producer probe; contains no BTX runtime or wallet calls."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parent
SONAME = "libbtx_s3_runpath_marker_a97af7b3.so.1"
EXPECTED_OUTPUT = "btx-runpath-probe:42\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--work", type=Path, required=True,
                        help="New, exclusively owned results/build directory")
    parser.add_argument("--cmake", required=True, help="Exact CMake 3.22 executable")
    parser.add_argument("--ninja", action="store_true", help="Also check the neighboring generator")
    args = parser.parse_args()
    if not sys.platform.startswith("linux"):
        parser.error("This is a Linux ELF generator/loader check")
    cmake = Path(args.cmake).resolve()
    if not cmake.is_file() or not os.access(cmake, os.X_OK):
        parser.error("--cmake must identify an executable file")
    readelf = shutil.which("readelf")
    if not readelf or not shutil.which("make") or not shutil.which("c++"):
        parser.error("readelf, make and a C++ compiler must already be available")
    if args.ninja and not shutil.which("ninja"):
        parser.error("Ninja requested but unavailable; no automatic installation")
    work = args.work.resolve()
    if work.exists():
        parser.error("--work must not exist; preserve prior evidence")
    work.mkdir(parents=True)
    # Keep tool discovery, but remove loader overrides and all compiler/CMake
    # environment knobs. No user environment or credentials are logged.
    env = {"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "LC_ALL": "C",
           "HOME": str(work / "home")}
    (work / "home").mkdir()
    result = {"status": "INCOMPLETE", "scope": "inert exact-module ELF probe only",
              "cases": [], "commands": [], "inputs": {}}
    started = time.monotonic()
    stage = "admission"

    def command(argv, cwd=None):
        remaining = 300 - (time.monotonic() - started)
        if remaining <= 0:
            raise RuntimeError("Five-minute fixture budget exhausted")
        entry = {"argv": [str(a) for a in argv], "cwd": str(cwd or work)}
        result["commands"].append(entry)
        index = len(result["commands"])
        log = "command-%03d.log" % index
        proc = subprocess.Popen(entry["argv"], cwd=entry["cwd"], env=env,
                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                text=True, start_new_session=True)
        try:
            output, _ = proc.communicate(timeout=min(60, remaining))
        except subprocess.TimeoutExpired:
            # CMake/make can have compiler children: stop our whole new process
            # group, retain output and reap it before reporting a timeout.
            entry["timeout"] = True
            try:
                os.killpg(proc.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            output, _ = proc.communicate()
            (work / log).write_text(output)
            entry.update(returncode=proc.returncode, log=log)
            raise
        (work / log).write_text(output)
        entry.update(returncode=proc.returncode, log=log)
        return proc.returncode, output

    def require(condition, message):
        if not condition:
            raise RuntimeError(message)

    def successful(argv, cwd=None):
        code, output = command(argv, cwd)
        require(code == 0, "Command failed; see retained command log")
        return output

    try:
        manifest = json.loads((ROOT / "INPUTS.json").read_text())
        for name, expected in manifest["files"].items():
            actual = hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
            require(actual == expected, "Fixture input changed: " + name)
            result["inputs"][name] = actual
        result["source_revisions"] = manifest["source_revisions"]
        version = successful([cmake, "--version"])
        require(re.match(r"cmake version 3\.22\.\d+\b", version),
                "Original minimum-toolchain case requires CMake 3.22.x")
        successful(["c++", "--version"])
        successful(["make", "--version"])
        successful([readelf, "--version"])
        generators = ["Unix Makefiles"] + (["Ninja"] if args.ninja else [])
        if args.ninja:
            successful(["ninja", "--version"])
        for generator in generators:
            for variant in ("before", "after", "opt-out"):
                stage = generator + ":" + variant
                case_root = work / (generator.replace(" ", "-") + "-" + variant)
                case_root.mkdir()
                build = case_root / "build"
                module = ROOT / "modules" / (("before" if variant == "before" else "after") + ".cmake")
                case = {"generator": generator, "variant": variant, "status": "INCOMPLETE"}
                result["cases"].append(case)
                successful([cmake, "-S", ROOT, "-B", build, "-G", generator,
                            "-DBTX_MODULE_FILE=" + str(module),
                            "-DCMAKE_BUILD_TYPE=Release",
                            "-DCMAKE_SKIP_BUILD_RPATH=" + ("ON" if variant == "opt-out" else "OFF")])
                successful([cmake, "--build", build, "--parallel", "1", "--verbose"])
                dynamic = successful([readelf, "-d", build / "bin/probe"])
                needed = re.findall(r"\(NEEDED\).*?\[(.*?)\]", dynamic)
                runpaths = re.findall(r"\(RUNPATH\).*?\[(.*?)\]", dynamic)
                rpaths = re.findall(r"\(RPATH\).*?\[(.*?)\]", dynamic)
                case.update(needed=needed, runpath=runpaths, rpath=rpaths)
                require(SONAME in needed, "Probe does not depend on the marker library")
                installed = case_root / "relocated"
                shutil.copytree(build / "bin", installed / "bin", symlinks=True)
                shutil.copytree(build / "lib", installed / "lib", symlinks=True)
                # Remove the build location from resolution without destroying
                # its logs or binaries. Nothing here references a peer cache.
                build.rename(case_root / "build-retained")
                code, output = command([installed / "bin/probe"], work)
                case.update(relocated_exit=code, relocated_output=output)
                if variant == "after":
                    require(runpaths == ["$ORIGIN/../lib"] and not rpaths,
                            "Corrected module did not emit the exact relative RUNPATH")
                    require(code == 0 and output == EXPECTED_OUTPUT,
                            "Corrected relocated binary failed")
                    (installed / "lib").rename(installed / "lib-withheld")
                    try:
                        missing_code, missing_output = command([installed / "bin/probe"], work)
                        case.update(missing_library_exit=missing_code, missing_library_output=missing_output)
                        require(missing_code != 0 and SONAME in missing_output,
                                "Missing-library control did not fail on the marker dependency")
                    finally:
                        (installed / "lib-withheld").rename(installed / "lib")
                    code, output = command([installed / "bin/probe"], work)
                    require(code == 0 and output == EXPECTED_OUTPUT,
                            "Restoring the adjacent library did not restore startup")
                    case["restored_library_exit"] = code
                elif variant == "opt-out":
                    require(not runpaths and not rpaths, "RPATH opt-out was not preserved")
                    require(code != 0 and SONAME in output, "Opt-out lookup control was masked")
                elif generator == "Unix Makefiles":
                    # Non-reproduction is useful evidence. Do not abort the
                    # corrected case or its controls just because the source
                    # spellings produced equivalent linker arguments here.
                    if runpaths != ["$ORIGIN/../lib"] and code != 0 and SONAME in output:
                        case["baseline_disposition"] = "old Makefiles lookup failure observed"
                    else:
                        case["baseline_disposition"] = "original failure not reproduced"
                        case["status"] = "BASELINE_UNCONFIRMED"
                else:
                    # The report established old Makefiles, not old Ninja.
                    # A correct old Ninja result is a legitimate control.
                    if code == 0:
                        require(runpaths == ["$ORIGIN/../lib"] and not rpaths and output == EXPECTED_OUTPUT,
                                "Old Ninja success did not match the literal-path contract")
                        case["baseline_disposition"] = "old Ninja unaffected"
                    else:
                        require(SONAME in output, "Old Ninja failed for an unrelated dependency")
                        case["baseline_disposition"] = "old Ninja lookup failure also observed"
                if case["status"] == "INCOMPLETE":
                    case["status"] = "PASS"
        result["status"] = ("AFTER_PASS_BASELINE_UNCONFIRMED"
                            if any(c["status"] == "BASELINE_UNCONFIRMED" for c in result["cases"])
                            else "PASS")
    except Exception as error:
        result.update(status="FAIL_OR_SETUP_ERROR", failed_stage=stage,
                      error=type(error).__name__ + ": " + str(error))
    finally:
        result["elapsed_seconds"] = round(time.monotonic() - started, 3)
        (work / "RESULT.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"status": result["status"], "result": str(work / "RESULT.json")}))
    # Exit2 retains successful corrected controls without claiming matched
    # reproduction. It must not be silently counted as a whole-fixture pass.
    return {"PASS": 0, "AFTER_PASS_BASELINE_UNCONFIRMED": 2}.get(result["status"], 1)


if __name__ == "__main__":
    sys.exit(main())
