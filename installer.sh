#!/usr/bin/env bash
set -euo pipefail
out="$PWD/installer-records"
mkdir "$out"
exec > >(tee "$out/installer.log") 2>&1
root=$(mktemp -d)
export HOME="$root/home" BTX_INSTALL_ROOT="$root/updater" BTX_LINK_DIR="$root/links" BTX_CACHE_ROOT="$root/cache"
mkdir "$HOME" "$root/extract" "$root/data"
node=
stop() {
  if [[ -n "$node" ]] && kill -0 "$node" 2>/dev/null; then
    timeout 6s "$root/installed/bin/btx-cli" -regtest -datadir="$root/data" -rpcport="$port" stop || true
  fi
}
trap stop EXIT
archive=candidate-input/btx-linux-gui-candidate.tar.gz
echo '7d9dab78797d6c4e9668d92d65fb909f218b256760e565345089a1bbbd724fc5  '"$archive" | sha256sum --check
python3 - "$archive" "$root/extract" <<'PY'
import sys, tarfile
with tarfile.open(sys.argv[1]) as archive:
    archive.extractall(sys.argv[2], filter='data')
PY
source accepted-source/contrib/autoupdate/install.sh
install_prebuilt_release_tree "$root/extract/btx-0.34.16/bin" 0.34.16 "$root/installed" linux-x86_64 'https://github.com/sunnyriverr/btx/actions/runs/43428864330/artifacts/14040930895' 88c9b49cb16360fc8fbf3f84003b8b54c29e6db5
port=$(python3 -c 'import socket;s=socket.socket();s.bind(("127.0.0.1",0));print(s.getsockname()[1])')
"$root/installed/bin/btxd" -regtest -datadir="$root/data" -rpcport="$port" -rpcbind=127.0.0.1 -listen=0 -connect=0 -dnsseed=0 -discover=0 -natpmp=0 -disablewallet=1 -modelnet=0 > "$out/node.log" 2>&1 &
node=$!
cli=("$root/installed/bin/btx-cli" -regtest -datadir="$root/data" -rpcport="$port")
for i in {1..45}; do
 if "${cli[@]}" getblockchaininfo > "$out/rpc.json" 2>/dev/null; then break; fi
 kill -0 "$node"
 sleep 1
done
jq -e '.chain=="regtest" and .blocks==0' "$out/rpc.json"
test "$(readlink "/proc/$node/exe")" = "$root/installed/libexec/btxd.real"
"${cli[@]}" stop
timeout 30s tail --pid="$node" -f /dev/null
wait "$node"
node=
rm -rf -- "$root"
echo 'PASS installed launcher, installed binary identity, regtest RPC, clean shutdown and cleanup'
