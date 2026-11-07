"""Scoped RPC-help comparison prototype; no RPC dispatch or conversion emulation.

Expectations must be independently source-backed. A passing selected binding
does not establish completeness of the command or of the RPC inventory.
"""

from dataclasses import dataclass
import math
from typing import Any, Dict, Iterable, List, Mapping, Tuple, Union


@dataclass(frozen=True)
class Probe:
    method: str
    form: str
    selector: Union[int, str]
    raw: str
    expected: Mapping[str, Any]
    destination: str
    mode: str

    @property
    def key(self) -> Tuple[str, str, Union[int, str], str]:
        return self.method, self.form, self.selector, self.raw


@dataclass(frozen=True)
class Finding:
    kind: str
    binding: str
    detail: str


def same_json(left: Any, right: Any) -> bool:
    """Do not let Python's True == 1 erase a JSON type disagreement."""
    if type(left) is not type(right):
        return False
    if isinstance(left, dict):
        return left.keys() == right.keys() and all(
            same_json(left[key], right[key]) for key in left)
    if isinstance(left, list):
        return len(left) == len(right) and all(
            same_json(a, b) for a, b in zip(left, right))
    return left == right


def record_error(record: Any) -> str:
    if not isinstance(record, dict):
        return "Record is not an object"
    if set(record) == {"error"}:
        return "" if isinstance(record["error"], str) and record["error"] else "Invalid error text"
    if set(record) != {"value", "type"}:
        return "Success record must contain exactly value and type"
    kind = record["type"]
    if type(kind) is not int or kind not in range(6):
        return "Unknown UniValue type"
    value = record["value"]
    valid = {0: value is None, 1: type(value) is dict, 2: type(value) is list,
             3: type(value) is str, 4: type(value) in (int, float), 5: type(value) is bool}[kind]
    if not valid or (kind == 4 and isinstance(value, float) and not math.isfinite(value)):
        return "Value does not match UniValue type"
    return ""


def compare(probes: Iterable[Probe], observations: Mapping[Tuple, Dict]) -> List[Finding]:
    """Compare actual converter observations; keep every mismatching binding."""
    findings = []
    seen = set()
    for probe in probes:
        binding = f"{probe.method}/{probe.form}/{probe.selector}->{probe.destination}"
        invalid = record_error(probe.expected)
        if invalid:
            findings.append(Finding("invalid_contract", binding, invalid))
            continue
        if probe.form not in ("named", "positional") or probe.mode not in (
                "literal", "json", "json_or_string", "object_or_string"):
            findings.append(Finding("invalid_contract", binding, "Unknown form or mode"))
            continue
        if probe.key in seen:
            findings.append(Finding("invalid_contract", binding, "Duplicate probe key"))
            continue
        seen.add(probe.key)
        actual = observations.get(probe.key)
        if probe.key not in observations:
            findings.append(Finding("unresolved", binding, f"No observation for {probe.raw!r}"))
        elif record_error(actual):
            findings.append(Finding("invalid_observation", binding, record_error(actual)))
        elif not same_json(dict(probe.expected), actual):
            findings.append(Finding(
                "conversion_mismatch", binding,
                f"raw={probe.raw!r}; expected={dict(probe.expected)!r}; actual={actual!r}"))
    return findings


def metadata_findings(method: str, declared_count: int, schema: str,
                      conversion_rows: Iterable[Tuple[str, int, str]]) -> List[Finding]:
    """Only zero-argument completeness and opaque schemas are in this prototype."""
    if schema == "opaque" and declared_count > 0:
        return [Finding("unresolved", method, "Declared arguments lack a complete semantic contract")]
    if schema != "zero_arguments" or declared_count != 0:
        return [Finding("invalid_contract", method, "No complete metadata rule for this declaration")]
    return [Finding("unexpected_conversion", method, f"Zero-argument command has row {row!r}")
            for row in conversion_rows if row[0] == method]


def require_agreement(findings: Iterable[Finding]) -> None:
    findings = list(findings)
    if findings:
        raise AssertionError("\n".join(
            f"{finding.kind}: {finding.binding}: {finding.detail}" for finding in findings))
