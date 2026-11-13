#!/usr/bin/env bash
set -euo pipefail
mkdir -p records
sudo apt-get install -y --no-install-recommends libevent-dev libsqlite3-0 libzmq5 python3
runtime_path=$(/usr/bin/python3 -I -c 'import sys; print(next(p for p in sys.path if p.startswith("/usr/local/") and p.endswith("/dist-packages")))')
sudo mkdir -p "$runtime_path"
sudo cp -a payload/python/. "$runtime_path/"
chmod +x payload/bin/{btxd,btx-cli}
sha256sum -c payload/patch-sha256.txt
test "$(cat payload/source.txt)" = 88aeaac965f6ad0031aa6d8a062bfae23a45c4e0
(cd payload && sha256sum -c SHA256SUMS >/dev/null)
cp payload/{SHA256SUMS,source.txt} records/
scratch=$(mktemp -d)
trap 'rm -rf -- "$scratch"' EXIT
curl -fsSL --retry 2 --max-time 90 https://bitcoincore.org/bin/bitcoin-core-30.4/bitcoin-30.4-x86_64-linux-gnu.tar.gz -o "$scratch/bitcoin.tar.gz"
echo "051a18c595d9a27df23cb7187ff9fb343e90943cb142af751e12787806500c3d  $scratch/bitcoin.tar.gz" | sha256sum -c
tar -xzf "$scratch/bitcoin.tar.gz" -C "$scratch" bitcoin-30.4/bin/bitcoind
echo "e4f5c68ea419820592a50a744040ab0c08f84fff5942ebe92eca21f5ccddcb5c  $scratch/bitcoin-30.4/bin/bitcoind" | sha256sum -c
timeout --signal=TERM --kill-after=40s 17m /usr/bin/python3 -u settle.py "$scratch" "$1" 2>&1 | tee records/harness.log
