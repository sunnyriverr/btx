"""Bounded component regression, not root-project/native-node qualification."""
from pathlib import Path
import argparse
import base64
import hashlib
import json
import os
import platform
import shutil
import subprocess

BASE = "ab1b5cbe42d5b3ceb4faafff213292efed2bba18"
HEADER = "src/compat/mingw/posix_extra.h"
HERE = Path(__file__).resolve().parent


def sha(data):
    return hashlib.sha256(data).hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    manifest = json.loads((HERE / "closure.json").read_text())
    assert manifest["base"] == BASE
    for path, expected in manifest["files"].items():
        data = subprocess.check_output(["git", "-C", str(args.repo), "show", BASE + ":" + path])
        assert sha(data) == expected, path
        target = args.out / "closure" / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    original = subprocess.check_output(["git", "-C", str(args.repo), "show", BASE + ":" + HEADER])
    candidate = (args.repo / HEADER).read_bytes()
    assert sha(original) == manifest["baseline_header"]
    assert sha(candidate) == manifest["candidate_header"]
    for name, data in [("baseline", original), ("candidate", candidate)]:
        target = args.out / name / HEADER
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    cpp = args.repo / "test" / "util" / "windows_posix_header_tests.cpp"
    is_win = os.name == "nt"
    result = {"base": BASE, "platform": platform.platform(), "native_windows": is_win,
              "runner_sha256": sha(Path(__file__).read_bytes()),
              "test_sha256": sha(cpp.read_bytes()), "candidate_header": sha(candidate),
              "profile": "standalone component / native compiler; not CMake root flags",
              "toolchain": {k: os.environ.get(k) for k in ["WindowsSDKVersion", "WindowsSdkDir", "VCToolsVersion", "UCRTVersion", "VSCMD_ARG_TGT_ARCH"]},
              "commands": [], "preprocess": [], "errors": []}

    def run(label, command, expected=None):
        r = subprocess.run([str(x) for x in command], cwd=args.out,
                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=120)
        data = r.stdout
        (args.out / (label + ".log")).write_bytes(data)
        row = {"label": label, "command": [str(x) for x in command],
               "exit": r.returncode, "log_sha256": sha(data), "expected": expected}
        result["commands"].append(row)
        if expected is not None and (r.returncode == 0) != expected:
            result["errors"].append(label + ": unexpected exit " + str(r.returncode))
        print(label, "exit", r.returncode, "expected", expected, flush=True)
        if r.returncode and expected is not False:
            print(data.decode(errors="replace")[-6000:], flush=True)
        return r, data

    if is_win:
        compilers = ["cl", "clang-cl"]
    else:
        compilers = ["x86_64-w64-mingw32-g++"]
    for compiler in compilers:
        if shutil.which(compiler) is None:
            raise RuntimeError("Missing required compiler: " + compiler)
        run(compiler + "-version", [compiler] + (["/Bv"] if compiler == "cl" else ["--version"]))
        for core_first in [False, True]:
            order = "core-first" if core_first else "header-first"
            preprocess = {}
            for version in ["baseline", "candidate"]:
                label = compiler + "-" + order + "-" + version
                inc = args.out / version / "src"
                closure = args.out / "closure" / "src"
                exe = args.out / (label + ".exe")
                if is_win:
                    flags = ["/nologo", "/std:c++20", "/EHsc", "/W4", "/MD", "/DWIN32",
                             "/D_WIN32_WINNT=0x0A00", "/DWIN32_LEAN_AND_MEAN", "/DNOMINMAX",
                             "/D_CRT_SECURE_NO_WARNINGS", "/I" + str(inc), "/I" + str(closure)]
                    if core_first:
                        flags.append("/DBTX_CORE_FIRST")
                    command = [compiler, *flags, cpp, "/Fe:" + str(exe),
                               "/Fo:" + str(args.out / (label + ".obj")), "/link", "ws2_32.lib"]
                    expected = version == "candidate"
                else:
                    flags = ["-std=c++20", "-DWIN32", "-D_WIN32_WINNT=0x0A00",
                             "-DWIN32_LEAN_AND_MEAN", "-DNOMINMAX", "-I" + str(inc), "-I" + str(closure)]
                    if core_first:
                        flags.append("-DBTX_CORE_FIRST")
                    command = [compiler, *flags, cpp, "-o", exe, "-lws2_32"]
                    expected = True
                r, data = run(label + "-compile", command, expected)
                if is_win and version == "baseline" and b"unistd.h" not in data:
                    result["errors"].append(label + ": baseline did not identify unistd.h")
                if is_win and version == "candidate" and r.returncode == 0:
                    run(label + "-runtime", [exe, args.out / (label + ".tmp")], True)
                if not is_win:
                    r, data = run(label + "-preprocess", [compiler, *flags, "-E", "-P", cpp], True)
                    preprocess[version] = data
                # Compile the unchanged production types TU through the full forced header.
                obj = args.out / (label + "-types.obj")
                source = args.out / "closure" / "src" / "modelnet" / "types.cpp"
                if is_win:
                    force = ["-include", str(inc / "compat" / "mingw" / "posix_extra.h")] if compiler == "clang-cl" else ["/FI" + str(inc / "compat" / "mingw" / "posix_extra.h")]
                    run(label + "-types", [compiler, *flags, *force, "/c", source,
                                          "/Fo:" + str(obj)], expected)
                else:
                    run(label + "-types", [compiler, *flags, "-include", inc / "compat" / "mingw" / "posix_extra.h",
                                          "-c", source, "-o", obj], True)
            if not is_win:
                same = preprocess["baseline"] == preprocess["candidate"]
                result["preprocess"].append({"order": order, "identical": same,
                                             "baseline_sha256": sha(preprocess["baseline"]),
                                             "candidate_sha256": sha(preprocess["candidate"])})
                if not same:
                    result["errors"].append(order + ": MinGW preprocessed tokens differ")
    result["status"] = "PASS" if not result["errors"] else "FAIL"
    data = (json.dumps(result, indent=2) + "\n").encode()
    (args.out / "result.json").write_bytes(data)
    print("BTX_RESULT_BEGIN")
    print(base64.b64encode(data).decode())
    print("BTX_RESULT_END")
    raise SystemExit(0 if not result["errors"] else 1)


if __name__ == "__main__":
    main()
