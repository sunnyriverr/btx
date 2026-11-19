"""Verify and stage the exact retained binary, never execute it here."""
import hashlib
import io
import json
import os
from pathlib import Path
import struct
import urllib.parse
import urllib.request
import zipfile

w = Path(os.environ["GITHUB_WORKSPACE"])
receipt = json.loads((w / "proposal/helper-receipt.json").read_text())
record = {"complete": False}

class SafeRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, url):
        new = super().redirect_request(req, fp, code, msg, headers, url)
        if urllib.parse.urlsplit(req.full_url).netloc != urllib.parse.urlsplit(url).netloc:
            new.remove_header("Authorization")
        return new

def sha(data):
    return hashlib.sha256(data).hexdigest()

try:
    artifact = receipt["helper_artifact_id"]
    request = urllib.request.Request(
        f"https://api.github.com/repos/sunnyriverr/btx/actions/artifacts/{artifact}/zip",
        headers={"Authorization": "Bearer " + os.environ["GH_TOKEN"], "User-Agent": "btx-alias-artifact"})
    with urllib.request.build_opener(SafeRedirect()).open(request, timeout=45) as src:
        data = src.read(40 * 1024**2 + 1)
    assert len(data) <= 40 * 1024**2 and sha(data) == receipt["helper_archive_sha256"]
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        assert sorted(z.namelist()) == ["SHA256SUMS", "SOURCE", "btx-modeld"]
        assert z.read("SOURCE").decode().strip() == receipt["source"] == "c97c9a8d00ea37359b8691fd25c783725c1f4021"
        assert z.getinfo("btx-modeld").file_size == receipt["helper_size"]
        binary = z.read("btx-modeld")
        digest = sha(binary)
        assert digest == receipt["helper_sha256"]
        assert z.read("SHA256SUMS").decode().split() == [digest, "btx-modeld"]
        assert binary[:6] == b"\x7fELF\x02\x01" and struct.unpack_from("<H", binary, 18)[0] == 62
    path = w / "current-helper/btx-modeld"
    path.parent.mkdir()
    path.write_bytes(binary)
    path.chmod(0o755)
    record.update(complete=True, source=receipt["source"], helper_sha256=digest,
                  archive_sha256=sha(data), artifact=artifact)
finally:
    (w / "records/alias-helper.json").write_text(json.dumps(record, indent=2) + "\n")
