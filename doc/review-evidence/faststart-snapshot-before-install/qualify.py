import contextlib
import hashlib
import gzip
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import tarfile
import sys
import tempfile
from unittest import mock

ROOT = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("installer_fixture", ROOT / sys.argv[1] / "test/util/btx_agent_setup_test.py")
fixture = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fixture)
cases = fixture.BTXAgentSetupTest()
cases.setUp()
setup = cases.module


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def release(path, marker, *, with_companion):
    path.mkdir()
    archive = cases._build_fake_archive(path, extra_files={
        "bin/btxd": f"#!/bin/sh\nprintf '%s\\n' '{marker}'\n",
        "bin/btx-cli": "#!/bin/sh\nexit 0\n",
    })
    tree = path / "package/btx-29.2"
    for launcher in (tree / "bin").iterdir():
        launcher.chmod(0o755)
    def stable_metadata(member):
        member.mtime = 0
        return member

    with archive.open("wb") as raw:
        with gzip.GzipFile(fileobj=raw, filename="", mtime=0) as compressed:
            with tarfile.open(fileobj=compressed, mode="w") as bundle:
                bundle.add(tree, arcname=tree.name, filter=stable_metadata)
    manifest = cases._write_manifest(path, archive, include_snapshot_manifest=with_companion)
    return archive, manifest


def invoke(manifest, *, preset=False):
    args = [
        "--release-manifest", str(manifest), "--platform", "linux-x86_64",
        "--install-dir", str(install), "--datadir", str(data), "--json",
    ]
    if preset:
        args.extend(("--force", "--preset", "service"))
    stdout, stderr = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
        try:
            result = {"returned": setup.main(args)}
        except (OSError, ValueError) as exc:
            result = {"raised": type(exc).__name__, "message": str(exc)}
    if stdout.getvalue() and "returned" in result:
        result["summary"] = json.loads(stdout.getvalue())
    result["stderr"] = stderr.getvalue()
    return result


def probe(path):
    if not path.is_file():
        return {"present": False}
    cmd = subprocess.run([str(path), "--version"], capture_output=True, text=True, timeout=5)
    return {"present": True, "exit": cmd.returncode, "marker": cmd.stdout.strip(), "sha256": digest(path)}


with tempfile.TemporaryDirectory(prefix="faststart-companion-", dir=ROOT) as tmp:
    directory = Path(tmp)
    install, data = directory / "install", directory / "data"
    data.mkdir()
    sentinel = data / "keep.txt"
    sentinel.write_text("separate data directory stays intact\n")
    initial_data = digest(sentinel)
    _, manifest_a = release(directory / "release-a", "fixture-A", with_companion=False)
    archive_b, manifest_b = release(directory / "release-b", "fixture-B", with_companion=True)
    archive_sha = digest(archive_b)
    release_manifest_sha = digest(manifest_b)
    checksum_list_sha = digest(manifest_b.parent / "SHA256SUMS")
    companion = manifest_b.parent / "snapshot.manifest.json"
    expected = companion.read_bytes()
    expected_sha = digest(companion)

    initial = invoke(manifest_a)
    assert initial["returned"] == 0, initial
    original = Path(initial["summary"]["btxd"])
    before = probe(original)
    assert before["exit"] == 0 and before["marker"] == "fixture-A", before
    calls = []

    def observe_bootstrap(command, *, json_mode):
        assert command[2] == "service" and json_mode
        companion_arg = next(x.partition("=")[2] for x in command if x.startswith("--snapshot-manifest="))
        launcher_arg = next(x.partition("=")[2] for x in command if x.startswith("--btxd="))
        calls.append({"preset": "service", "companion_sha256": digest(Path(companion_arg)),
                      "launcher": probe(Path(launcher_arg))})

    # Only the companion payload changes. The manifest, committed digests and
    # valid replacement archive remain identical across attempts.
    companion.write_bytes(b'{"chain":"wrong-fixture-chain"}\n')
    bad_sha = digest(companion)
    assert bad_sha != expected_sha
    with mock.patch.object(setup, "run_logged_subprocess", side_effect=observe_bootstrap):
        failed = invoke(manifest_b, preset=True)
        bootstrap_before_retry = len(calls)
        launcher_before_retry = probe(original)
        install_staging_before_retry = sorted(x.name for x in directory.glob("install.*"))
        data_before_retry = digest(sentinel)
        companion.write_bytes(expected)
        retry = invoke(manifest_b, preset=True)
        launcher_after_retry = probe(original)
        install_staging_after_retry = sorted(x.name for x in directory.glob("install.*"))
        data_after_retry = digest(sentinel)

    assert digest(archive_b) == archive_sha
    assert digest(manifest_b) == release_manifest_sha
    assert digest(manifest_b.parent / "SHA256SUMS") == checksum_list_sha
    result = {
        "base": "7d65025bb3bff27e4f6c2fdc95f33e4b859a2df5",
        "installer_sha256": digest(fixture.SCRIPT_PATH),
        "archive_sha256_for_both_attempts": archive_sha,
        "companion_expected_sha256": expected_sha, "companion_bad_sha256": bad_sha,
        "initial_launcher": before, "bad_manifest_attempt": failed,
        "launcher_before_retry": launcher_before_retry,
        "bootstrap_calls_before_retry": bootstrap_before_retry,
        "retry": retry, "launcher_after_retry": launcher_after_retry, "bootstrap_calls": calls,
        "data_sentinel_intact": initial_data == data_before_retry == data_after_retry,
        "staging_before_retry": install_staging_before_retry, "staging_after_retry": install_staging_after_retry,
    }
result["temporary_directory_removed"] = not directory.exists()
(ROOT / sys.argv[2]).write_text(json.dumps(result, indent=2) + "\n")
assert failed.get("raised") == "ValueError" and "SHA256 mismatch for snapshot.manifest.json" in failed.get("message", "")
assert bootstrap_before_retry == 0
assert retry.get("returned") == 0 and launcher_after_retry.get("exit") == 0 and launcher_after_retry.get("marker") == "fixture-B"
assert len(calls) == 1 and calls[0]["companion_sha256"] == expected_sha
assert calls[0]["launcher"] == launcher_after_retry
assert result["data_sentinel_intact"] and result["temporary_directory_removed"]
assert not install_staging_before_retry and not install_staging_after_retry
print(json.dumps({key: result[key] for key in ("initial_launcher", "bad_manifest_attempt", "launcher_before_retry",
    "bootstrap_calls_before_retry", "launcher_after_retry", "bootstrap_calls", "data_sentinel_intact")}, indent=2))

assert launcher_before_retry == before, "The original launcher must stay runnable and byte-identical after a bad manifest"
