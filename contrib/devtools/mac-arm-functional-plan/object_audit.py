"""Record object inventory changes across a Mac configure-only preflight."""
import hashlib
import json
import os
import re
import stat

OBJECT_SUFFIXES = {".o", ".obj"}
PROBE_DIRECTORIES = {"CMakeScratch", "CMakeTmp"}
COMPILER_ID_DIRECTORIES = {"CompilerIdC", "CompilerIdCXX", "CompilerIdOBJC", "CompilerIdOBJCXX"}


def is_cmake_probe(relative_path):
    parts = relative_path.split("/")
    for index, part in enumerate(parts[:-1]):
        if part != "CMakeFiles":
            continue
        if parts[index + 1] in PROBE_DIRECTORIES:
            return True
        if (index + 3 < len(parts) and re.fullmatch(r"\d+(?:\.\d+)+(?:[-.][A-Za-z0-9]+)*", parts[index + 1])
                and parts[index + 2] in COMPILER_ID_DIRECTORIES):
            return True
    return False


def snapshot(build):
    result = {}
    for path in sorted(build.rglob("*")):
        if path.suffix not in OBJECT_SUFFIXES:
            continue
        info = path.lstat()
        if stat.S_ISDIR(info.st_mode):
            continue
        relative = path.relative_to(build).as_posix()
        entry = {"size": info.st_size, "mtime_ns": info.st_mtime_ns}
        if stat.S_ISREG(info.st_mode):
            digest = hashlib.sha256()
            with path.open("rb") as file:
                for chunk in iter(lambda: file.read(1024 * 1024), b""):
                    digest.update(chunk)
            entry.update(type="file", sha256=digest.hexdigest())
        elif stat.S_ISLNK(info.st_mode):
            entry.update(type="symlink", target=os.readlink(path))
        else:
            entry.update(type="other", mode=info.st_mode)
        result[relative] = entry
    return result


def compare(before, after):
    summary = {"before_count": len(before), "after_count": len(after),
               "product_or_unclassified": 0, "configuration_probes": 0}
    differences = []
    for path in sorted(before.keys() | after.keys()):
        old, new = before.get(path), after.get(path)
        if old == new:
            continue
        category = "configuration_probes" if is_cmake_probe(path) else "product_or_unclassified"
        summary[category] += 1
        differences.append({"path": path, "category": category,
                            "change": "added" if old is None else "removed" if new is None else "changed",
                            "before": old, "after": new})
    return dict(summary=summary, differences=differences)


def write_audit(report, before, after):
    audit = compare(before, after)
    report.write_text(json.dumps(audit, indent=2) + "\n")
    return audit["summary"]
