"""Observe cloud configuration status across three disposable helper launches."""
import argparse
import hashlib
import json
from pathlib import Path
import tempfile

from fixture import Fixture
from origin import Origin


HELPER_SHA = "28d7ecb6c611e5676d85de7a64038bc7d07cd0b6b2fb2606390d5e6405838ad2"
DUMMY_KEY = "TEST_KEY_NOT_REAL"
DUMMY_SECRET = "TEST_SECRET_NOT_REAL"


class CloudStatusFixture(Fixture):
    def rpc(self, method, *params):
        reply = super().rpc(method, *params)
        assert reply["id"] == "settings-qualification", reply
        return reply


def status(fixture):
    value = fixture.ok("getcloudstorageinfo")
    assert value["automatic_spend_atoms"] == 0, value
    assert value["secrets_in_response"] is False, value
    assert all(marker not in json.dumps(value) for marker in (DUMMY_KEY, DUMMY_SECRET))
    local = fixture.ok("listmodels")
    assert isinstance(local["models"], list), local
    return value


def sha(value):
    return hashlib.sha256(value).hexdigest()


def observe(helper, output, result):
    result["helper_sha256"] = sha(helper.read_bytes())
    assert result["helper_sha256"] == HELPER_SHA
    with tempfile.TemporaryDirectory(prefix="s2-cloud-status-", dir="/tmp") as directory:
        root = Path(directory)
        result["runtime"] = str(root)
        fixture = CloudStatusFixture(helper, root, output)
        cloud = fixture.model / "cloud.json"
        budget = fixture.model / "cloud-budget.json"
        with Origin(mode="success") as origin:
            credentials = root / "credentials"
            credentials.write_text(f"aws_access_key_id={DUMMY_KEY}\naws_secret_access_key={DUMMY_SECRET}\n")
            credentials.chmod(0o600)
            with fixture.running():
                never = status(fixture)
                result["never_configured"] = never
                assert never["configured"] is False and "init_error" not in never, never
                assert not cloud.exists()
                options = {
                    "endpoint": origin.endpoint,
                    "bucket": "fixture",
                    "prefix": "cloud-status",
                    "provider": "GENERIC_S3",
                    "region": "us-east-1",
                    "layout": "SOURCE_FILES",
                    "credential_ref": str(credentials),
                    "credential_ref_kind": "path",
                    "use_fake": False,
                    "allow_http_loopback": True,
                    "automatic_spend_atoms": 0,
                    "idempotency_key": "cloud-status-initial",
                }
                configured = fixture.ok("setcloudstorage", options)
                assert configured["applied"] and configured["configured"], configured
            original = cloud.read_bytes()
            assert json.loads(original)["endpoint"] == origin.endpoint
            original_budget = budget.read_bytes()
            damaged = original.rstrip()
            assert damaged.endswith(b"}")
            damaged = damaged[:-1]
            cloud.write_bytes(damaged)
            result["saved_config_sha256"] = sha(original)
            result["damaged_config_sha256"] = sha(damaged)
            result["saved_budget_sha256"] = sha(original_budget)
            requests_before_failure = origin.snapshot()["requests"]
            with fixture.running():
                failed = status(fixture)
                repeated = status(fixture)
                result["failed_load"] = failed
                result["failed_load_repeated"] = repeated
                assert failed["configured"] is False and failed == repeated, repeated
                assert cloud.read_bytes() == damaged
                assert budget.read_bytes() == original_budget
            assert cloud.read_bytes() == damaged
            assert budget.read_bytes() == original_budget
            assert origin.snapshot()["requests"] == requests_before_failure
            result["failed_load_files_preserved"] = True
            result["failed_load_origin_requests"] = 0

            cloud.write_bytes(original)
            with fixture.running():
                restored = status(fixture)
                result["restored"] = restored
                assert restored["configured"] is True and "init_error" not in restored, restored
                assert restored["layout"] == "SOURCE_FILES" and cloud.read_bytes() == original
                result["restored_budget_sha256_before_probe"] = sha(budget.read_bytes())
                requests_before_probe = len(origin.snapshot()["requests"])
                probe = fixture.ok("testcloudstorage")
                result["restored_probe"] = probe
                assert probe["probe_ok"] is True, probe
                ledger = origin.snapshot()
                result["origin"] = ledger
                methods = {row["method"] for row in ledger["requests"][requests_before_probe:]
                           if row["path"].endswith("/health/probe") and row["response_status"] == 200}
                assert {"PUT", "GET"} <= methods, ledger
            assert cloud.read_bytes() == original
            result["restored_config_preserved"] = True
            result["starts"] = fixture.starts
            result["setter_calls"] = sum(call["method"] == "setcloudstorage" for call in fixture.calls)
            assert result["starts"] == 3 and result["setter_calls"] == 1
            fixture.finish()
            result["verdict"] = (
                "FAILED_LOAD_INDISTINGUISHABLE" if failed == never else "FAILED_LOAD_STATUS_DIFFERS"
            )
    result["runtime_removed"] = not root.exists()
    assert result["runtime_removed"]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--helper", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    result = {"complete": False}
    try:
        observe(args.helper.resolve(), args.out, result)
        result["complete"] = True
    except Exception as error:
        result["fixture_error"] = repr(error)
        raise
    finally:
        (args.out / "result.json").write_text(json.dumps(result, indent=2) + "\n")


if __name__ == "__main__":
    main()
