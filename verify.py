"""Compare the two native MSVC fixtures with pinned arbitrary-precision expectations."""
from collections import Counter
import hashlib
from itertools import zip_longest
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import traceback

HERE = Path(__file__).resolve().parent
RECORDS = HERE.parent / "records"
RELEASE = "c2e71aafc48a41593277e335c8bc370e45599f01"
WORD = (1 << 64) - 1
MASK = (1 << 128) - 1
SIGNED_MIN = -(1 << 127)
# These are JPP's explicit FullWidthSamples edges, in source order.
PAIRS = (
    (0, 0), (0, 1), (0, 2), (WORD, WORD), (0, WORD), (1, 0), (1, 1),
    (1 << 63, 0), (1 << 63, 1), ((1 << 63) - 1, WORD), (WORD, 0),
    (0, 1 << 63), (0xffffffff, 0xffffffff00000000),
)
PINS = {
    "src/compat/wide128.h": "b9fae42faea352f2d813e76b38bc528d02f3c473460b53f894b5a2566eae1bd5",
    "src/test/wide128_tests.cpp": "e30e7a92913839edacaa3eaae87f6f76d4ffce945011e59e4d54e87139ea9709",
    "candidate-cost-fixture.cpp": "ab527518e22fc386ef6b5a457e34125083ab5d0e054a477c6b827c1cb27aa530",
    "macos-expected-cost.txt": "c95f7b37658fbdfa21f8a5a2d04551032a84a904a0a46059273a01ac2e386d8a",
}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def signed(value):
    return value - (1 << 128) if value & (1 << 127) else value


def truncate_div(a, b):
    magnitude = abs(a) // abs(b)
    return -magnitude if (a < 0) != (b < 0) else magnitude


def oracle():
    edges = [(hi << 64) | lo for hi, lo in PAIRS]
    for i, a in enumerate(edges):
        sa = signed(a)
        unary = (
            ("u_narrow64", a & WORD), ("u_narrow32", a & 0xffffffff),
            ("i_roundtrip", sa), ("i_narrow64", sa & WORD), ("i_narrow_u64", sa & WORD),
            ("i_neg", -sa),
        )
        for op, value in unary:
            yield op, value & MASK, (i,)
        for shift in range(128):
            shifts = (
                ("u_left", a << shift), ("u_right", a >> shift),
                ("i_left", sa << shift), ("i_right", sa >> shift),
            )
            for op, value in shifts:
                yield op, value & MASK, (i, shift)
        for j, b in enumerate(edges):
            sb = signed(b)
            arithmetic = (
                ("u_add", a + b), ("u_sub", a - b), ("u_mul", a * b),
                ("u_and", a & b), ("u_or", a | b), ("u_xor", a ^ b),
                ("u_eq", a == b), ("u_lt", a < b), ("u_le", a <= b),
                ("u_gt", a > b), ("u_ge", a >= b),
                ("i_add", sa + sb), ("i_sub", sa - sb), ("i_mul", sa * sb),
                ("i_and", sa & sb), ("i_or", sa | sb),
                ("i_eq", sa == sb), ("i_lt", sa < sb), ("i_le", sa <= sb), ("i_ge", sa >= sb),
            )
            for op, value in arithmetic:
                yield op, value & MASK, (i, j)
            if b:
                yield "u_div", a // b, (i, j)
                yield "u_mod", a % b, (i, j)
            if sb and (sa, sb) != (SIGNED_MIN, -1):
                q = truncate_div(sa, sb)
                yield "i_div", q & MASK, (i, j)
                yield "i_mod", (sa - q * sb) & MASK, (i, j)


def compare_edges(data):
    counts = Counter()
    for index, (actual, expected) in enumerate(zip_longest(data.splitlines(), oracle()), 1):
        assert actual is not None and expected is not None, f"Fixture output count mismatch at line {index}"
        operation, hi, lo = actual.split()
        actual_word = (int(hi, 16) << 64) + int(lo, 16)
        expected_op, expected_word, coordinates = expected
        assert (operation, actual_word) == (expected_op, expected_word), (
            f"{index} {expected_op}, indexes {coordinates}: expected {expected_word:032x}, "
            f"got {operation} {actual_word:032x}"
        )
        counts[operation] += 1
    return dict(counts)


def verify_cost(data):
    ref = (HERE / "macos-expected-cost.txt").read_text(encoding="ascii")
    assert data == ref
    return {"named_cases": len(data.splitlines()) - 1, "extra_boundary_assertions": 4,
            "matches_retained_macos_portable_output": True}


def git_bytes(source, path):
    return subprocess.check_output(["git", "-C", str(source), "show", f"HEAD:{path}"], timeout=20)


