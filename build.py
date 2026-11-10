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
    # Track links by target as well as by content. is_file() follows links;
    # excluding only the restored side would falsely reject tracked PQ sources.
    source_links = {str(p.relative_to(source)):os.readlink(p) for p in source.rglob("*") if p.is_symlink()}
    expected_links = {n:os.readlink(w/"accepted-source"/n) for n in names if (w/"accepted-source"/n).is_symlink()}
    (out/"source-links.json").write_text(json.dumps({"actual":source_links,"expected":expected_links},indent=2)+"\n")
    assert source_links == expected_links, "Source symlink targets differ"
    # Retained functional-test Python bytecode is not a compiler input.
    # Delete only these observed, immutable-checkpoint-verified cache files;
    # every actual source and symlink remains covered by the exact tree guard.
    retained_bytecode = {'test/functional/test_framework/__pycache__/__init__.cpython-312.pyc': 'ac612df381cdb115141ae91dfa5b1949dd825196a4bd93117344b63e97a089d1', 'test/functional/test_framework/__pycache__/address.cpython-312.pyc': '8ce8b73b3c43010db034f0fad79768c938e89d534816b81ecbee89f41f9215b8', 'test/functional/test_framework/__pycache__/authproxy.cpython-312.pyc': '1a1bcc8318e3bca6ccbf9285e039bcfade9fb81e0bfc8b62497b0c826d356743', 'test/functional/test_framework/__pycache__/coverage.cpython-312.pyc': '1e32cbaf3ad528b394a40d1a6d565cca1295a792f3fa0cb2eb454a2e1e9d0498', 'test/functional/test_framework/__pycache__/descriptors.cpython-312.pyc': '15beb58486df9111bfcf795b39ed3d4fb2f307afe4daf70b89345678d405d7bc', 'test/functional/test_framework/__pycache__/key.cpython-312.pyc': 'a773797dd8478bd7e68ec19ddcb491e16be668710c06db08a93bc377e016fa9f', 'test/functional/test_framework/__pycache__/messages.cpython-312.pyc': 'fedeaea51d9c7d4ce6539e359cb8fdfc33b2d246f29868a3b976107e56c884ec', 'test/functional/test_framework/__pycache__/p2p.cpython-312.pyc': '13ae15e5880ab3675cbfa208e7a7d262057197cde76129b4f97256aaaa4ee087', 'test/functional/test_framework/__pycache__/script.cpython-312.pyc': '3b85475a6bd5257af69c72cf9188898521c2f0e9887c69872b263530089f538c', 'test/functional/test_framework/__pycache__/script_util.cpython-312.pyc': 'cdfb35640b3fff3ff18d0109bb76f16b4aabe8468b18fd0acef02a15b6593787', 'test/functional/test_framework/__pycache__/segwit_addr.cpython-312.pyc': '7cd6d6ec1c031009ea9961aa14205b783b8cef8ed9636452504284b9ee81d927', 'test/functional/test_framework/__pycache__/test_framework.cpython-312.pyc': '2e50ea19b4a99affbdb793382b6b729d0bad978ce45a2dc0f5366bcf8a19f8a0', 'test/functional/test_framework/__pycache__/test_node.cpython-312.pyc': 'eedc1f92a68e5b907daae79d743e74f10622c836fa42f3310be9b20b3ff93c93', 'test/functional/test_framework/__pycache__/util.cpython-312.pyc': '1279acc147c630d84ae16917c99669ed106a4c862dac4553f406c8066601de90', 'test/functional/test_framework/__pycache__/v2_p2p.cpython-312.pyc': '33f42b48697893fd57c4fa25611ae4d33c417891203487210c6d2193c9eebaed', 'test/functional/test_framework/crypto/__pycache__/bip324_cipher.cpython-312.pyc': 'f153f7db8ab92e197672faa408553f02364bafec1f7082f75e16fe4ed3dd7f30', 'test/functional/test_framework/crypto/__pycache__/chacha20.cpython-312.pyc': 'd9673138c830bd22af3c96be68bfec0fc45416b3508329885c8fc2a91c39dcea', 'test/functional/test_framework/crypto/__pycache__/ellswift.cpython-312.pyc': '186972a0da388f046949e877d7a46cbb36f4b4c3488406c24aaf82a173681196', 'test/functional/test_framework/crypto/__pycache__/hkdf.cpython-312.pyc': 'b9079b1abe40e5170b1d7f3546c479f8ed715c1d083ae36f0b2b077bfe9f8acb', 'test/functional/test_framework/crypto/__pycache__/poly1305.cpython-312.pyc': 'ed0de67f05792457ced68493c1394e8b1ac47062b27c38c519fc56aee10291b4', 'test/functional/test_framework/crypto/__pycache__/ripemd160.cpython-312.pyc': 'cf20a6dda5f07bcf3c4be955c646645c669df9eeab8a08b25ffc953181eb71d0', 'test/functional/test_framework/crypto/__pycache__/secp256k1.cpython-312.pyc': 'efa58eec131b71408a2618e9338a01eadfa4979788daf949b9d96ea44da08236', 'test/functional/test_framework/crypto/__pycache__/siphash.cpython-312.pyc': 'ef2909cfa656362773e94f05db6da620cc2ae4499e04b8e93d65c481dc4175df'}
    for name,digest in retained_bytecode.items():
        assert sha(source/name)==digest, name
        (source/name).unlink()
    state["discarded_retained_bytecode"] = retained_bytecode
    actual_source = {str(p.relative_to(source)): sha(p) for p in source.rglob("*") if p.is_file()}
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
    assert {str(p.relative_to(source)):sha(p) for p in source.rglob("*") if p.is_file()} == after_source
    (out/"source-after.json").write_text(json.dumps(after_source, sort_keys=True, indent=2)+"\n")
    run(["cmake", "-P", build/"CMakeFiles/VerifyGlobs.cmake"], "verify-globs", cwd=build)
    observed = out/"observed.ninja"; shutil.copy2(build/"build.ninja", observed)
    plan = run(["ninja", "-C", build, "-f", observed, "-n", "btx-qt"], "build-plan")
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
    assert "Linking CXX executable bin/btx-qt" in actions
    state.update(phase="compile", planned_actions=actions, original_binaries={n:sha(originals/n) for n in ("btx-qt","btxd","btx-cli")})
    assert shutil.disk_usage(w).free > 2 * 1024**3
    # Exactly one serial compile invocation; no retry/reconfigure/broad fallback.
    run(["ninja", "-C", build, "-f", observed, "-j1", "btx-qt"], "compile", limit=600)
    assert sha(cache) == state["profile"]["cache_sha256"]
    assert sha(build/"build.ninja") == state["profile"]["build_ninja_sha256"]
    assert sha(build/"bin/btx-cli") == sha(originals/"btx-cli")
    binaries = w/"compiled-binaries"; binaries.mkdir()
    for n in ("btx-qt", "btxd", "btx-cli"): shutil.copy2(build/"bin"/n, binaries/n)
    state["candidate_binaries"] = {n:sha(binaries/n) for n in ("btx-qt", "btxd", "btx-cli")}
    assert state["candidate_binaries"]["btx-qt"] != state["original_binaries"]["btx-qt"]
    assert state["candidate_binaries"]["btxd"] == state["original_binaries"]["btxd"]
    state.update(phase="built", native_control_in_qt_only=True, setup_daemon_unchanged=True, checkpoint_sha256=ARCHIVE, encrypt499_sha256=ENCRYPT,
                 source_before_manifest_sha256=sha(out/"source-before.json"), source_after_manifest_sha256=sha(out/"source-after.json"))
except Exception as exc:
    state["error"] = repr(exc)
    raise
finally:
    (out/"result.json").write_text(json.dumps(state, indent=2)+"\n")
