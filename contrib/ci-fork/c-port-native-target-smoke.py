"""Exercise the two Windows default-target repairs in disposable directories."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile


def run(exe, args, log, env=None):
    result = subprocess.run(
        [str(exe), *args], env=env, stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT, text=True, errors="replace", timeout=180,
    )
    log.write_text(result.stdout, encoding="utf-8")
    return result


def wallet(exe, logs, scratch):
    args = ["-regtest", f"-datadir={scratch}", "-wallet=cport-smoke"]
    for command in ("create", "info"):
        result = run(exe, [*args, command], logs / f"wallet-{command}.log")
        if result.returncode or not all(
            field in result.stdout for field in (
                "Name: cport-smoke", "Format: sqlite", "Descriptors: yes",
            )
        ):
            raise RuntimeError(f"wallet {command} did not confirm the SQLite wallet")
    if not (scratch / "regtest" / "wallets" / "cport-smoke" / "wallet.dat").is_file():
        raise RuntimeError("wallet.dat was not created in the disposable datadir")


def harness(exe, logs, scratch):
    env = dict(os.environ)
    env.pop("BTX_MATMUL_V4_BACKEND", None)
    report = scratch / "cpu.json"
    args = ["--toy", "--episodes", "3", "--backend", "cpu", "--out"]
    result = run(exe, [*args, str(report)], logs / "harness-cpu.log", env)
    if result.returncode:
        raise RuntimeError("CPU toy harness failed")
    record = json.loads(report.read_text(encoding="utf-8"))
    if record["backend"] != "cpu" or record["backend_requested"] != "cpu":
        raise RuntimeError("CPU toy harness reported a different backend")
    env["BTX_MATMUL_V4_BACKEND"] = "cuda"
    conflict = scratch / "conflict.json"
    result = run(exe, [*args, str(conflict)], logs / "harness-conflict.log", env)
    if result.returncode != 2 or "conflict:" not in result.stdout or conflict.exists():
        raise RuntimeError("harness did not reject the backend conflict before output")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bin", type=Path, required=True)
    parser.add_argument("--logs", type=Path, required=True)
    args = parser.parse_args()
    args.logs.mkdir(parents=True, exist_ok=True)
    results = {}
    for target, check in (("btx-wallet", wallet), ("matmul-v4-rc-harness", harness)):
        exe = (args.bin / f"{target}.exe").resolve()
        result = {"status": "not_built"}
        results[target] = result
        if not exe.is_file():
            continue
        with exe.open("rb") as stream:
            digest = hashlib.sha256()
            for block in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(block)
        result["sha256"] = digest.hexdigest()
        try:
            with tempfile.TemporaryDirectory(prefix="cport-") as scratch:
                check(exe, args.logs, Path(scratch))
        except (OSError, RuntimeError, ValueError, subprocess.TimeoutExpired) as exc:
            result.update(status="fail", reason=str(exc))
        else:
            result["status"] = "pass"
    (args.logs / "native-target-smoke.json").write_text(
        json.dumps(results, indent=2) + "\n", encoding="utf-8"
    )
    return int(any(result["status"] != "pass" for result in results.values()))


if __name__ == "__main__":
    raise SystemExit(main())