def compiler_profile():
    vswhere = Path(os.environ["ProgramFiles(x86)"]) / "Microsoft Visual Studio/Installer/vswhere.exe"
    choices = json.loads(subprocess.check_output(
        [str(vswhere), "-all", "-products", "*", "-requires",
         "Microsoft.VisualStudio.Component.VC.Tools.x86.x64", "-format", "json"], timeout=20))
    toolset = "14.44.35207"
    sdk = "10.0.26100.0"
    relative = Path("VC/Tools/MSVC") / toolset / "bin/Hostx64/x64/cl.exe"
    installation = next(
        (Path(i["installationPath"]) for i in choices
         if i["installationVersion"].startswith("17.") and (Path(i["installationPath"]) / relative).is_file()),
        None,
    )
    assert installation is not None, "Missing exact retained MSVC 19.44 x64 toolset"
    dev = installation / "Common7/Tools/VsDevCmd.bat"
    settings = subprocess.check_output(
        f'call "{dev}" -arch=x64 -host_arch=x64 -vcvars_ver={toolset} -winsdk={sdk} >nul && set',
        shell=True, text=True, timeout=40)
    env = os.environ.copy()
    env.update(line.split("=", 1) for line in settings.splitlines() if "=" in line and not line.startswith("="))
    env = {key.upper(): value for key, value in env.items()}
    cl = Path(shutil.which("cl.exe", path=env["PATH"])).resolve()
    banner = subprocess.run([str(cl)], env=env, capture_output=True, timeout=10)
    log = banner.stdout + banner.stderr
    (RECORDS / "compiler-version.txt").write_bytes(log)
    assert cl == (installation / relative).resolve() and b"19.44.35230" in log and b"x64" in log
    assert env["WINDOWSSDKVERSION"].rstrip(chr(92)) == sdk
    return cl, env, {"toolset": toolset, "compiler": "19.44.35230 x64", "sdk": sdk,
                     "cl_sha256": sha(cl.read_bytes())}


def build_fixture(cl, env, source, name, report):
    target = RECORDS / (name + ".exe")
    command = [str(cl), "/nologo", "/std:c++20", "/O2", "/EHsc", f"/I{source / 'src'}",
               f"/Fo{RECORDS / (name + '.obj')}", f"/Fe{target}", str(HERE / (name + ".cpp"))]
    result = subprocess.run(command, capture_output=True, cwd=RECORDS, env=env, timeout=60)
    (RECORDS / (name + "-build.txt")).write_bytes(result.stdout + result.stderr)
    result.check_returncode()
    report.setdefault("fixtures", {})[name] = {
        "sha256": sha(target.read_bytes()), "compile_exit": result.returncode,
        "source_sha256": sha((HERE / (name + ".cpp")).read_bytes().replace(b"\r\n", b"\n")),
    }
    (RECORDS / (name + ".obj")).unlink()
    return target


def run_fixture(binary, label, env, report, input_text=""):
    result = subprocess.run([str(binary)], input=input_text, encoding="ascii", capture_output=True,
                            cwd=RECORDS, env=env, timeout=20)
    (RECORDS / f"{label}-stdout.txt").write_text(result.stdout, encoding="ascii", newline="\n")
    (RECORDS / f"{label}-stderr.txt").write_text(result.stderr, encoding="ascii", newline="\n")
    report["fixtures"][label]["run_exit"] = result.returncode
    result.check_returncode()
    assert not result.stderr, result.stderr
    return result.stdout


def run(report):
    source = HERE.parent / "source"
    assert subprocess.check_output(["git", "-C", str(source), "rev-parse", "HEAD"], text=True).strip() == RELEASE
    for path, expected in PINS.items():
        if path.startswith("src/"):
            data = git_bytes(source, path)
            assert (source / path).read_bytes().replace(b"\r\n", b"\n") == data
        else:
            data = (HERE / path).read_bytes().replace(b"\r\n", b"\n")
        assert sha(data) == expected, path
    report["inputs_verified"] = PINS

    cl, env, report["profile"] = compiler_profile()
    edges = build_fixture(cl, env, source, "edge-check", report)
    costs = build_fixture(cl, env, source, "candidate-cost-fixture", report)
    words = "".join(f"{hi:x} {lo:x}\n" for hi, lo in PAIRS)
    (RECORDS / "edge-input.txt").write_text(words, encoding="ascii", newline="\n")
    actual = run_fixture(edges, "edge-check", env, report, words)
    counts = compare_edges(actual)
    report["edge_comparison"] = {"edge_operands": len(PAIRS), "shifts_per_operand": 128,
                                 "comparisons": sum(counts.values()), "by_operation": counts,
                                 "portable_unsigned_and_signed_alias_assertions": True}
    actual_costs = run_fixture(costs, "candidate-cost-fixture", env, report)
    report["cost_comparison"] = verify_cost(actual_costs)
    report["complete"] = True
    print(f"{sum(counts.values())} exact arithmetic results and nine saved cost cases matched")


if __name__ == "__main__":
    if sys.argv[1:] != ["run"]:
        sys.exit("Use run")
    RECORDS.mkdir(exist_ok=True)
    report = {"revision": RELEASE, "platform": platform.platform(), "image": os.getenv("ImageVersion"),
              "product_builds": 0, "complete": False}
    try:
        run(report)
    except Exception:
        (RECORDS / "exception.txt").write_text(traceback.format_exc(), encoding="utf-8")
        raise
    finally:
        (RECORDS / "result.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
