"""Runner-only small entry-point preflight; no BTX, compiler or package execution."""
from pathlib import Path
import datetime, hashlib, importlib.util, json, os, shutil, subprocess, sys, tempfile, time
from unittest import mock

w = Path(os.environ["GITHUB_WORKSPACE"]).resolve()
assert str(w) == "/home/runner/work/btx/btx"
control = w / "control"
records = w / "build-records"
records.mkdir(exist_ok=True)
deadline = time.monotonic() + 45
def tick():
    if time.monotonic() >= deadline:
        raise RuntimeError("Portable preflight time bound")
def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module
attempts = []
def deny(*args, **kwargs):
    attempts.append(repr(args[:1]))
    raise RuntimeError("External execution forbidden during portable overlay preflight")
result = {"scope": "Small release-script copy/import/overlay-integrity checks only",
          "native_probes": False, "build": False, "external_attempts": attempts}
try:
    with mock.patch.object(subprocess, "Popen", side_effect=deny):
        helper = load("package_entrypoint_preflight", control / "packaging/package_candidate.py")
        diagnostic = load("selection_entrypoint_preflight", control / "record-python-selection.py")
        inputs = json.loads((control / "inputs.json").read_text())
        with tempfile.TemporaryDirectory(prefix="s3-overlay-preflight-", dir=w) as scratch:
            scratch = Path(scratch)
            product = scratch / "product"
            source = product / "scripts/release"
            shutil.copytree(w / "accepted-source/scripts/release", source,
                            ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
            (scratch / "control/patch").mkdir(parents=True)
            for name in ("bundle_python_runtime.py", "nested-site-packages.patch"):
                shutil.copyfile(control / "patch" / name, scratch / "control/patch" / name)
            shutil.copyfile(control / "record-python-selection.py",
                            scratch / "control/record-python-selection.py")
            local_records = scratch / "records"
            local_records.mkdir()
            overlay, implementation = helper.prepare_implementation(
                scratch, product, inputs, local_records, tick)
            helper.verify_implementation(scratch, product, overlay, implementation, local_records, tick)
            result["release_files"] = len(implementation["source_files"])
            result["single_reviewed_delta_bound"] = True
            result["pristine_source_and_overlay_check"] = "PASS"
            old = (overlay / "bundle_python_runtime.py").read_bytes()
            fresh_value = json.loads(json.dumps(implementation))
            (overlay / "bundle_python_runtime.py").write_bytes(old + b"\n# controlled preflight change\n")
            try:
                helper.verify_implementation(scratch, product, overlay, implementation, local_records, tick)
            except RuntimeError as error:
                assert "Candidate packaging implementation changed during use" in str(error)
                result["intentional_overlay_change_rejected"] = str(error)
            else:
                raise RuntimeError("Preflight failed to reject altered overlay")
            (overlay / "bundle_python_runtime.py").write_bytes(old)
            helper.verify_implementation(scratch, product, overlay, fresh_value, local_records, tick)
            # Exercise both diagnostic source loaders without executing its native main/probe.
            original = diagnostic.load("preflight_original_selector",
                                       source / "bundle_python_runtime.py", diagnostic.ORIGINAL)
            candidate = diagnostic.load("preflight_candidate_selector",
                                        overlay / "bundle_python_runtime.py", diagnostic.CANDIDATE)
            assert callable(original._third_party_roots) and callable(candidate._third_party_roots)
            assert callable(diagnostic.main)
            result["diagnostic_import_and_pinned_loaders"] = "PASS"
    assert not attempts
    result["verdict"] = "PORTABLE_OVERLAY_ENTRYPOINT_PREFLIGHT_PASS"
except BaseException as error:
    result["verdict"] = "PREFLIGHT_FAILED"
    result["error"] = repr(error)
    raise
finally:
    result["utc"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    (records / "entrypoint-preflight.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result))
