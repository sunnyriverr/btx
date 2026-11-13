"""Record native Windows attribute errors for disposable profile paths."""
import ctypes
from ctypes import wintypes
import json
import os
from pathlib import Path
import subprocess
import tempfile

get_attributes = ctypes.WinDLL("kernel32", use_last_error=True).GetFileAttributesW
get_attributes.argtypes = [wintypes.LPCWSTR]
get_attributes.restype = wintypes.DWORD
invalid = 0xFFFFFFFF
reparse = 0x400

def probe(path):
    ctypes.set_last_error(0)
    attributes = get_attributes(str(path))
    return {"attributes": attributes if attributes != invalid else None,
            "error": ctypes.get_last_error() if attributes == invalid else None,
            "reparse": attributes != invalid and bool(attributes & reparse)}

with tempfile.TemporaryDirectory(prefix="cport profile ") as scratch:
    root = Path(scratch)
    destination = root / "operator_profile.json"
    temp = root / "operator_profile.json.tmp"
    rows = {
        "missing_destination": probe(destination),
        "missing_temporary": probe(temp),
        "missing_parent": probe(root / "absent" / destination.name),
        "invalid_name": probe(root / "bad<name" / destination.name),
    }
    destination.write_bytes(b"fixture")
    rows["regular_destination"] = probe(destination)

    target = root / "junction-target"
    target.mkdir()
    subprocess.run(["cmd.exe", "/d", "/c", "mklink", "/J", str(temp), str(target)], check=True)
    try:
        rows["temporary_junction"] = probe(temp)
    finally:
        temp.rmdir()

    # Deny only reading attributes on a disposable file. Preserve the rights
    # needed by the owner to restore its DACL and remove the fixture.
    denied = root / "denied.json"
    denied.write_bytes(b"fixture")
    sid = subprocess.check_output(
        ["powershell.exe", "-NoProfile", "-Command",
         "[System.Security.Principal.WindowsIdentity]::GetCurrent().User.Value"],
        text=True).strip()
    subprocess.run(["icacls", str(denied), "/deny", f"*{sid}:(RA)"], check=True)
    try:
        rows["denied_file"] = probe(denied)
    finally:
        subprocess.run(["icacls", str(denied), "/remove:d", f"*{sid}"], check=True)
    rows["restored_file"] = probe(denied)

output = Path(os.environ["RUNNER_TEMP"]) / "profile-attributes.json"
output.write_text(json.dumps(rows, indent=2) + "\n", encoding="utf-8")
print(output.read_text())
assert rows["missing_destination"]["error"] == rows["missing_temporary"]["error"] == 2
assert rows["missing_parent"]["error"] == 3
assert rows["invalid_name"]["error"] not in (None, 2, 3)
assert rows["regular_destination"]["error"] is None and not rows["regular_destination"]["reparse"]
assert rows["temporary_junction"]["reparse"]
assert rows["denied_file"]["error"] == 5
assert rows["restored_file"]["error"] is None
