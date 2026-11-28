"""Inventory generated files and tracked source timestamps for the immutable resume cache."""
import json
import os
from pathlib import Path
import runpy
import subprocess

CONTROL = Path(__file__).resolve().parent
PREFLIGHT = runpy.run_path(str(CONTROL / "daemon-plan.py"))
BUILD = PREFLIGHT["BUILD"]
SOURCE = PREFLIGHT["SOURCE"]
RECORDS = PREFLIGHT["RECORDS"]
HASH = PREFLIGHT["get_hash"]


def stat_info(path):
    stat = path.stat()
    return {"bytes": stat.st_size, "mtime_ns": stat.st_mtime_ns}


def main():
    RECORDS.mkdir(exist_ok=True)
    result_path = RECORDS / "link-result.json"
    result = json.loads(result_path.read_text()) if result_path.exists() else {}
    objects = sorted(path for path in (BUILD / "src").rglob("*.obj") if path.is_file())
    key = f'msvc-959-btxd-checkpoint-{os.environ["GITHUB_RUN_ID"]}-{os.environ["GITHUB_RUN_ATTEMPT"]}'
    receipt = {"key": key, "candidate": PREFLIGHT["CANDIDATE"], "plan_admitted": result.get("plan_admitted", False),
               "objects": len(objects), "linked": result.get("linked", False)}
    if objects:
        paths = [path for path in BUILD.rglob("*") if path.is_file()]
        build_files = {path.relative_to(BUILD).as_posix(): {**stat_info(path), "sha256": HASH(path)}
                       for path in paths}
        source_names = subprocess.check_output(["git", "-C", str(SOURCE), "ls-files", "-z"], timeout=30)
        tracked = [SOURCE / name for name in source_names.decode("utf-8").split("\0") if name]
        timestamps = {path.relative_to(SOURCE).as_posix(): stat_info(path) for path in tracked if path.is_file()}
        assert len(timestamps) >= 1000 and (BUILD / ".ninja_log").is_file() and (BUILD / ".ninja_deps").is_file()
        manifest = RECORDS / "checkpoint-manifest.json"
        manifest.write_text(json.dumps({"candidate": PREFLIGHT["CANDIDATE"], "cache_key": key,
                                        "build_files": build_files, "tracked_source": timestamps},
                                       indent=2) + "\n", encoding="utf-8")
        receipt.update(manifest_sha256=HASH(manifest), build_files=len(build_files),
                       source_files=len(timestamps), build_bytes=sum(f["bytes"] for f in build_files.values()),
                       archives=sum(name.endswith(".lib") and not name.startswith("CMakeFiles/")
                                    for name in build_files), ninja_state_saved=True)
    (RECORDS / "checkpoint-receipt.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    with Path(os.environ["GITHUB_OUTPUT"]).open("a", encoding="utf-8") as output:
        output.write(f"has_objects={'true' if objects else 'false'}\n")
    print(json.dumps(receipt), flush=True)


if __name__ == "__main__":
    main()
