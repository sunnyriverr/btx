#!/usr/bin/env python3
"""One bounded qualification batch; no retries, BTX runtime or wallets."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
import time


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture", type=Path, required=True)
    parser.add_argument("--work", type=Path, required=True)
    parser.add_argument("--modern-cmake", type=Path, required=True)
    args = parser.parse_args()
    if args.work.exists():
        parser.error("Refuse existing work; preserve prior attempts")
    args.work.mkdir(parents=True)
    profiles = [
        ("gcc-minimum", "/usr/bin/cmake", "3.22", "/usr/bin/g++-11", True),
        ("clang-minimum", "/usr/bin/cmake", "3.22", "/usr/bin/clang++-14", False),
        ("gcc-modern", str(args.modern_cmake), "4.3", "/usr/bin/g++-11", False),
    ]
    summary = {"status": "INCOMPLETE", "profiles": [],
               "scope": "inert direct-library producer checks only"}
    started = time.monotonic()
    try:
        for name, cmake, series, compiler, ninja in profiles:
            argv = [sys.executable, str(args.fixture / "run.py"),
                    "--work", str(args.work / name), "--cmake", cmake,
                    "--cmake-series", series, "--cxx", compiler]
            if ninja:
                argv.append("--ninja")
            entry = {"name": name, "argv": argv, "status": "INCOMPLETE"}
            summary["profiles"].append(entry)
            # A failed profile is retained; the other distinct profiles run
            # once each. The workflow imposes one outer360s batch boundary.
            with (args.work / (name + "-controller.log")).open("w") as output:
                code = subprocess.call(argv, stdout=output, stderr=subprocess.STDOUT)
            entry["returncode"] = code
            result_path = args.work / name / "RESULT.json"
            if not result_path.is_file():
                entry["status"] = "MISSING_RESULT"
                continue
            result = json.loads(result_path.read_text())
            entry["result_status"] = result.get("status")
            expected = {(g, v) for g in (["Unix Makefiles", "Ninja"] if ninja else ["Unix Makefiles"])
                        for v in ["before", "after", "opt-out"]}
            cases = result.get("cases", [])
            observed = [(c.get("generator"), c.get("variant")) for c in cases]
            complete = len(observed) == len(expected) and set(observed) == expected
            all_cases_pass = all(c.get("status") == "PASS" for c in cases)
            controls_complete = all(
                c.get("missing_library_exit", 0) != 0 and c.get("restored_library_exit") == 0
                for c in cases if c.get("variant") == "after")
            # The native controller enforces exact RUNPATH, marker SONAME,
            # actual relocated startup/output, and the opt-out failure.
            entry["complete_case_selection"] = complete
            entry["positive_controls_complete"] = controls_complete
            entry["status"] = ("PASS" if code == 0 and result.get("status") == "PASS"
                               and complete and all_cases_pass and controls_complete
                               else "FAIL_OR_UNCONFIRMED")
        summary["status"] = ("PASS" if len(summary["profiles"]) == 3
                             and all(p["status"] == "PASS" for p in summary["profiles"])
                             else "FAIL_OR_UNCONFIRMED")
    except Exception as error:
        summary.update(status="SETUP_OR_COLLECTION_ERROR",
                       error=type(error).__name__ + ": " + str(error))
    finally:
        summary["elapsed_seconds"] = round(time.monotonic() - started, 3)
        (args.work / "SUMMARY.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps({"status": summary["status"], "path": str(args.work / "SUMMARY.json")}))
    return 0 if summary["status"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
