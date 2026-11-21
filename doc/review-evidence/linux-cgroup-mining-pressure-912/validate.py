"""Check captured before/after governor observations without a rerun."""
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parent
raw = (ROOT / "observation.log").read_text()
expected_fixture = {
    "healthy": (524288, 6291456),
    "mismatch": (52428, 6291456),
    "container_ram": (524288, 6291456),
    "container_swap": (524288, 6291456),
    "zero_swap_limit": (52428, 6291456),
    "unlimited_swap_fallback": (52428, 6291456),
    "root_fallback_healthy": (524288, 6291456),
    "root_fallback_pressure": (52428, 6291456),
    "host_ram_pressure": (524288, 524288),
    "ancestor_ram": (524288, 6291456),
}
before_denied = {
    "mismatch", "zero_swap_limit", "unlimited_swap_fallback",
    "root_fallback_pressure", "host_ram_pressure",
}
after_denied = {
    "container_ram", "container_swap", "unlimited_swap_fallback",
    "root_fallback_pressure", "host_ram_pressure", "ancestor_ram",
}

runs = {}
cases = None
case = None
ancestor_use = None
for line in raw.splitlines():
    if line.startswith("binary=./"):
        name = line.removeprefix("binary=./")
        assert name not in runs
        cases = runs[name] = {}
        case = None
    elif line.startswith("ancestor_memory_current="):
        ancestor_use = int(line.split("=", 1)[1])
    elif match := re.fullmatch(
        r"case=(\w+) host_swap_free_kib=(\d+) host_ram_available_kib=(\d+)", line
    ):
        name, swap_free, available = match.groups()
        assert cases is not None and name not in cases
        actual = (int(swap_free), int(available))
        assert actual == expected_fixture[name], (name, actual)
        case = cases[name] = {"host_swap_free_kib": actual[0],
                              "host_ram_available_kib": actual[1], "counters": {}}
        if name == "ancestor_ram":
            case["ancestor_memory_current"] = ancestor_use
    elif line.startswith("0::"):
        assert case is not None
        case["cgroup"] = line[3:]
    elif line.startswith("memory."):
        key, value = line.split("=", 1)
        case["counters"][key] = value
    elif line.startswith("{"):
        assert case is not None and "result" not in case
        case["result"] = json.loads(line)
    elif line != "cleanup_complete":
        raise AssertionError(f"Unexpected observation: {line!r}")

assert list(runs) == ["before", "after"]
assert raw.splitlines()[-1] == "cleanup_complete"
for build, cases in runs.items():
    assert list(cases) == list(expected_fixture)
    denied = before_denied if build == "before" else after_denied
    for name, case in cases.items():
        outcome = case["result"]
        should_allow = name not in denied
        assert outcome["mining_allowed"] is should_allow, (build, name, outcome)
        expected_reason = "NONE" if should_allow else "GPU_MEMORY_PRESSURE"
        assert outcome["pause_reason"] == expected_reason, (build, name, outcome)
        group = case["cgroup"]
        if name.startswith("root_fallback"):
            assert group == "/" and not case["counters"]
            assert outcome["memory_available_bytes"] == 6442450944
        else:
            suffix = "/child" if name == "ancestor_ram" else ""
            assert group == "/btx-governor-912" + suffix
    for name in ("healthy", "mismatch"):
        counters = cases[name]["counters"]
        assert int(counters["memory.max"]) == 268435456
        assert 0 <= int(counters["memory.current"]) < int(counters["memory.max"]) // 4
        assert int(counters["memory.swap.max"]) == 67108864
        assert int(counters["memory.swap.current"]) == 0
    assert int(cases["container_ram"]["counters"]["memory.current"]) == 260046848
    assert int(cases["container_swap"]["counters"]["memory.swap.current"]) == 66060288
    assert cases["zero_swap_limit"]["counters"]["memory.swap.max"] == "0"
    assert cases["unlimited_swap_fallback"]["counters"]["memory.swap.max"] == "max"
    assert cases["ancestor_ram"]["ancestor_memory_current"] == 260046848
    assert cases["ancestor_ram"]["counters"]["memory.max"] == "max"
assert runs["before"]["mismatch"]["result"]["swap_pressure"] is True
assert runs["after"]["mismatch"]["result"]["swap_pressure"] is False
assert runs["after"]["container_swap"]["result"]["swap_pressure"] is True
assert runs["after"]["container_ram"]["result"]["memory_available_bytes"] == 8388608
assert runs["after"]["ancestor_ram"]["result"]["memory_available_bytes"] == 8388608

result = {
    "source": json.loads((ROOT / "inputs.json").read_text())["source"],
    "verdict": "same_mismatch_fails_before_passes_after",
    "candidate_patch_sha256": hashlib.sha256((ROOT / "fix.patch").read_bytes()).hexdigest(),
    "observation_sha256": hashlib.sha256(raw.encode()).hexdigest(),
    "qualified_cases_per_binary": len(expected_fixture),
    "runs": runs,
}
(ROOT / "result.json").write_text(json.dumps(result, indent=2) + "\n")
print(f"Verified {result['qualified_cases_per_binary']} observations per binary")
