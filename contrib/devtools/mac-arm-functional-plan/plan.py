"""Restore the exact Mac ARM seed, inspect the pinned tree without configuring."""
from collections import Counter
from pathlib import Path
import hashlib
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import tarfile
import traceback
import urllib.request
import zipfile

from object_audit import snapshot, write_audit

root = Path(os.environ["GITHUB_WORKSPACE"]).resolve()
source, build, reports = (root/name for name in ("product", "mac-config-build", "records"))
reports.mkdir()
head = "63c0475d4a8b11e80f727688c5c6d203a0ab938f"
checkpoint = 14703680085
zip_digest = "bd1d38d3248fda0307f4a3010e4fb62726b1ae60317fe9b327958415c26f1a1d"
state = dict(source=head, checkpoint=checkpoint, archive_sha256=zip_digest,
             image=os.environ.get("ImageVersion"), btx_compiled=False, tests_run=False,
             status="INCOMPLETE")
env = dict(os.environ, NINJA_STATUS="[%f/%t] ")

def sha(path):
    with Path(path).open("rb") as f:
        return hashlib.file_digest(f, "sha256").hexdigest()

def run(label, args, timeout=120):
    print(label, flush=True)
    path = reports/(label+".log")
    with path.open("wb") as log:
        subprocess.run(list(map(str, args)), cwd=root, env=env, stdout=log,
                       stderr=subprocess.STDOUT, check=True, timeout=timeout)
    return path.read_text(errors="replace")

def restore():
    cache = root/"producer-restore"
    cache.mkdir()
    outer = cache/"checkpoint.zip"
    request = urllib.request.Request(
        f"https://api.github.com/repos/sunnyriverr/btx/actions/artifacts/{checkpoint}/zip",
        headers={"User-Agent": "BTX-Mac-checkpoint"})
    request.add_unredirected_header("Authorization", "Bearer "+os.environ["GH_TOKEN"])
    try:
        with urllib.request.urlopen(request, timeout=75) as response, outer.open("wb") as dest:
            shutil.copyfileobj(response, dest, 1024*1024)
    except Exception:
        raise RuntimeError("Artifact transfer failed") from None
    assert outer.stat().st_size == 284018992 and sha(outer) == zip_digest
    with zipfile.ZipFile(outer) as z:
        for name in ("checkpoint.tar.gz", "inventory.json", "receipt.json"):
            with z.open(name) as stream, (cache/name).open("wb") as dest:
                shutil.copyfileobj(stream, dest, 1024*1024)
    archive = cache/"checkpoint.tar.gz"
    receipt = json.loads((cache/"receipt.json").read_text())
    assert sha(archive) == receipt["sha256"] == "2e73aa10042715b9f9399527e5a9c852146492075efb7de108dbd9a17fc1602c"
    assert archive.stat().st_size == receipt["bytes"] == 278893505
    inventory = json.loads((cache/"inventory.json").read_text())
    restored = set()
    assert not build.exists()
    with tarfile.open(archive) as tar:
        for member in tar:
            rel = Path(member.name)
            if not rel.parts or rel.parts[0] != build.name:
                continue
            assert not rel.is_absolute() and ".." not in rel.parts and member.name not in restored
            dest = root/rel
            assert dest.parent.resolve().is_relative_to(root)
            meta = inventory[member.name]
            restored.add(member.name)
            if member.isdir():
                assert meta["type"] == "dir"
                dest.mkdir(parents=True, exist_ok=True)
                continue
            dest.parent.mkdir(parents=True, exist_ok=True)
            if member.issym():
                assert meta["type"] == "symlink" and member.linkname == meta["target"]
                target = (dest.parent/member.linkname).resolve()
                assert target.is_relative_to(root) and ".git" not in target.relative_to(root).parts
                dest.symlink_to(member.linkname)
                continue
            assert member.isfile() and meta["type"] == "file" and not dest.is_symlink()
            with tar.extractfile(member) as src, dest.open("xb") as out:
                shutil.copyfileobj(src, out, 1024*1024)
            assert sha(dest) == meta["sha256"]
            dest.chmod(meta["mode"])
            os.utime(dest, ns=(meta["mtime_ns"], meta["mtime_ns"]))
    assert restored == {name for name in inventory if name.startswith(build.name+"/")}
    matched = 0
    for name, meta in inventory.items():
        if name.startswith("product/") and meta["type"] == "file":
            item = root/name
            if item.is_file() and not item.is_symlink() and sha(item) == meta["sha256"]:
                os.utime(item, ns=(meta["mtime_ns"], meta["mtime_ns"]))
                matched += 1
    state.update(restore_verified=True, restored_members=len(restored), restored_objects=sum(
        name.endswith(".o") for name in restored), preserved_source_mtimes=matched,
        checkpoint_payload_sha256=receipt["sha256"])
    producer_cache = (build/"CMakeCache.txt").read_text()
    assert f"CMAKE_HOME_DIRECTORY:INTERNAL={source}" in producer_cache
    assert f"CMAKE_CACHEFILE_DIR:INTERNAL={build}" in producer_cache
    shutil.copy2(build/"CMakeCache.txt", reports/"producer-CMakeCache.txt")


