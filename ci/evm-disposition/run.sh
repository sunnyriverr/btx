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
for mode in same-lock drop cancel; do
  echo "Starting bounded $mode recovery case"
  anvil --port 18545 --slots-in-an-epoch 1 > "records/anvil-$mode.log" 2>&1 &
  anvil_pid=$!
  trap 'kill "$anvil_pid" 2>/dev/null || true; wait "$anvil_pid" || true' EXIT
  sleep 2
  PYTHONPATH="$PWD/product/contrib/swapnet:$PWD/product/contrib/swapnet/tests" timeout --kill-after=15s 90s "$RUNNER_TEMP/evm-deps/bin/python" -u ci/evm-disposition/check.py "$RUNNER_TEMP/evm-disposition-$mode" "$mode" | tee "records/$mode-measurement.log"
  kill "$anvil_pid";wait "$anvil_pid" || true
  trap - EXIT
done
