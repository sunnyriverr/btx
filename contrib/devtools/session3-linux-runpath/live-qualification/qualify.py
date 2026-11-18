#!/usr/bin/env python3
"""Qualify the maintained test through the real CTest registration, not a frozen module inside the test."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import os
import time

NAME = "util_install_binary_component_runpath_test"
PRODUCTION = ["cmake/module/InstallBinaryComponent.cmake", "cmake/tests.cmake",
              "test/util/install_binary_component_runpath_test.py"]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository", type=Path, required=True)
    parser.add_argument("--work", type=Path, required=True)
    parser.add_argument("--modern-cmake", type=Path, required=True)
    args = parser.parse_args()
    args.repository = args.repository.resolve()
    args.work = args.work.resolve()
    args.modern_cmake = args.modern_cmake.resolve()
    if args.work.exists():
        parser.error("Preserve existing qualification results")
    args.work.mkdir(parents=True)
    (args.work / "home").mkdir()
    env = {"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "LC_ALL": "C",
           "HOME": str(args.work / "home")}
    control = Path(__file__).resolve().parent
    summary = {"status": "INCOMPLETE", "contexts": [], "commands": []}
    started = time.monotonic()

    def run(argv, expected_success=True, limit=60):
        remaining = 330 - (time.monotonic() - started)
        if remaining <= 0:
            raise RuntimeError("Qualification command budget exhausted")
        entry = {"argv": [str(a) for a in argv]}
        summary["commands"].append(entry)
        proc = subprocess.Popen(entry["argv"], cwd=args.work, stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT, text=True, start_new_session=True, env=env)
        try:
            output, _ = proc.communicate(timeout=min(limit, remaining))
        except subprocess.TimeoutExpired:
            entry["timeout"] = True
            try:
                os.killpg(proc.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            output, _ = proc.communicate()
            log = "command-%03d.log" % len(summary["commands"])
            (args.work / log).write_text(output)
            entry.update(returncode=proc.returncode, log=log)
            raise
        log = "command-%03d.log" % len(summary["commands"])
        (args.work / log).write_text(output)
        entry.update(returncode=proc.returncode, log=log)
        if expected_success and proc.returncode:
            raise RuntimeError("Command failed; see " + log)
        return proc.returncode, output

    def require(condition, message):
        if not condition:
            raise RuntimeError(message)

    def configure(source, build, cmake, compiler, generator, enabled=True):
        run([cmake, "-S", control, "-B", build, "-G", generator,
             "-DCMAKE_CXX_COMPILER=" + compiler,
             "-DBTX_TEST_SOURCE_ROOT=" + str(source),
             "-DBTX_TEST_PYTHON=" + sys.executable,
             "-DBTX_TEST_BUILD_TESTS=" + ("ON" if enabled else "OFF")])
        ctest = str(Path(cmake).with_name("ctest"))
        _, output = run([ctest, "--test-dir", build, "--show-only=json-v1", "-R", "^" + NAME + "$"])
        tests = json.loads(output)["tests"]
        require(len(tests) == (1 if enabled else 0), "Wrong CTest registration selection")
        command = None
        if enabled:
            command = tests[0].get("command", [])
            require(tests[0]["name"] == NAME and str(source / PRODUCTION[2]) in command,
                    "Registration did not point to the real production test")
            for flag, value in [("--cmake", cmake), ("--compiler", compiler), ("--generator", generator)]:
                require(flag in command and command.index(flag) + 1 < len(command), "Missing forwarded " + flag)
                actual = command[command.index(flag) + 1]
                require(actual == value if flag == "--generator" else Path(actual).resolve() == Path(value).resolve(),
                        "Registration forwarded the wrong " + flag)
            properties = {p["name"]: p["value"] for p in tests[0]["properties"]}
            require(float(properties.get("TIMEOUT", 0)) == 120, "Missing bounded CTest timeout")
            require(int(properties.get("PROCESSORS", 1)) == 1, "Unexpected parallel allocation")
        return ctest, command

    try:
        manifest = json.loads((control / "INPUTS.json").read_text())
        for path, expected in manifest["files"].items():
            require(digest(args.repository / path) == expected, "Input hash mismatch: " + path)
        summary["input_hashes"] = manifest["files"]
        for cmake, series in [("/usr/bin/cmake", "3.22"), (str(args.modern_cmake), "4.3")]:
            _, version = run([cmake, "--version"])
            require(version.startswith("cmake version " + series + "."), "Wrong selected CMake series")
            _, version = run([str(Path(cmake).with_name("ctest")), "--version"])
            require(version.startswith("ctest version " + series + "."), "Wrong selected CTest series")
        sources = {}
        for variant in ["before", "after"]:
            root = args.work / "sources" / variant
            for path in PRODUCTION:
                dest = root / path
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(args.repository / path, dest)
            if variant == "before":
                shutil.copy2(control / "baseline.cmake", root / PRODUCTION[0])
            sources[variant] = root
        profiles = [("gcc-minimum-make", "/usr/bin/cmake", "/usr/bin/g++-11", "Unix Makefiles", True),
                    ("gcc-minimum-ninja", "/usr/bin/cmake", "/usr/bin/g++-11", "Ninja", True),
                    ("clang-minimum-ninja", "/usr/bin/cmake", "/usr/bin/clang++-14", "Ninja", True),
                    ("gcc-modern-ninja", str(args.modern_cmake), "/usr/bin/g++-11", "Ninja", False)]
        configure(sources["after"], args.work / "registration-disabled", profiles[0][1],
                  profiles[0][2], profiles[0][3], enabled=False)
        summary["disabled_registration_absent"] = True
        for name, cmake, compiler, generator, baseline_fails in profiles:
            for variant in ["before", "after"]:
                source = sources[variant]
                build = args.work / name / variant
                entry = {"profile": name, "variant": variant, "status": "INCOMPLETE"}
                summary["contexts"].append(entry)
                ctest, registered_command = configure(source, build, cmake, compiler, generator)
                entry["registered_command"] = registered_command
                code, _ = run([ctest, "--test-dir", build, "-R", "^" + NAME + "$",
                               "--no-tests=error", "--output-on-failure",
                               "--output-junit", str(build / "ctest.xml")],
                              expected_success=False, limit=150)
                reports = list((build / "test/util/runpath-regression").glob("run-*/SUMMARY.json"))
                require(len(reports) == 1, "Missing or duplicate maintained-test result")
                result = json.loads(reports[0].read_text())
                observations = json.loads((reports[0].parent / "OBSERVATIONS.json").read_text())
                inputs = observations["inputs"]
                require(Path(inputs["module"]) == source / PRODUCTION[0], "Test did not use its live module")
                require(inputs["module_sha256"] == digest(source / PRODUCTION[0])
                        and observations["module_after"] == inputs["module_sha256"], "Module changed or was misbound")
                require(inputs["test_sha256"] == digest(args.repository / PRODUCTION[2]), "Different test before/after")
                require(inputs["generator"] == generator
                        and Path(inputs["cmake"]).resolve() == Path(cmake).resolve()
                        and Path(inputs["compiler"]).resolve() == Path(compiler).resolve(),
                        "Maintained test did not use the configured tools/generator")
                require(result["tests_run"] == 2 and result["skipped"] == 0 and result["errors"] == 0
                        and result["scratch_removed"], "Test missing, skipped, setup failed or scratch remained")
                observed = {x["test"]: x for x in observations["observations"]}
                require(len(observed) == 2 and all(x["built"] for x in observed.values()), "Not both probes built")
                positive = observed["test_adjacent_library_after_relocation"]
                opt_out = observed["test_runtime_path_opt_out"]
                require(not opt_out["runpath"] and not opt_out["rpath"] and opt_out["relocated_exit"] != 0,
                        "Opt-out control did not qualify")
                expected_failure = variant == "before" and baseline_fails
                if expected_failure:
                    bad = "$$ORIGIN/../lib" if generator == "Unix Makefiles" else "$/../lib"
                    require(code != 0 and result["failures"] == 1 and not result["success"]
                            and positive["runpath"] == [bad] and positive["relocated_exit"] == 127,
                            "Baseline did not fail at the real runpath boundary")
                    entry["status"] = "EXPECTED_BASELINE_FAILURE"
                else:
                    require(code == 0 and result["success"] and result["failures"] == 0
                            and positive["runpath"] == ["$ORIGIN/../lib"] and positive["relocated_exit"] == 0
                            and positive["missing_library_exit"] != 0 and positive["restored_library_exit"] == 0,
                            "Live-module test or controls failed")
                    entry["status"] = "PASS"
                entry.update(ctest_exit=code, test_result=str(reports[0].relative_to(args.work)),
                             module_sha256=inputs["module_sha256"], result=result)
        require(len(summary["contexts"]) == 8, "Incomplete paired contexts")
        summary["status"] = "PASS"
    except Exception as error:
        summary.update(status="FAIL_OR_INCOMPLETE", error=type(error).__name__ + ": " + str(error))
    finally:
        summary["elapsed_seconds"] = round(time.monotonic() - started, 3)
        (args.work / "SUMMARY.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps({"status": summary["status"], "result": str(args.work / "SUMMARY.json")}))
    return 0 if summary["status"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
