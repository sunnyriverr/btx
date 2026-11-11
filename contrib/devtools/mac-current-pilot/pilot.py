"""Verify and restore two retained Mac checkpoints and inspect the current graph."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import tarfile

HERE = Path(__file__).resolve().parent
BASE = "36ab43008cac48aa5c8410e4b70d90a249196a33"
TARGET = "c6f9678dd225572528d06c456c16eb4c78bc637c"
WORK = Path(os.environ["GITHUB_WORKSPACE"])
LOG = WORK / "pilot-records"
PRODUCT = WORK / "product"
BUILD = WORK / "mac-config-build"
TARGETS = json.loads((HERE / "targets.json").read_text())


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def run(label, *command, timeout=120, env=None):
    print(label, flush=True)
    with (LOG / (label + ".log")).open("w") as out:
        subprocess.run(command, cwd=WORK, env=env, stdout=out,
                       stderr=subprocess.STDOUT, timeout=timeout, check=True)
    return (LOG / (label + ".log")).read_text()


def restore(name, roots):
    expected = json.loads((HERE / "checkpoints.json").read_text())[name]
    payload = WORK / (name + "-payload") / "after"
    receipt = json.loads((payload / "receipt.json").read_text())
    archive = payload / "checkpoint.tar.gz"
    manifest = payload / "inventory.json"
    assert receipt == expected, name
    assert digest(archive) == receipt["sha256"] and archive.stat().st_size == receipt["bytes"]
    assert digest(manifest) == receipt["inventory_sha256"]
    inventory = json.loads(manifest.read_text())
    assert len(inventory) == receipt["entries"]
    stage = WORK / ("restored-" + name)
    stage.mkdir()
    with tarfile.open(archive) as bundle:
        members = bundle.getmembers()
        assert len(members) == len(inventory) and {m.name for m in members} == set(inventory)
        for member in members:
            path = Path(member.name)
            assert not path.is_absolute() and ".." not in path.parts and path.parts[0] in roots
            expected_type = inventory[member.name]["type"]
            if member.issym():
                assert expected_type == "symlink"
                link = Path(member.linkname)
                assert not link.is_absolute() and member.linkname == inventory[member.name]["archive_target"]
                assert any((stage / path.parent / link).resolve().is_relative_to(stage / root)
                           for root in roots)
            elif member.islnk():
                assert expected_type == "file" and member.linkname in inventory
            else:
                assert ((member.isfile() and expected_type == "file")
                        or (member.isdir() and expected_type == "dir"))
        bundle.extractall(stage, filter="data")
    for relative, item in sorted(inventory.items(), key=lambda row: -len(Path(row[0]).parts)):
        path = stage / relative
        if item["type"] == "symlink":
            assert path.is_symlink() and os.readlink(path) == item["archive_target"]
        else:
            assert not path.is_symlink()
            if item["type"] == "file":
                assert path.stat().st_size == item["bytes"] and digest(path) == item["sha256"]
            path.chmod(item["mode"])
        os.utime(path, ns=(item["mtime_ns"],) * 2, follow_symlinks=False)
        info = path.lstat()
        assert stat.S_IMODE(info.st_mode) == item["mode"] and info.st_mtime_ns == item["mtime_ns"]
    assert digest(archive) == receipt["sha256"]
    return stage, inventory


def main():
    LOG.mkdir()
    result = {"source": TARGET, "compiled": False, "restored": {}}
    try:
        assert shutil.disk_usage(WORK).free > 16 * 1024**3
        for name, roots in (("cmake", ("product", "mac-config-build")),
                            ("cargo", ("product", "atlas-target"))):
            stage, inventory = restore(name, roots)
            result["restored"][name] = len(inventory)
            if name == "cmake":
                cmake_stage, cmake_inventory = stage, inventory
            else:
                (stage / "atlas-target").rename(WORK / "atlas-target")

        # The prior configure recreates the runner dependencies at the cached paths.
        shutil.rmtree(BUILD)
        PRODUCT.rename(WORK / "identity-checkout")
        (cmake_stage / "product").rename(PRODUCT)
        (cmake_stage / "mac-config-build").rename(BUILD)
        (WORK / "identity-checkout" / ".git").rename(PRODUCT / ".git")
        for relative, item in cmake_inventory.items():
            path = WORK / relative
            if item["type"] == "symlink" and item["target"] != item["archive_target"]:
                assert Path(item["target"]).resolve().is_relative_to(WORK)
                path.unlink()
                path.symlink_to(item["target"])
                os.utime(path, ns=(item["mtime_ns"],) * 2, follow_symlinks=False)
        assert not run("clean-restored-source", "git", "-C", PRODUCT, "status", "--porcelain").strip()
        assert run("restored-source", "git", "-C", PRODUCT, "rev-parse", "HEAD").strip() == BASE
        run("fetch-target", "git", "-C", PRODUCT, "fetch", "--depth=1", "origin", TARGET)
        run("select-target", "git", "-C", PRODUCT, "checkout", "--detach", TARGET)
        assert run("current-source", "git", "-C", PRODUCT, "rev-parse", "HEAD").strip() == TARGET
        run("configure", "cmake", "-S", PRODUCT, "-B", BUILD, timeout=300)
        inspection = BUILD / "checkpoint-inspection.ninja"
        inspection.write_text("include build.ninja\n")
        graph = run("current-command-graph", "ninja", "-C", BUILD, "-f", inspection.name,
                    "-t", "commands", *TARGETS)
        plan = run("ninja-dry-plan", "ninja", "-C", BUILD, "-f", inspection.name,
                   "-n", "-d", "explain", *TARGETS)
        result["ninja_actions"] = sum(line.startswith("[") for line in plan.splitlines())
        assert result["ninja_actions"] > 0 and graph.strip()
        scheduled = set()
        for line in plan.splitlines():
            for prefix in ("Building CXX object ", "Building C object "):
                if prefix in line:
                    scheduled.add("mac-config-build/" + line.split(prefix, 1)[1].strip())
        result["cached_objects_scheduled"] = sorted(scheduled.intersection(cmake_inventory))
        result["cmake_objects_preserved"] = 0
        for relative, item in cmake_inventory.items():
            if relative.startswith("mac-config-build/") and relative.endswith(".o"):
                path = WORK / relative
                assert digest(path) == item["sha256"], ("object contents changed", relative)
                if path.stat().st_mtime_ns != item["mtime_ns"]:
                    probe = ("mac-config-build/src/libbitcoinpqc/shake_a64_probe/build/"
                             "CMakeFiles/shake_a64_probe.dir/shake_a64_probe.s.o")
                    assert relative == probe, ("unexpected object timestamp change", relative)
                    result["configure_probe_refreshed"] = relative
                else:
                    result["cmake_objects_preserved"] += 1
        run("rust-install-pinned", "rustup", "toolchain", "install", "1.95.0",
            "--profile", "minimal", "--target", "aarch64-apple-darwin", timeout=300)
        cargo_env = dict(os.environ, RUSTUP_TOOLCHAIN="1.95.0",
                         CARGO_TARGET_DIR=str(WORK / "atlas-target"))
        rust = run("rust-version", "rustc", "-Vv", env=cargo_env)
        assert "release: 1.95.0" in rust and "host: aarch64-apple-darwin" in rust
        manifest = PRODUCT / "gui/atlas/Cargo.toml"
        run("cargo-fetch-locked", "cargo", "fetch", "--locked", "--manifest-path", manifest,
            "--target", "aarch64-apple-darwin", timeout=300, env=cargo_env)
        run("cargo-metadata-offline", "cargo", "metadata", "--locked", "--offline",
            "--manifest-path", manifest, "--format-version", "1", "--filter-platform",
            "aarch64-apple-darwin", env=cargo_env)
        assert not run("clean-current-source", "git", "-C", PRODUCT, "status", "--porcelain").strip()
        result["complete"] = True
    except Exception as exc:
        result["error"] = repr(exc)
        raise
    finally:
        (LOG / "result.json").write_text(json.dumps(result, indent=2) + "\n")


if __name__ == "__main__":
    main()
