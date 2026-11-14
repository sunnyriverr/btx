#!/usr/bin/env bash
set -euo pipefail
mkdir -p records
python3 -m venv "$RUNNER_TEMP/evm-deps"
"$RUNNER_TEMP/evm-deps/bin/pip" install --only-binary=:all: cryptography==46.0.4 pytest==8.4.2
curl -fsSL --retry 2 --max-time 120 https://github.com/foundry-rs/foundry/releases/download/v1.9.0/foundry_v1.9.0_linux_amd64.tar.gz -o "$RUNNER_TEMP/foundry.tgz"
echo "8d17599b42e3139f1a9c171be3798c4ed8e743ae17b84cc3435e57bf2a51ae99  $RUNNER_TEMP/foundry.tgz" | sha256sum -c
mkdir -p "$RUNNER_TEMP/foundry";tar -xzf "$RUNNER_TEMP/foundry.tgz" -C "$RUNNER_TEMP/foundry"
export PATH="$RUNNER_TEMP/foundry:$PATH"
forge --version | tee records/foundry.txt
forge build --root product/contrib/swapnet/contracts --skip test
anvil --port 18545 --slots-in-an-epoch 1 > records/anvil.log 2>&1 &
anvil_pid=$!;trap 'kill "$anvil_pid" 2>/dev/null || true; wait "$anvil_pid" || true' EXIT
sleep 2

PYTHONPATH="$PWD/product/contrib/swapnet:$PWD/product/contrib/swapnet/tests" timeout --kill-after=20s 5m "$RUNNER_TEMP/evm-deps/bin/python" -u ci/pending-evm/check.py "$RUNNER_TEMP/pending-recovery" | tee records/measurement.log