def inspect():
    assert platform.machine() == "arm64" and shutil.disk_usage(root).free > 15*1024**3
    assert run("source", ["git","-C",source,"rev-parse","HEAD"]).strip() == head
    changed = run("source-delta", ["git", "-C", source, "diff", "--name-only", "2c4da891f0089ebc0fb082e65d03a4efda4488a3", head]).splitlines()
    assert changed == ["src/test/mempool_tests.cpp", "src/txmempool.cpp", "src/wallet/rpc/backup.cpp",
                       "src/wallet/test/pq_wallet_tests.cpp"], changed
    state["source_delta"] = changed
    assert "Xcode 16.4" in run("xcode", ["xcodebuild","-version"])
    assert "Apple clang version 17.0.0" in run("clang", ["xcrun","clang++","--version"])
    assert run("sdk", ["xcrun","--sdk","macosx","--show-sdk-version"]).strip() == "15.5"
    run("metal-tool", ["xcrun","--find","metal"])
    run("metallib-tool", ["xcrun","--find","metallib"])
    restore()
    restored_objects = snapshot(build)
    assert len(restored_objects) == 4227, len(restored_objects)
    state["object_audits"] = {}
    run("dependencies", ["brew","install","--force-bottle","boost@1.85","libevent","zeromq",
                         "libomp","qt","qrencode","librsvg","libicns","python@3.12","ninja","cmake"], 600)
    run("dependency-versions", ["brew","list","--versions"])
    ssl = Path(run("openssl-prefix", ["brew","--prefix","openssl@3"]).strip())
    assert sha(ssl/"lib/libssl.a") == "b1a96521d10e2ce59ece360814915ed33c0e65aa60f7a9844b8b94c5d048cc56", "OpenSSL libssl differs"
    assert sha(ssl/"lib/libcrypto.a") == "76304e70825b4522b15461ad29c9106db1eeb8d421a12a641c210dabb11ed375", "OpenSSL libcrypto differs"
    python = Path(run("python-prefix", ["brew","--prefix","python@3.12"]).strip())/"bin/python3.12"
    run("venv", [python,"-m","venv",root/"test-env"])
    test_python = root/"test-env/bin/python"
    cache = (build/"CMakeCache.txt").read_text()
    assert any(f"CMAKE_SUPPRESS_REGENERATION:{kind}=ON" in cache for kind in ("BOOL", "UNINITIALIZED"))
    binaries = [build/"bin"/name for name in ("btxd", "btx-cli")]
    prior = {path.name: sha(path) for path in binaries}
    targets = ["btxd", "btx-cli"]
    state.update(functional_profile_targets=targets, configure_invoked=False)
    state["plans"] = {}
    try:
        plan = run("wallet-dry-run", ["ninja", "-C", build, "-n", "-d", "explain", *targets], 160)
        assert "Re-running CMake" not in plan
        rows = [m.group(1) for line in plan.splitlines() if (m := re.match(r"^\[\d+/\d+\] (.*)$", line))]
        assert rows or "no work to do" in plan
        groups = Counter("compile" if row.startswith("Building ") else
                         "link" if row.startswith("Linking ") else "other" for row in rows)
        sdk_reasons = sum("ninja explain:" in line and "MacOSX" in line and ".sdk/" in line
                          for line in plan.splitlines())
        state["plans"]["wallet-dry-run"] = dict(
            edges=len(rows), kinds=dict(groups), sdk_explanation_lines=sdk_reasons)
        (reports/"planned-actions.txt").write_text("\n".join(rows) + "\n")
    finally:
        final_objects = snapshot(build)
        state["object_audits"]["restore_to_dry_run"] = write_audit(
            reports/"objects-restore-to-dry-run.json", restored_objects, final_objects)
    dry = state["object_audits"]["restore_to_dry_run"]
    assert not (dry["product_or_unclassified"] or dry["configuration_probes"]), (
        "Object inventory changed during Ninja dry run; see object audit")
    assert {path.name: sha(path) for path in binaries} == prior
    state.update(status="PASS_DRY_RUN", btx_objects_unchanged=True, dry_run_objects_unchanged=True,
                 binary_hashes_unchanged=True)

try:
    inspect()
except Exception as error:
    state.update(status="BLOCKED_OR_FAILED", error=str(error))
    (reports/"exception.txt").write_text(traceback.format_exc())
finally:
    (reports/"result.json").write_text(json.dumps(state, indent=2)+"\n")
sys.exit(0 if state["status"] == "PASS_DRY_RUN" else 1)
