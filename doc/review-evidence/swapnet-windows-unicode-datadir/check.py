"""Exercise the pinned node-to-shared-runtime filesystem boundary."""
import contextlib
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

PIN = "c2e71aafc48a41593277e335c8bc370e45599f01"
ROOT = Path.cwd()
CONTROL = Path(__file__).resolve().parent
SOURCE = ROOT / "source"
RECORDS = ROOT / "records"
RECORDS.mkdir(exist_ok=True)
WINDOWS = os.name == "nt"
NODE = "src/swapnet/node.cpp"
STATES = {"ascii": "data-ascii/regtest/shared-p2p",
          "unicode": "data-\u00fc-\U0001f3c3/regtest/shared-p2p"}
RESULT = {"base": PIN, "platform": sys.platform, "cases": {}, "status": "INCOMPLETE"}

def save_receipt():
    (RECORDS / "result.json").write_text(json.dumps(RESULT, indent=2) + "\n", encoding="utf-8")

def git(*args):
    return subprocess.check_output(["git", "-C", str(SOURCE), *args], timeout=20)

def execute(command, log, env, cwd):
    output = RECORDS / log
    with output.open("wb") as file:
        subprocess.run(command, cwd=cwd, env=env, stdout=file, stderr=subprocess.STDOUT,
                       timeout=100, check=True)
    return output.read_text(errors="replace").strip()

def compiler_environment():
    if not WINDOWS:
        return os.environ.copy(), shutil.which("clang++")
    locator = Path(os.environ["ProgramFiles(x86)"]) / "Microsoft Visual Studio/Installer/vswhere.exe"
    installs = json.loads(subprocess.check_output([str(locator), "-products", "*", "-all", "-format", "json"], timeout=20))
    vs = next(Path(item["installationPath"]) for item in installs
              if item["installationVersion"].startswith("17.") and
              (Path(item["installationPath"]) / "VC/Tools/MSVC/14.44.35207/bin/Hostx64/x64/cl.exe").is_file())
    dev = vs / "Common7/Tools/VsDevCmd.bat"
    output = subprocess.check_output(f'call "{dev}" -arch=x64 -host_arch=x64 -vcvars_ver=14.44.35207 -winsdk=10.0.26100.0 >nul && set',
                                     shell=True, text=True, timeout=30)
    env = os.environ.copy()
    env.update((k.upper(), v) for k, v in (line.split("=", 1) for line in output.splitlines()
               if "=" in line and not line.startswith("=")))
    cl = shutil.which("cl.exe", path=env["PATH"])
    assert cl and Path(cl).resolve().samefile(vs / "VC/Tools/MSVC/14.44.35207/bin/Hostx64/x64/cl.exe")
    banner = subprocess.run([cl], env=env, capture_output=True, text=True, timeout=10)
    (RECORDS / "compiler.log").write_text(banner.stdout + banner.stderr)
    assert "19.44.35230 for x64" in banner.stdout + banner.stderr
    RESULT.update(compiler="MSVC 19.44.35230 x64", sdk=env["WINDOWSSDKVERSION"].rstrip(chr(92)))
    assert RESULT["sdk"] == "10.0.26100.0"
    return env, cl

def compile_fixture(label, work, env, compiler):
    calls = [line.strip() for line in (SOURCE / NODE).read_text(encoding="utf-8").splitlines()
             if "btx::p2p::StartRuntime(" in line]
    assert len(calls) == 1 and calls[0].endswith("GetRandHash().GetHex());")
    RESULT.setdefault("node_calls", {})[label] = calls[0]
    call = calls[0].replace("GetRandHash().GetHex()", "token")
    fixture = work / f"{label}.cpp"
    template = (CONTROL / "path-fixture.cpp").read_text(encoding="utf-8")
    assert template.count("NODE_START_RUNTIME_CALL") == 1
    fixture.write_text(template.replace("NODE_START_RUNTIME_CALL", call), encoding="utf-8")
    exe = work / (label + (".exe" if WINDOWS else ""))
    if WINDOWS:
        cmd = [compiler, "/nologo", "/std:c++20", "/EHsc", "/utf-8", "/DWIN32", "/DNOMINMAX",
               f"/I{SOURCE/'src'}", str(fixture), f"/Fe:{exe}"]
    else:
        cmd = [compiler,"-std=c++20","-pthread", "-I", str(SOURCE/"src"), str(fixture), "-o", str(exe)]
    execute(cmd, f"{label}-build.log", env, work)
    return exe

