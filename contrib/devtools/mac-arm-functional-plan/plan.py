"""Restore the exact Mac ARM seed, configure the pinned tree, and inspect only."""
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

root = Path(os.environ["GITHUB_WORKSPACE"]).resolve()
source, build, reports = (root/name for name in ("product", "mac-config-build", "records"))
reports.mkdir()
head = "26d5d2ddb0a27827b5b603a004177582747c294c"
checkpoint = 14137836649
zip_digest = "f752e99c80ce2b4f0ae5256e41379e6196656a93a66ee44fb8a255e133ffc2ad"
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
    assert outer.stat().st_size == 310667645 and sha(outer) == zip_digest
    with zipfile.ZipFile(outer) as z:
        for name in ("checkpoint.tar.gz", "inventory.json", "receipt.json"):
            with z.open(name) as stream, (cache/name).open("wb") as dest:
                shutil.copyfileobj(stream, dest, 1024*1024)
    archive = cache/"checkpoint.tar.gz"
    receipt = json.loads((cache/"receipt.json").read_text())
    assert sha(archive) == receipt["sha256"] and archive.stat().st_size == receipt["bytes"]
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
    shutil.copy2(build/"CMakeCache.txt", reports/"producer-CMakeCache.txt")

def object_stamps():
    return {str(p.relative_to(build)): (p.stat().st_size, p.stat().st_mtime_ns)
            for p in build.rglob("*.o") if "CMakeScratch" not in p.parts and
            not any(part.startswith("CompilerId") for part in p.parts)}

def inspect():
    assert platform.machine() == "arm64" and shutil.disk_usage(root).free > 15*1024**3
    assert run("source", ["git","-C",source,"rev-parse","HEAD"]).strip() == head
    assert "Xcode 16.4" in run("xcode", ["xcodebuild","-version"])
    assert "Apple clang version 17.0.0" in run("clang", ["xcrun","clang++","--version"])
    assert run("sdk", ["xcrun","--sdk","macosx","--show-sdk-version"]).strip() == "15.5"
    run("metal-tool", ["xcrun","--find","metal"])
    run("metallib-tool", ["xcrun","--find","metallib"])
    restore()
    before = object_stamps()
    run("dependencies", ["brew","install","--force-bottle","boost@1.85","libevent","zeromq",
                         "libomp","qt","qrencode","librsvg","libicns","python@3.12","ninja","cmake"], 600)
    run("dependency-versions", ["brew","list","--versions"])
    ssl = Path(run("openssl-prefix", ["brew","--prefix","openssl@3"]).strip())
    assert sha(ssl/"lib/libssl.a") == "b1a96521d10e2ce59ece360814915ed33c0e65aa60f7a9844b8b94c5d048cc56", "OpenSSL libssl differs"
    assert sha(ssl/"lib/libcrypto.a") == "76304e70825b4522b15461ad29c9106db1eeb8d421a12a641c210dabb11ed375", "OpenSSL libcrypto differs"
    python = Path(run("python-prefix", ["brew","--prefix","python@3.12"]).strip())/"bin/python3.12"
    run("venv", [python,"-m","venv",root/"test-env"])
    test_python = root/"test-env/bin/python"
    run("cryptography", [test_python,"-m","pip","install","--only-binary=:all:","cryptography==46.0.4"], 180)
    env.update(BTX_OPENSSL=str(ssl/"bin/openssl"), PATH=str(root/"test-env/bin")+":"+str(ssl/"bin")+":"+env["PATH"])
    run("configure", ["cmake","-S",source,"-B",build,"-DCMAKE_SUPPRESS_REGENERATION=ON",
                      f"-DPython3_EXECUTABLE={test_python}"], 250)
    shutil.copy2(build/"CMakeCache.txt", reports/"CMakeCache.txt")
    shutil.copy2(build/"test/config.ini", reports/"test-config.ini")
    current = (build/"CMakeCache.txt").read_text()
    assert all(f"{option}:BOOL=ON" in current for option in
               ("BUILD_GUI","BUILD_TESTS","WITH_MODELNET","WITH_ZMQ","ENABLE_WALLET","WITH_SQLITE","BTX_ENABLE_METAL"))
    state["configure_complete"] = True
    targets = ["btxd","btx-cli","btx-qt","btx-util","btx-tx","btx-wallet","btx-modeld","btx-hcpd",
               "btx-hosted","btx-open","btx-capability","btx-capabilityd","btx-modelcheck",
               "btx-matmul-backend-info","btx-security","btx-guardd","btx-native-qualify"]
    state["functional_profile_targets"] = targets
    state["plans"] = {}
    for label, want in (("functional-dry-run", targets), ("all-dry-run", ["all"])):
        plan = run(label, ["ninja","-C",build,"-n","-d","explain",*want], 160)
        assert "Re-running CMake" not in plan
        rows = [m.group(1) for line in plan.splitlines() if (m := re.match(r"^\[\d+/\d+\] (.*)$", line))]
        assert rows or "no work to do" in plan
        groups = Counter("compile" if r.startswith("Building ") else "link" if r.startswith("Linking ") else "other" for r in rows)
        state["plans"][label] = dict(edges=len(rows), kinds=dict(groups))
    assert object_stamps() == before, "Restored target objects changed during configure-only job"
    state.update(status="PASS_CONFIGURE_ONLY", btx_objects_unchanged=True)

try:
    inspect()
except Exception as error:
    state.update(status="BLOCKED_OR_FAILED", error=str(error))
    (reports/"exception.txt").write_text(traceback.format_exc())
finally:
    (reports/"result.json").write_text(json.dumps(state, indent=2)+"\n")
sys.exit(0 if state["status"] == "PASS_CONFIGURE_ONLY" else 1)
