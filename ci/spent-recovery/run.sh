#!/usr/bin/env bash
set -euo pipefail
mkdir -p records
python3 -m venv "$RUNNER_TEMP/deps"
"$RUNNER_TEMP/deps/bin/pip" install --only-binary=:all: cryptography==46.0.4 pytest==8.4.2
curl -fsSL --max-time 120 --retry 2 https://bitcoincore.org/bin/bitcoin-core-30.4/bitcoin-30.4-x86_64-linux-gnu.tar.gz -o "$RUNNER_TEMP/core.tgz"
echo "051a18c595d9a27df23cb7187ff9fb343e90943cb142af751e12787806500c3d  $RUNNER_TEMP/core.tgz" | sha256sum -c
tar -xzf "$RUNNER_TEMP/core.tgz" -C "$RUNNER_TEMP" bitcoin-30.4/bin/bitcoind
export BITCOIND="$RUNNER_TEMP/bitcoin-30.4/bin/bitcoind" TEST_ROOT="$RUNNER_TEMP/spent-recovery"
echo "e4f5c68ea419820592a50a744040ab0c08f84fff5942ebe92eca21f5ccddcb5c  $BITCOIND" | sha256sum -c
PYTHONPATH="$PWD/contrib/swapnet:$PWD/contrib/swapnet/tests" timeout --kill-after=20s 6m "$RUNNER_TEMP/deps/bin/python" -u ci/spent-recovery/check.py
