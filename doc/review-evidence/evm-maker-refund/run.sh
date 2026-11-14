#!/usr/bin/env bash
set -euo pipefail
mkdir -p records
sudo apt-get -o Acquire::Retries=1 update
sudo apt-get install -y --no-install-recommends libboost-dev libevent-dev libsqlite3-dev libzmq3-dev python3-dev python3-venv ninja-build ccache zstd
python3 -m venv "$RUNNER_TEMP/evm-deps"
"$RUNNER_TEMP/evm-deps/bin/pip" install --only-binary=:all: cryptography==46.0.4 pytest==8.4.2
runtime_path=$(/usr/bin/python3 -I -c 'import sys; print(next(p for p in sys.path if p.startswith("/usr/local/") and p.endswith("/dist-packages")))')
sudo mkdir -p "$runtime_path"; sudo cp -a bundle/payload/python/. "$runtime_path/"
(cd bundle/payload && sha256sum -c SHA256SUMS > ../../records/prior-binary-checksums.log)
python3 -c 'import shutil;assert shutil.disk_usage(".").free>8*1024**3'
git -C product diff --exit-code b14b1b29e476ca135bf8ca7cce8ec236c197d77d -- contrib/swapnet/swapnet
mkdir -p obj/bin
cp prior-native/obj/bin/{btxd,btx-cli} obj/bin/
grep -Fx PASS_INCREMENTAL prior-native/records/build-verdict.txt
(cd obj/bin && sha256sum btxd btx-cli) > records/reused-native-binaries.sha256
cp prior-native/records/new-binaries.sha256 records/producer-binaries.sha256
echo REUSED_VERIFIED_INCREMENTAL_BUILD > records/build-verdict.txt
curl -fsSL --retry 2 --max-time 120 https://github.com/foundry-rs/foundry/releases/download/v1.9.0/foundry_v1.9.0_linux_amd64.tar.gz -o "$RUNNER_TEMP/foundry.tgz"
echo "8d17599b42e3139f1a9c171be3798c4ed8e743ae17b84cc3435e57bf2a51ae99  $RUNNER_TEMP/foundry.tgz" | sha256sum -c
mkdir -p "$RUNNER_TEMP/foundry";tar -xzf "$RUNNER_TEMP/foundry.tgz" -C "$RUNNER_TEMP/foundry"
export PATH="$RUNNER_TEMP/foundry:$PATH"
forge --version | tee records/foundry.txt
forge build --root product/contrib/swapnet/contracts --skip test
anvil --port 18545 --slots-in-an-epoch 1 > records/anvil.log 2>&1 &
anvil_pid=$!;trap 'kill "$anvil_pid" 2>/dev/null || true; wait "$anvil_pid" || true' EXIT
sleep 2
mkdir -p baseline
(git -C product archive f08e0b4be0eea06152ad83e47311ff8907f9c25d contrib/swapnet | tar -x -C "$PWD/baseline")
py="$RUNNER_TEMP/evm-deps/bin/python"
set +e
PYTHONPATH="$PWD/baseline/contrib/swapnet:$PWD/baseline/contrib/swapnet/tests" timeout 3m "$py" -u ci/evm-cleanup/check.py "$RUNNER_TEMP/before" release > records/before.log 2>&1
before=$?
set -e
test "$before" = 1
for mode in release funded; do
 PYTHONPATH="$PWD/product/contrib/swapnet:$PWD/product/contrib/swapnet/tests" timeout 3m "$py" -u ci/evm-cleanup/check.py "$RUNNER_TEMP/after-$mode" "$mode" | tee "records/after-$mode.log"
done
python3 - <<'PY'
import json
from pathlib import Path
r=json.loads(Path('records/before.json').read_text());assert r['finalized_refund']['refunded'] and r['after_restart']['reservation']=='held' and int(r['after_restart']['held'])>0
print('NATIVE_EVM_BEFORE_AFTER_VERIFIED')
PY
