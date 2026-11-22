import contextlib
import errno
import gzip
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile
from unittest import mock

root = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location(
    "fixture", root / sys.argv[1] / "test/util/btx_agent_setup_test.py"
)
fixture = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fixture)
cases = fixture.BTXAgentSetupTest()
cases.setUp()
setup = cases.module

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def release(path, marker):
    path.mkdir()
    archive = cases._build_fake_archive(path, extra_files={
        "bin/btxd": f"#!/bin/sh\nprintf '%s\\n' '{marker}'\n",
        "bin/btx-cli": "#!/bin/sh\nexit 0\n",
    })
    package = path / "package/btx-29.2"
    for launcher in (package / "bin").iterdir():
        launcher.chmod(0o755)
    def stable_metadata(member):
        member.mtime = 0
        return member

    with archive.open("wb") as raw:
        with gzip.GzipFile(fileobj=raw, filename="", mtime=0) as compressed:
            with tarfile.open(fileobj=compressed, mode="w") as bundle:
                bundle.add(package, arcname="btx-29.2", filter=stable_metadata)
    return archive, cases._write_manifest(path, archive, include_snapshot_manifest=False)

def invoke(manifest, force=False):
    out, err = io.StringIO(), io.StringIO()
    args = [
        "--release-manifest", str(manifest), "--platform", "linux-x86_64",
        "--install-dir", str(install), "--datadir", str(data), "--json",
    ]
    if force:
        args.append("--force")
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        try:
            result = {"entry_return": setup.main(args)}
        except OSError as exc:
            result = {"raised": type(exc).__name__, "errno": exc.errno, "message": str(exc)}
    result.update(stdout=out.getvalue(), stderr=err.getvalue())
    return result

def launch(path):
    try:
        response = subprocess.run([str(path), "--version"], capture_output=True, text=True, timeout=5)
    except FileNotFoundError:
        return {"exists": False, "outcome": "launcher_missing"}
    return {"exists": True, "exit": response.returncode, "marker": response.stdout.strip(), "sha256": sha(path)}

with tempfile.TemporaryDirectory(prefix="installer-replacement-", dir=root) as temporary:
    temp = Path(temporary)
    install, data = temp / "install", temp / "data"
    data.mkdir()
    sentinel = data / "keep.txt"
    sentinel.write_text("separate data directory\n")
    data_digest = sha(sentinel)
    archive_a, manifest_a = release(temp / "release-a", "fixture-A")
    archive_b, manifest_b = release(temp / "release-b", "fixture-B")
    digest_b = sha(archive_b)

    first = invoke(manifest_a)
    assert first["entry_return"] == 0, first
    original = Path(json.loads(first["stdout"])["btxd"])
    before = launch(original)
    assert before["exit"] == 0 and before["marker"] == "fixture-A", before

    no_force = invoke(manifest_b)
    assert no_force.get("raised") == "FileExistsError" and launch(original) == before, no_force

    makefile = tarfile.TarFile.makefile
    writes = []

    def fail_second_write(bundle, member, target):
        if len(writes) == 1:
            staging = Path(target).relative_to(temp).parts[0]
            assert staging.startswith("install.")
            assert sha(Path(bundle.name)) == digest_b
            writes.append({"failed_member": member.name, "staging": staging,
                           "verified_archive_sha256": digest_b})
            raise OSError(errno.ENOSPC, "simulated staging write failure")
        result = makefile(bundle, member, target)
        writes.append({"written_member": member.name, "exists_after_write": Path(target).is_file()})
        return result

    with mock.patch.object(tarfile.TarFile, "makefile", fail_second_write):
        failed = invoke(manifest_b, force=True)
    stage_after_failure = sorted(x.name for x in temp.glob("install.*"))
    install_exists_after_failure = install.is_dir()
    old_after_failure = launch(original)
    data_after_failure = sha(sentinel)

    assert sha(archive_b) == digest_b
    retry = invoke(manifest_b, force=True)
    retry_launcher = launch(original)
    stage_after_retry = sorted(x.name for x in temp.glob("install.*"))
    data_after_retry = sha(sentinel)
    result = {
        "source": "7d65025bb3bff27e4f6c2fdc95f33e4b859a2df5",
        "installer_sha256": sha(fixture.SCRIPT_PATH),
        "archive_b_sha256": digest_b, "failure_writes": writes,
        "initial_launch": before, "no_force": no_force, "forced_failure": failed,
        "install_directory_exists_after_failure": install_exists_after_failure,
        "old_launch_before_retry": old_after_failure, "staging_after_failure": stage_after_failure,
        "retry": retry, "retry_launch": retry_launcher, "staging_after_retry": stage_after_retry,
        "sentinel_preserved": data_digest == data_after_failure == data_after_retry,
    }

result["temporary_install_removed"] = not temp.exists()
(root / sys.argv[2]).write_text(json.dumps(result, indent=2) + "\n")
assert failed.get("errno") == errno.ENOSPC and len(writes) == 2 and writes[0]["exists_after_write"], result
assert retry.get("entry_return") == 0 and retry_launcher.get("exit") == 0 and retry_launcher.get("marker") == "fixture-B", result
assert result["sentinel_preserved"] and result["temporary_install_removed"] and not stage_after_failure and not stage_after_retry, result
print(json.dumps({k: result[k] for k in ("initial_launch", "failure_writes", "old_launch_before_retry", "retry_launch", "sentinel_preserved")}, indent=2))
assert old_after_failure == before, "Original launcher must remain runnable and byte-identical before retry"
