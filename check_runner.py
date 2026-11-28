"""Qualify redirected test_runner.py diagnostics without starting a daemon."""

import argparse
import codecs
import csv
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import sys
import tempfile

RUNNER_HASH = "f74603b4c2d5ccb8e4c672746972ade80c221378d60af8448fc6669d86cf7a9b"
COMBINE_HASH = "106f240f609d66c42014360a6e6590fc3720cb1eb4d0c153618082f5414b7c4e"
CASE = "feature_config_args.py"

CHILD = """\
import argparse
from pathlib import Path
import sys

parser = argparse.ArgumentParser()
parser.add_argument("--tmpdir", type=Path, required=True)
args, _ = parser.parse_known_args()
if "--fixture-fail" in sys.argv:
    args.tmpdir.mkdir(parents=True)
    (args.tmpdir / "test_framework.log").write_text(
        "2026-11-28T01:00:00Z FIXTURE-FRAMEWORK-LOG\u0020caf\N{LATIN SMALL LETTER E WITH ACUTE} \N{BITCOIN SIGN} \N{RUNNER}\\n", encoding="utf-8"
    )
    debug_log = args.tmpdir / "node0" / "regtest" / "debug.log"
    debug_log.parent.mkdir(parents=True)
    debug_log.write_text("2026-11-28T01:00:01Z FIXTURE-NODE-LOG\\n", encoding="utf-8")
    print("FIXTURE-ORIGINAL-FAILURE-STDOUT")
    print("FIXTURE-ORIGINAL-FAILURE-STDERR", file=sys.stderr)
    sys.exit(17)
print("FIXTURE-CONTROL-PASS")
"""

PROBE = """\
import json, sys
print(json.dumps({
    'stdout': {'encoding': sys.stdout.encoding, 'errors': sys.stdout.errors, 'tty': sys.stdout.isatty()},
    'stderr': {'encoding': sys.stderr.encoding, 'errors': sys.stderr.errors, 'tty': sys.stderr.isatty()},
    'utf8_mode': sys.flags.utf8_mode,
}))
"""


def sha256(path):
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def execute(command, env):
    return subprocess.run([sys.executable, *command], env=env, capture_output=True, timeout=30)


def redirected_environment():
    env = os.environ.copy()
    for name in ("PYTHONUTF8", "PYTHONIOENCODING", "PYTHONLEGACYWINDOWSSTDIO"):
        env.pop(name, None)
    natural = json.loads(execute(["-c", PROBE], env).stdout)
    if any(codecs.lookup(natural[stream]["encoding"]).name != "cp1252" for stream in ("stdout", "stderr")):
        env.update(PYTHONUTF8="0", PYTHONIOENCODING="cp1252")
    actual = json.loads(execute(["-c", PROBE], env).stdout)
    assert not any(actual[stream]["tty"] for stream in ("stdout", "stderr")), actual
    assert all(codecs.lookup(actual[stream]["encoding"]).name == "cp1252" for stream in ("stdout", "stderr")), actual
    return env, {"natural": natural, "tested": actual, "injected": natural != actual}


def run_case(root, records, name, fail, utf8, env):
    runner = root / "test" / "functional" / "test_runner.py"
    config = root / "config.ini"
    temp = root / name
    temp.mkdir()
    csv_path = temp / "summary.csv"
    command = [
        str(runner), CASE, "--jobs=1", "--combinedlogslen=25",
        f"--configfile={config}", f"--tmpdirprefix={temp}", f"--resultsfile={csv_path}",
    ]
    if fail:
        command.append("--fixture-fail")
    if utf8:
        env = {**env, "PYTHONIOENCODING": "utf-8"}
    execution = execute(command, env)
    (records / f"{name}.stdout").write_bytes(execution.stdout)
    (records / f"{name}.stderr").write_bytes(execution.stderr)
    encoding = "utf-8" if utf8 else "cp1252"
    output = execution.stdout.decode(encoding)
    errors = execution.stderr.decode(encoding)
    summary = []
    if csv_path.is_file():
        shutil.copyfile(csv_path, records / f"{name}.csv")
        with csv_path.open(encoding="utf-8", newline="") as handle:
            summary = [row[:2] for row in csv.reader(handle) if row]
    fixture_logs = list(temp.glob("test_runner_*/*/test_framework.log"))
    if fixture_logs:
        assert len(fixture_logs) == 1
        shutil.copyfile(fixture_logs[0], records / f"{name}.fixture.log")
    return {
        "exit": execution.returncode,
        "unicode_fixture_path": any("\N{BITCOIN SIGN}_\N{RUNNER}" in str(path) for path in fixture_logs),
        "runner_encoding_traceback": "UnicodeEncodeError" in errors,
        "traceback_at_combined_heading": "Combined log for" in errors,
        "traceback_at_summary": "in print_results" in errors,
        "unexpected_output_errors": any(term in errors for term in ("Traceback (", "--- Logging error ---")),
        "failed_child_stdout": "FIXTURE-ORIGINAL-FAILURE-STDOUT" in output,
        "failed_child_stderr": "FIXTURE-ORIGINAL-FAILURE-STDERR" in output,
        "combined_heading": "Combined log for " in output,
        "combined_framework": "FIXTURE-FRAMEWORK-LOG" in output,
        "combined_node": "FIXTURE-NODE-LOG" in output,
        "accent_retained": "caf\N{LATIN SMALL LETTER E WITH ACUTE}" in output,
        "unicode_retained_or_escaped": (
            "\N{BITCOIN SIGN} \N{RUNNER}" if utf8 else r"\u20bf \U0001f3c3"
        ) in output,
        "summary_visible": bool(re.search(r"^ALL\s*\|.*\b" + ("Failed" if fail else "Passed") + r"\b", output, re.M)),
        "summary_csv": summary[1:],
    }


