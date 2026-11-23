"""Compare the diagnostic output of the packaged and patched ModelNet tools."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile

CASES = {
    "btx-hcpd": ("-version", "--help", "-help"),
    "btx-capabilityd": ("-version", "--version", "--help", "-help", "-h", "--unknown-version-test"),
    "btx-capability": ("-version", "--version", "--help", "-help", "-h", "help"),
}
STALE = "0.34.8-dev"


def capture(directory):
    records = {}
    with tempfile.TemporaryDirectory(prefix="btx-version-check-") as tmp:
        for name, flags in {**CASES, "btx-modeld": ("-version",)}.items():
            for flag in flags:
                call = subprocess.run([str(directory / name), flag], cwd=tmp, capture_output=True,
                                      text=True, timeout=8)
                records[f"{name} {flag}"] = {"exit": call.returncode, "stdout": call.stdout,
                                             "stderr": call.stderr}
    return records


def version(records):
    control = records["btx-modeld -version"]
    assert control["exit"] == 0
    first = control["stdout"].splitlines()[0]
    assert first.startswith("btx-modeld v0.34.17"), first
    return first.removeprefix("btx-modeld ")


def compare(stock, candidate):
    installed, generated = version(stock), version(candidate)
    assert installed == generated, (installed, generated)
    compared = []
    for name, flags in CASES.items():
        for flag in flags:
            key = f"{name} {flag}"
            before, after = stock[key], candidate[key]
            expected_exit = 1 if flag == "--unknown-version-test" else 0
            assert before["exit"] == after["exit"] == expected_exit, (key, before, after)
            text = before["stdout"] + before["stderr"]
            assert text.count(STALE) == 1 and generated not in text, (key, text)
            for stream in ("stdout", "stderr"):
                assert after[stream] == before[stream].replace(STALE, generated), (key, stream, after)
            compared.append(key)
    assert "HCP/1+CR11+CR12" in candidate["btx-hcpd -version"]["stdout"]
    return {"stock_mismatches": len(compared), "candidate_passes": len(compared),
            "reference_version": generated, "commands": compared}


if __name__ == "__main__":
    if sys.argv[1] == "capture":
        records = capture(Path(sys.argv[2]).resolve())
        Path(sys.argv[3]).write_text(json.dumps(records, indent=2) + "\n")
        version(records)
    else:
        assert sys.argv[1] == "compare"
        print(json.dumps(compare(*(json.loads(Path(p).read_text()) for p in sys.argv[2:])), indent=2))
