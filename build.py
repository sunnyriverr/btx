"""Bounded #498 checkpoint + exact #499 product delta. Never dispatches CI."""
from pathlib import Path
import hashlib, json, os, re, shutil, subprocess, tarfile, threading, urllib.request

BASE = "dac9aee53520bd49ed320ec7a49b9072fc7d88d9"
AUTHOR = "57c98fa3fab36ddb3f792364714f8577fa3e50ee"
PATCH498 = "c786d666dd70021b48dd7e3f7941c2779db8d3ba38668564c864ab8e6ded06e4"
ARCHIVE = "28e76817f2d40dfb54ee078682bcae8b537f12a0b9eb2ca3bbb83911176e91aa"
QT498 = "1f5316436856bdc05c57e4593a7936ea59a3c3ab1d86560493026cfe91b0dc28"
ENCRYPT = "8a3e0b187bd94a5b068b939284060a64ec2437ea470f844c3d605acbe10d6927"
DELTA = "src/wallet/rpc/encrypt.cpp"
w = Path(os.environ["GITHUB_WORKSPACE"]).resolve()
out = w / "build-records"
out.mkdir(exist_ok=False)
state = dict(phase="restore", accepted_base=BASE, patch498_sha256=PATCH498,
             author499=AUTHOR, product_delta=[DELTA], normal_qt_unlock_changed=False)

def sha(p):
    h = hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda: f.read(1024 * 1024), b""): h.update(b)
    return h.hexdigest()

def run(args, label, limit=60, cwd=None):
    # Reader runs separately so timeout still applies to a quiet/stuck compiler.
    with (out / (label + ".log")).open("wb") as log:
        p = subprocess.Popen(list(map(str, args)), cwd=cwd, stdout=subprocess.PIPE,
                             stderr=subprocess.STDOUT, start_new_session=True)
        def drain():
            for line in iter(p.stdout.readline, b""):
                log.write(line); log.flush()
                print(line.decode(errors="replace"), end="", flush=True)
        reader = threading.Thread(target=drain, daemon=True); reader.start()
        try: code = p.wait(timeout=limit)
        except subprocess.TimeoutExpired:
            import signal
            os.killpg(p.pid, signal.SIGKILL); p.wait(); reader.join()
            raise
        reader.join()
        if code: raise subprocess.CalledProcessError(code, args)
    return (out / (label + ".log")).read_text()

def restore(manifest):
    roots = ("product", "gui-pilot-runtime/qtbuild", "gui-pilot-runtime/openssl")
    rows = manifest["rows"]
    actual = set()
    for root in roots:
        p = w / root
        for item in [p, *p.rglob("*")]:
            rel = str(item.relative_to(w))
            if ".git" not in item.relative_to(w).parts: actual.add(rel)
    assert actual == set(rows), "Unexpected checkpoint members"
    for name, row in rows.items():
        p = w / name
        assert not Path(name).is_absolute() and ".." not in Path(name).parts
        if row["kind"] == "file": assert p.is_file() and not p.is_symlink() and sha(p) == row["sha256"], name
        elif row["kind"] == "directory": assert p.is_dir() and not p.is_symlink(), name
        elif row["kind"] == "link":
            assert p.is_symlink() and os.readlink(p) == row["target"], name
            assert any(p.resolve().is_relative_to((w / r).resolve()) for r in roots), name
        else: raise AssertionError(name)
    for name, row in sorted(rows.items(), key=lambda x: len(Path(x[0]).parts), reverse=True):
        p = w / name
        if row["kind"] != "link": os.chmod(p, row["mode"])
        os.utime(p, ns=(row["mtime_ns"], row["mtime_ns"]), follow_symlinks=False)
        st = p.lstat()
        assert st.st_mtime_ns == row["mtime_ns"] and st.st_mode & 0o777 == row["mode"], name

