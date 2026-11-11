"""Check native search-policy acknowledgement, restart and retry."""
import importlib.util
import json
from pathlib import Path
import sys
import tempfile

fixture = Path(__file__).resolve().with_name("helper-regression.py")
spec = importlib.util.spec_from_file_location("helper_fixture", fixture)
helper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helper)
publisher = "a" * 96
other = "b" * 96
binary = str(Path(sys.argv[1]).resolve())


def exercise(root, force_failed_save):
    modeldir = root / "model"
    modeldir.mkdir(parents=True)
    endpoint = root / "helper.sock"
    snapshot = modeldir / "search-index.json"
    blocked = modeldir / "search-index.json.tmp"

    def call(method, value):
        return helper.request(endpoint, method, value)

    def muted_on_disk():
        return set(json.loads(snapshot.read_text())["muted_publishers"])

    def prime_search():
        helper.result(helper.request(endpoint, "getmodelfeedstatus"))

    with helper.helper(binary, root, modeldir, endpoint):
        prime_search()
        assert helper.result(call("mutesearchpublisher", other))["muted"] is True
        assert muted_on_disk() == {other}
        if force_failed_save:
            blocked.mkdir()
            (blocked / "sentinel").write_text("obstruct")
            previous = snapshot.read_bytes()
            fault = call("mutesearchpublisher", publisher.upper())
            assert snapshot.read_bytes() == previous
            assert (blocked / "sentinel").read_text() == "obstruct"
            print(json.dumps({"case": "blocked_save", "reply": fault, "file_unchanged": True}), flush=True)
            (blocked / "sentinel").unlink()
            blocked.rmdir()

    with helper.helper(binary, root, modeldir, endpoint):
        assert muted_on_disk() == {other}
        if force_failed_save:
            prime_search()
        assert helper.result(call("mutesearchpublisher", publisher.upper()))["muted"] is True
        persisted = muted_on_disk()
        assert publisher in persisted
        print(json.dumps({"case": "primed_retry" if force_failed_save else "first_write_after_restart",
                          "new_mute_saved": True, "existing_mute_retained": other in persisted}), flush=True)

    with helper.helper(binary, root, modeldir, endpoint):
        prime_search()
        assert helper.result(call("unmutesearchpublisher", other))["muted"] is False
        assert muted_on_disk() == {publisher}
    if force_failed_save:
        err = fault["error"]
        return isinstance(err, dict) and err.get("code") == "IO_ERROR" and persisted == {other, publisher}
    return persisted == {other, publisher}


with tempfile.TemporaryDirectory(prefix="br-mute-", dir="/tmp") as tmp:
    root = Path(tmp)
    outcomes = [exercise(root / "cold", False), exercise(root / "failure", True)]
sys.exit(0 if all(outcomes) else 1)