def cases(label, exe, work, env):
    profile = execute([str(exe), "profile"], f"{label}-profile.log", env, work)
    if WINDOWS:
        assert profile.startswith("ansi_code_page="), profile
        cp = int(profile.split("=")[1])
        assert cp != 65001, "Windows process uses UTF-8 ACP and cannot discriminate the stock failure"
        RESULT["ansi_code_page"] = cp
    for path_case, expected in STATES.items():
        name = f"{label}-{path_case}"
        with tempfile.TemporaryDirectory(prefix="bwp-") as folder:
            scratch = Path(folder)
            execute([str(exe), "write", path_case], f"{name}-write.log", env, scratch)
            catalog_before = sorted((file.relative_to(scratch).as_posix(), hashlib.sha256(file.read_bytes()).hexdigest())
                                    for file in scratch.rglob("swapnet.catalog"))
            execute([str(exe), "reopen", path_case], f"{name}-reopen.log", env, scratch)
            actual = sorted(file.relative_to(scratch).as_posix() for file in scratch.rglob("shared-p2p") if file.is_dir())
            catalog_after = sorted((file.relative_to(scratch).as_posix(), hashlib.sha256(file.read_bytes()).hexdigest())
                                   for file in scratch.rglob("swapnet.catalog"))
            assert len(actual) == len(catalog_before) == 1
            assert catalog_before == catalog_after and catalog_before[0][0] == actual[0] + "/swapnet.catalog"
            RESULT["cases"][name] = {
                "configured_path": expected, "created_paths": actual, "path_matches": actual == [expected],
                "catalog_sha256": catalog_after[0][1], "catalog_reopened_unchanged": True,
            }
            save_receipt()
    assert RESULT["cases"][f"{label}-ascii"]["path_matches"], "ASCII control diverged"
    assert RESULT["cases"][f"{label}-unicode"]["path_matches"] == (label == "candidate" or not WINDOWS), (
        "Expected wrong Unicode directory for stock on Windows and correct path for the other cases"
    )

def main():
    assert git("rev-parse", "HEAD").decode().strip() == PIN
    assert not git("status", "--porcelain", "--untracked-files=no")
    pins = json.loads((CONTROL / "source-pins.json").read_text())
    for path, expected in pins.items():
        assert hashlib.sha256(git("show", f"HEAD:{path}")).hexdigest() == expected
    env, compiler = compiler_environment()
    assert compiler
    patch = subprocess.check_output(["git", "-C", str(CONTROL), "show", "HEAD:candidate.patch"], timeout=10)
    RESULT["patch_sha256"] = hashlib.sha256(patch).hexdigest()
    with tempfile.TemporaryDirectory(prefix="bwp-build-") as folder:
        work = Path(folder)
        cases("stock", compile_fixture("stock", work, env, compiler), work, env)
        command = ["git", "-C", str(SOURCE), "apply", "--cached"]
        subprocess.run([*command, "--check", "-"], check=True, input=patch, timeout=10)
        subprocess.run([*command, "-"], check=True, input=patch, timeout=10)
        assert set(git("diff", "--cached", "--name-only").decode().splitlines()) == set(pins)
        git("checkout-index", "-f", "--", *sorted(pins))
        assert not git("diff", "--name-only")
        RESULT["candidate_file_sha256"] = {
            path: hashlib.sha256(git("show", f":{path}")).hexdigest() for path in pins
        }
        cases("candidate", compile_fixture("candidate", work, env, compiler), work, env)
        assert len({case["catalog_sha256"] for case in RESULT["cases"].values()}) == 1, "Catalog bytes changed"
    RESULT["status"] = "PASS_WINDOWS_BEFORE_AFTER" if WINDOWS else "PASS_POSIX_CONTROLS"

try:
    main()
except Exception as error:
    RESULT.update(error=str(error), status="FAILED")
    raise
finally:
    save_receipt()
    print(json.dumps(RESULT, indent=2))