try:
    manifest = json.loads((w / "saved-checkpoint/manifest.json").read_text())
    assert sha(w / "prior-build/result.json") == "7f138048ba44ccec56fda2d900881c1211f2f5cb5bc5c6e45530e4b697b82049"
    prior = json.loads((w / "prior-build/result.json").read_text())
    archive = w / "saved-checkpoint/build-state.tar.gz"
    assert prior["phase"] == "built" and prior["source"] == BASE
    assert prior["patch_sha256"] == manifest["identity"]["patch_sha256"] == PATCH498
    assert sha(archive) == manifest["archive_sha256"] == prior["successor_checkpoint_sha256"] == ARCHIVE
    assert prior["candidate_qt"] == QT498 and Path(manifest["workspace"]) == w
    assert not (w / "product").exists() and not (w / "gui-pilot-runtime").exists()
    total = sum(r.get("bytes", 0) for r in manifest["rows"].values())
    assert shutil.disk_usage(w).free > total + 3 * 1024**3, "Restore headroom"
    with tarfile.open(archive) as tar: tar.extractall(w, filter="data")
    restore(manifest)
    source = w / "product"; build = w / "gui-pilot-runtime/qtbuild"
    assert sha(w / "files498.json") == "3c496a92e482dacf359a2c9bc627c56a3478ff5236dcae6827f0fb059c121f86"
    files498 = json.loads((w / "files498.json").read_text())
    assert len(files498) == 10
    assert sha(w / "patch498.patch") == PATCH498
    assert run(["git", "rev-parse", "HEAD"], "accepted-head", cwd=w/"accepted-source").strip() == BASE
    run(["git", "apply", "--check", w/"patch498.patch"], "patch498-check", cwd=w/"accepted-source")
    run(["git", "apply", w/"patch498.patch"], "patch498-apply", cwd=w/"accepted-source")
    names = set(run(["git", "ls-files"], "accepted-files", cwd=w/"accepted-source").splitlines()) | set(files498)
    for name in names:
        expected = w / "accepted-source" / name
        if expected.is_file(): assert sha(source/name) == sha(expected), name
    actual_source = {str(p.relative_to(source)): sha(p) for p in source.rglob("*") if p.is_file() and not p.is_symlink()}
    expected_source = {n: sha(w/"accepted-source"/n) for n in names if (w/"accepted-source"/n).is_file()}
    differences = {"extra": sorted(set(actual_source)-set(expected_source)), "missing": sorted(set(expected_source)-set(actual_source)), "changed": sorted(n for n in set(actual_source)&set(expected_source) if actual_source[n]!=expected_source[n])}
    (out/"source-differences.json").write_text(json.dumps(differences,indent=2)+"\n")
    (out/"source-before.json").write_text(json.dumps(actual_source,sort_keys=True,indent=2)+"\n")
    print("Source differences:", json.dumps(differences), flush=True)
    assert actual_source == expected_source, "Full source tree differs from base plus #498"
    assert all(actual_source[n] == h for n,h in files498.items())
    (out/"source-before.json").write_text(json.dumps(actual_source, sort_keys=True, indent=2)+"\n")
    for n,h in {"btx-qt": QT498, "btxd": prior["baseline_binaries"]["btxd"], "btx-cli": prior["baseline_binaries"]["btx-cli"]}.items():
        assert sha(build/"bin"/n) == h, n
    originals = w/"original-binaries"; originals.mkdir()
    for n in ("btx-qt", "btxd", "btx-cli"): shutil.copy2(build/"bin"/n, originals/n)
    assert run(["g++", "-dumpfullversion"], "compiler").strip() == "11.4.0"
    assert "OpenSSL 3.5.9" in run([w/"gui-pilot-runtime/openssl/bin/openssl", "version"], "openssl")
    cache = build/"CMakeCache.txt"
    state["profile"] = {"cache_sha256":sha(cache), "build_ninja_sha256":sha(build/"build.ninja"), "rules_sha256":sha(build/"CMakeFiles/rules.ninja")}
    run(["cmake", "--version"], "cmake")
    run(["ninja", "--version"], "ninja")
    content = urllib.request.urlopen(f"https://raw.githubusercontent.com/btxchain/btx/{AUTHOR}/{DELTA}", timeout=30).read()
    assert hashlib.sha256(content).hexdigest() == ENCRYPT
    (out/"encrypt499.cpp").write_bytes(content)
    assert sha(source/DELTA) == "8126c60307774a91c0a7d907e3752c42fc17e784554f8fe55f32b32e37f052ec"
    before = (source/DELTA).read_text()
    after = content.decode()
    insertion = """        // The mempool pass at wallet load ran while the wallet was locked and
        // the shielded keys were not loaded, so it found no note of an
        // unconfirmed transaction. Now that they are, go over the mempool
        // again, as postInitProcess does at load.
        if (shielded_state_rehydrated) {
            pwallet->chain().requestMempoolTransactions(*pwallet);
        }
"""
    assert after.count(insertion) == 1 and after.replace(insertion, "", 1) == before
    (source/DELTA).write_bytes(content); (source/DELTA).touch()
    after_source = dict(actual_source); after_source[DELTA] = ENCRYPT
    assert {str(p.relative_to(source)):sha(p) for p in source.rglob("*") if p.is_file() and not p.is_symlink()} == after_source
    (out/"source-after.json").write_text(json.dumps(after_source, sort_keys=True, indent=2)+"\n")
    run(["cmake", "-P", build/"CMakeFiles/VerifyGlobs.cmake"], "verify-globs", cwd=build)
    observed = out/"observed.ninja"; shutil.copy2(build/"build.ninja", observed)
    plan = run(["ninja", "-C", build, "-f", observed, "-n", "btx-qt", "btxd"], "build-plan")
    actions = [re.sub(r"^\[\d+/\d+\] ", "", s) for s in plan.splitlines() if s.startswith("[")]
    allowed = {
        "Generating bitcoin-build-info.h",
        "Building CXX object src/wallet/CMakeFiles/bitcoin_wallet.dir/rpc/encrypt.cpp.o",
        "Building CXX object src/CMakeFiles/bitcoin_clientversion.dir/clientversion.cpp.o",
        "Building CXX object src/CMakeFiles/bitcoin_common.dir/matmul/matmul_v4_rc_production_canary.cpp.o",
        "Linking CXX static library lib/libbitcoin_wallet.a",
        "Linking CXX static library lib/libbitcoin_clientversion.a",
        "Linking CXX static library lib/libbitcoin_common.a",
        "Linking CXX executable bin/btx-qt", "Linking CXX executable bin/btxd",
    }
    assert 3 <= len(actions) <= 9 and len(actions) == len(set(actions)), actions
    assert set(actions) <= allowed, actions
    assert allowed.intersection(actions) and any("rpc/encrypt.cpp.o" in s for s in actions)
    assert all("Linking CXX executable bin/"+n in actions for n in ("btx-qt", "btxd"))
    state.update(phase="compile", planned_actions=actions, original_binaries={n:sha(originals/n) for n in ("btx-qt","btxd","btx-cli")})
    assert shutil.disk_usage(w).free > 2 * 1024**3
    # Exactly one serial compile invocation; no retry/reconfigure/broad fallback.
    run(["ninja", "-C", build, "-f", observed, "-j1", "btx-qt", "btxd"], "compile", limit=600)
    assert sha(cache) == state["profile"]["cache_sha256"]
    assert sha(build/"build.ninja") == state["profile"]["build_ninja_sha256"]
    assert sha(build/"bin/btx-cli") == sha(originals/"btx-cli")
    binaries = w/"compiled-binaries"; binaries.mkdir()
    for n in ("btx-qt", "btxd", "btx-cli"): shutil.copy2(build/"bin"/n, binaries/n)
    state["candidate_binaries"] = {n:sha(binaries/n) for n in ("btx-qt", "btxd", "btx-cli")}
    assert all(state["candidate_binaries"][n] != state["original_binaries"][n] for n in ("btx-qt", "btxd"))
    state.update(phase="built", checkpoint_sha256=ARCHIVE, encrypt499_sha256=ENCRYPT,
                 source_before_manifest_sha256=sha(out/"source-before.json"), source_after_manifest_sha256=sha(out/"source-after.json"))
except Exception as exc:
    state["error"] = repr(exc)
    raise
finally:
    (out/"result.json").write_text(json.dumps(state, indent=2)+"\n")
