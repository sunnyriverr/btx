#!/usr/bin/env bash
set -euo pipefail
out="$PWD/records"
mkdir "$out"
exec > >(tee "$out/pilot.log") 2>&1
. /etc/os-release
test "$VERSION_ID" = 24.04
test "$(uname -m)" = x86_64
test "$(git -C product rev-parse HEAD)" = 5806b2d0eb1ec1cd65c64da5db8d8905ff9d1148
test -z "$(git -C product status --porcelain)"
df -h .
tmp=$(mktemp -d)
chmod 700 "$tmp"
cleanup() {
  if [[ -n "${pid:-}" ]] && kill -0 "$pid" 2>/dev/null; then
    kill -TERM "$pid"
    wait "$pid" || true
  fi
  rm -rf -- "$tmp"
}
trap cleanup EXIT
if [[ "${1:-}" != --configure-only ]]; then
cd "$tmp"
download() { curl -fsSL --retry 2 --max-time 90 "$1" -o "$2"; }
signers=https://raw.githubusercontent.com/bitcoin-core/guix.sigs/f432c43b5fbd6b8355daf36127acb7a73d0308b7
release=https://bitcoincore.org/bin/bitcoin-core-30.4
download "$signers/30.4/fanquake/all.SHA256SUMS" signed-sums
echo 'd1c70ff2bc5af4318c61323753528625a8cb46f518f1a769c5004afbbdf65426  signed-sums' | sha256sum -c
export GNUPGHOME="$tmp/gnupg"
mkdir -m 700 "$GNUPGHOME"
download "$signers/builder-keys/fanquake.gpg" fanquake.gpg
download "$signers/builder-keys/achow101.gpg" achow101.gpg
sha256sum -c <<'SUMS'
d9d6d89f5d9da0811ed94469f790d5bd0e185b7ee678e7ca7b3121995ded3d26  fanquake.gpg
1b31ab2e336d5ee44dd4d9f5703ad4445798fcee3b1352ab75afa145e737224a  achow101.gpg
SUMS
gpg --batch --import fanquake.gpg achow101.gpg
for signer in fanquake achow101; do
  download "$signers/30.4/$signer/all.SHA256SUMS.asc" "$signer.asc"
  gpg --batch --status-fd 1 --verify "$signer.asc" signed-sums | tee "$out/$signer-signature.log"
  grep -q '^\[GNUPG:\] VALIDSIG ' "$out/$signer-signature.log"
done
name=bitcoin-30.4-x86_64-linux-gnu.tar.gz
grep -Fx "051a18c595d9a27df23cb7187ff9fb343e90943cb142af751e12787806500c3d  $name" signed-sums
download "$release/$name" "$name"
grep -F "  $name" signed-sums | sha256sum -c
tar -xzf "$name" bitcoin-30.4/bin/{bitcoind,bitcoin-cli}
sha256sum -c <<'SUMS'
e4f5c68ea419820592a50a744040ab0c08f84fff5942ebe92eca21f5ccddcb5c  bitcoin-30.4/bin/bitcoind
d702d81f2f32d5c08a592b883f48a416f8e7df69ffa4400024ec5b815bb58f2f  bitcoin-30.4/bin/bitcoin-cli
SUMS
node="$tmp/bitcoin-30.4/bin/bitcoind"
cli=("$tmp/bitcoin-30.4/bin/bitcoin-cli" -regtest "-datadir=$tmp/data")
"$node" --version | sed -n '1p'
"${cli[@]}" --version | sed -n '1p'
mkdir -m 700 "$tmp/data"
"$node" -regtest "-datadir=$tmp/data" -rpcbind=127.0.0.1 -listen=0 -connect=0 -dnsseed=0 -discover=0 -disablewallet=1 > "$out/bitcoin-console.log" 2>&1 &
pid=$!
timeout 20s "${cli[@]}" -rpcwait getblockchaininfo | jq -e '{chain,blocks} | select(.chain=="regtest" and .blocks==0)' | tee "$out/bitcoin-chain.json"
"${cli[@]}" getblockhash 0 | tee "$out/bitcoin-genesis.txt"
grep -Fx 0f9188f13cb7b2c71f2a335e3a4fc328bf5beb436012afca590b1a11466e2206 "$out/bitcoin-genesis.txt"
"${cli[@]}" stop
timeout 20s tail --pid="$pid" -f /dev/null
wait "$pid"
pid=
echo BITCOIN_REGTEST_PASS
fi
cd "$GITHUB_WORKSPACE"
sudo apt-get -o Acquire::Retries=1 update
sudo apt-get install -y --no-install-recommends libboost-dev libevent-dev libsqlite3-dev libzmq3-dev python3-dev python3-venv ninja-build
/usr/bin/python3 -m venv "$tmp/python"
py="$tmp/python/bin/python3"
"$py" -m pip install --disable-pip-version-check --only-binary=:all: cryptography==46.0.4
"$py" -I -c 'import sys,sysconfig,sqlite3,cryptography; from cryptography.hazmat.primitives.ciphers.aead import AESGCM; print(sys.version, sysconfig.get_config_var("SOABI"), sqlite3.sqlite_version, cryptography.__version__)'
cmake -S product -B "$tmp/build" -G Ninja -DCMAKE_BUILD_TYPE=Release \
  -DBUILD_DAEMON=ON -DBUILD_CLI=ON -DENABLE_WALLET=ON -DWITH_SQLITE=ON \
  -DBUILD_GUI=OFF -DWITH_MODELNET=OFF -DBUILD_TESTS=OFF \
  "-DPython3_EXECUTABLE=$py" | tee "$out/configure.log"
grep -E '^(ENABLE_WALLET|WITH_SQLITE|WITH_MODELNET|BUILD_DAEMON|BUILD_CLI|Python3_EXECUTABLE|_Python3_(EXECUTABLE|LIBRARY_RELEASE|INCLUDE_DIR)):' "$tmp/build/CMakeCache.txt" | tee "$out/selected-config.txt"
grep -Fx 'ENABLE_WALLET:BOOL=ON' "$out/selected-config.txt"
grep -Fx 'WITH_SQLITE:BOOL=ON' "$out/selected-config.txt"
# Query the generated graph without triggering the CONFIGURE_DEPENDS glob check.
ninja -C "$tmp/build" -t commands btxd btx-cli > "$out/ninja-commands.log"
grep -m1 'generate_embedded.py' "$out/ninja-commands.log" | cut -c1-240
grep -m1 ' -o bin/btxd ' "$out/ninja-commands.log" | cut -c1-240
grep -m1 ' -o bin/btx-cli ' "$out/ninja-commands.log" | cut -c1-240
test ! -e "$tmp/build/bin/btxd"
test ! -e "$tmp/build/bin/btx-cli"
wc -l "$out/ninja-commands.log"
echo BTX_CONFIGURE_ONLY_PASS
