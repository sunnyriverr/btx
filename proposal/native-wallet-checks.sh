#!/usr/bin/env bash
set -euo pipefail
w="$GITHUB_WORKSPACE"
records="$w/records"
build="$w/gui-pilot-runtime/qtbuild"
python=/opt/hostedtoolcache/Python/3.12.16/x64/bin/python3
export BTX_OPENSSL="$w/gui-pilot-runtime/openssl/bin/openssl"
export BTXD="$build/bin/btxd" BTXCLI="$build/bin/btx-cli"
export BITCOIND="$BTXD" BITCOINCLI="$BTXCLI"
export PYTHONDONTWRITEBYTECODE=1
cp proposal/wallet_swapnet_relock.py "$w/product/test/functional/wallet_swapnet_relock.py"
scratch=$(mktemp -d)
trap 'rm -rf "$scratch"' EXIT
export HOME="$scratch/home"
mkdir -m 700 "$HOME"
timeout --kill-after=15s 600s "$python" -B "$w/product/test/functional/wallet_swapnet_relock.py" \
    --configfile="$build/test/config.ini" --tmpdir="$scratch/btx-data" --cachedir="$scratch/cache" \
    --descriptors --timeout-factor=3 2>&1 | tee "$records/native-btx.log"
grep -Fq 'Native named-wallet re-lock and both persistent locks verified' "$records/native-btx.log"
curl -fsSL --max-time 120 https://bitcoincore.org/bin/bitcoin-core-32.1/bitcoin-32.1-x86_64-linux-gnu.tar.gz -o "$scratch/core.tar.gz"
printf '%s  %s\n' 61545c17c3120fb7412f896d248b11993af04ec8817aad3649c55b2afb044963 "$scratch/core.tar.gz" | sha256sum --check
tar -xzf "$scratch/core.tar.gz" -C "$scratch" bitcoin-32.1/bin/bitcoind
core="$scratch/bitcoin-32.1/bin/bitcoind"
ldd "$core" | tee "$records/core.ldd"
if grep -q 'not found' "$records/core.ldd"; then exit 1; fi
PYTHONPATH="$w/product/contrib/swapnet" timeout --kill-after=15s 600s "$python" -B proposal/bitcoin-wallet.py "$core" | tee "$records/native-core.json"
grep -Fq '"result": "PASS"' "$records/native-core.json"
