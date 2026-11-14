#!/usr/bin/env bash
set -euo pipefail
mkdir -p records
sudo apt-get -o Acquire::Retries=1 update
sudo apt-get install -y --no-install-recommends libevent-dev libsqlite3-0 libzmq5 python3
(cd payload && sha256sum -c SHA256SUMS > ../records/checksums.log)
runtime_path=$(/usr/bin/python3 -I -c 'import sys; print(next(p for p in sys.path if p.startswith("/usr/local/") and p.endswith("/dist-packages")))')
sudo mkdir -p "$runtime_path"; sudo cp -a payload/python/. "$runtime_path/"
chmod +x payload/bin/{btxd,btx-cli}
/usr/bin/python3 -I -c 'import sqlite3,cryptography; from cryptography.hazmat.primitives.ciphers.aead import AESGCM; print(cryptography.__version__)' | tee records/runtime.txt
scratch=$(mktemp -d);trap 'rm -rf -- "$scratch"' EXIT
curl -fsSL --retry 2 --max-time 120 https://bitcoincore.org/bin/bitcoin-core-30.4/bitcoin-30.4-x86_64-linux-gnu.tar.gz -o "$scratch/core.tgz"
echo "051a18c595d9a27df23cb7187ff9fb343e90943cb142af751e12787806500c3d  $scratch/core.tgz" | sha256sum -c
tar -xzf "$scratch/core.tgz" -C "$scratch" bitcoin-30.4/bin/bitcoind
echo "e4f5c68ea419820592a50a744040ab0c08f84fff5942ebe92eca21f5ccddcb5c  $scratch/bitcoin-30.4/bin/bitcoind" | sha256sum -c
for case in restart refund; do
  mkdir -p "$scratch/$case/bitcoin-30.4/bin"
  cp "$scratch/bitcoin-30.4/bin/bitcoind" "$scratch/$case/bitcoin-30.4/bin/bitcoind"
  root="$PWD/records-$case"
  mkdir -p "$root"
  cp -a records/. "$root/"
  if ! timeout --signal=TERM --kill-after=30s 17m python3 -u ci/swapnet-funded/funded.py "$scratch/$case" "$case" 2>&1 | tee "funded-$case.log"; then
    cp -a records/. "$root/"
    exit 1
  fi
  cp -a records/. "$root/"
done