def prove_failure_intact(result):
    assert result["exit"] == 1 and not result["unexpected_output_errors"], result
    assert all(result[key] for key in (
        "unicode_fixture_path", "failed_child_stdout", "failed_child_stderr",
        "combined_heading", "combined_framework", "combined_node",
        "accent_retained", "unicode_retained_or_escaped", "summary_visible",
    )), result
    assert result["summary_csv"] == [[CASE, "Failed"], ["ALL", "Failed"]], result


def prove_passing_intact(result):
    assert result["exit"] == 0 and not result["unexpected_output_errors"], result
    assert result["summary_visible"], result
    assert result["summary_csv"] == [[CASE, "Passed"], ["ALL", "Passed"]], result
    assert not any(result[key] for key in ("combined_heading", "failed_child_stdout", "failed_child_stderr")), result


def qualify(args):
    source = args.source / "test" / "functional"
    assert sha256(source / "test_runner.py") == RUNNER_HASH
    assert sha256(source / "combine_logs.py") == COMBINE_HASH
    args.records.mkdir(parents=True, exist_ok=False)
    env, profile = redirected_environment()
    report = {
        "revision": "c2e71aafc48a41593277e335c8bc370e45599f01",
        "platform": platform.platform(),
        "python": platform.python_version(),
        "stream_profile": profile,
        "fixture": "Actual test runner and combine_logs.py, synthetic child and cache setup, no BTX binaries",
        "runner_sha256": {"stock": RUNNER_HASH},
        "controls": {},
    }

    try:
        with tempfile.TemporaryDirectory(prefix="btx-runner-output-") as sandbox:
            root = Path(sandbox)
            fixture = root / "test" / "functional"
            fixture.mkdir(parents=True)
            for filename in ("test_runner.py", "combine_logs.py"):
                (fixture / filename).write_bytes((source / filename).read_bytes().replace(b"\r\n", b"\n"))
            (fixture / CASE).write_text(CHILD, encoding="utf-8")
            (fixture / "create_cache.py").write_text("# Synthetic fixture starts no nodes.\n", encoding="utf-8")
            (root / "config.ini").write_text(
                f"[environment]\nSRCDIR={root.as_posix()}\nBUILDDIR={root.as_posix()}\n"
                "[components]\nENABLE_BITCOIND=true\n",
                encoding="utf-8",
            )
            controls = report["controls"]
            if not args.candidate_only:
                failing = controls["stock-legacy-fail"] = run_case(root, args.records, "stock-legacy-fail", True, False, env)
                passing = controls["stock-legacy-pass"] = run_case(root, args.records, "stock-legacy-pass", False, False, env)
                assert failing["exit"] == 1 and failing["runner_encoding_traceback"] and failing["traceback_at_combined_heading"], failing
                assert failing["unicode_fixture_path"] and failing["failed_child_stdout"] and failing["failed_child_stderr"], failing
                assert not failing["summary_csv"] and not failing["summary_visible"] and not failing["combined_framework"], failing
                if passing["runner_encoding_traceback"]:
                    assert passing["traceback_at_summary"] and not passing["summary_csv"], passing
                else:
                    prove_passing_intact(passing)
            if args.patch:
                lf_patch = root / "candidate.patch"
                lf_patch.write_bytes(args.patch.read_bytes().replace(b"\r\n", b"\n"))
                subprocess.run(
                    ["git", "-c", "core.autocrlf=false", "apply", str(lf_patch)],
                    cwd=root, check=True, timeout=15,
                )
                report["runner_sha256"]["candidate"] = sha256(fixture / "test_runner.py")
                for name, failed, utf8 in (
                    ("candidate-legacy-fail", True, False),
                    ("candidate-legacy-pass", False, False),
                    ("candidate-utf8-fail", True, True),
                ):
                    result = controls[name] = run_case(root, args.records, name, failed, utf8, env)
                    if failed:
                        prove_failure_intact(result)
                    else:
                        prove_passing_intact(result)
            report["qualified"] = bool(args.patch)
    finally:
        (args.records / "result.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--records", required=True, type=Path)
    parser.add_argument("--patch", type=Path)
    parser.add_argument("--candidate-only", action="store_true")
    args = parser.parse_args()
    if args.candidate_only and not args.patch:
        parser.error("--candidate-only requires --patch")
    qualify(args)
