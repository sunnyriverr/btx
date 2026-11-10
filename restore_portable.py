"""Restore an exact, branch-independent checkpoint inside the disposable runner."""
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import subprocess
import urllib.request

import checkpoint

workspace = Path(os.environ["GITHUB_WORKSPACE"])
contract = json.loads((workspace / "portable-input.json").read_text())
records = workspace / "pr467-records"
source_root = Path("D:/btx-native-035")
download = workspace / "portable-input"
payload = download / contract["payload"]
assert payload.resolve().is_relative_to(download.resolve())
assert payload.is_file() and checkpoint.digest(payload) == contract["payload_sha256"]
assert not source_root.exists(), "Expected a fresh disposable runner"
assert shutil.disk_usage(source_root.parent).free >= 8 * 1024**3

tar = Path(os.environ["SystemRoot"]) / "System32/tar.exe"
members = subprocess.check_output([str(tar), "-tf", str(payload)], timeout=75, text=True).splitlines()
allowed = {"project-build", "vcpkg-installed", "openssl-3.5.4-static", "vcpkg"}
top_levels = set()
for line in members:
    path = PurePosixPath(line.replace("\\", "/"))
    if str(path) == ".":
        continue
    assert not path.is_absolute() and ".." not in path.parts and ":" not in line
    assert path.parts[0] in allowed, f"Unexpected archive member {path.parts[0]}"
    top_levels.add(path.parts[0])
assert {"project-build", "vcpkg-installed"} <= top_levels
source_root.mkdir()
subprocess.run([str(tar), "-xf", str(payload), "-C", str(source_root)], check=True, timeout=180)
# The pinned toolchain file is a dependency of the saved Ninja graph.
# Its presence must not trigger a reconfigure; the job refuses that path.
toolchain = source_root / "vcpkg/scripts/buildsystems/vcpkg.cmake"
pinned = workspace / "vcpkg.cmake"
assert checkpoint.digest(pinned) == "f911a8769d07e10b26ce651f3cef6f52f2d5e598e3504d7f19e70bcbd3b3b25b"
if toolchain.exists():
    assert checkpoint.digest(toolchain) == checkpoint.digest(pinned)
else:
    toolchain.parent.mkdir(parents=True)
    shutil.copyfile(pinned, toolchain)
    manifest_time = (source_root / "project-build/build.ninja").stat().st_mtime_ns
    os.utime(toolchain, ns=(manifest_time - 1_000_000_000, manifest_time - 1_000_000_000))
# The preserved Ninja link rule runs vcpkg's applocal command.
# Reuse the exact official executable from the retained native profile.
vcpkg = source_root / "vcpkg/vcpkg.exe"
vcpkg_sha = "191ee64b0887af80aad3eff6c5e888ab733d3ef2182885ed4747b4574c201834"
if not vcpkg.exists():
    req = urllib.request.Request(
        "https://api.github.com/repos/microsoft/vcpkg-tool/releases/assets/690264732",
        headers={"Accept":"application/octet-stream", "User-Agent":"btx-pinned-native-tool",
                 "X-GitHub-Api-Version":"2022-11-28"},
    )
    with urllib.request.urlopen(req, timeout=60) as response:
        content = response.read(8 * 1024**2)
    assert len(content) == 6836024 and hashlib.sha256(content).hexdigest() == vcpkg_sha
    vcpkg.write_bytes(content)
assert checkpoint.digest(vcpkg) == vcpkg_sha
for name, digest in {
    "include/openssl/opensslv.h": "df513ae26e8baebbc641ba19f3d16f3e9ac0895cb092c81a39e1669f7fcb9c5c",
    "lib/libssl.lib": "860ce6dd4edf55af8a82a958afb9bae9cd025f3ef7e263bcc266d79cdd5179e8",
    "lib/libcrypto.lib": "f9385fc262485a1c779aa9a740ee3bde3025b9eb61b113e311024c9571899e12",
}.items():
    assert checkpoint.digest(source_root / "openssl-3.5.4-static" / name) == digest, name
marker = source_root / "project-build/btx-checkpoint.json"
assert checkpoint.digest(marker) == "2482100da1abb82abda529df0223f815ee8f498fd8cfb470f0803f865db4bdec"
(records / "restore-portable.json").write_text(json.dumps(
    {"artifact": contract["artifact"], "run": contract["run"], "payload_sha256": contract["payload_sha256"],
     "vcpkg_sha256": vcpkg_sha, "archive_members": len(members), "top_levels": sorted(top_levels), "marker_sha256": checkpoint.digest(marker)},
    indent=2) + "\n")
