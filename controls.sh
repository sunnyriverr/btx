#!/usr/bin/env bash
set -euo pipefail
out="$PWD/records"
mkdir "$out"
exec > >(tee "$out/controls.log") 2>&1
test "$(cat payload/source.txt)" = 88aeaac965f6ad0031aa6d8a062bfae23a45c4e0
(cd payload && sha256sum -c SHA256SUMS >/dev/null)
cp payload/SHA256SUMS "$out/"
chmod +x payload/bin/{btxd,btx-cli}
sudo apt-get install -y --no-install-recommends libevent-dev libsqlite3-0 libzmq5 python3
runtime_path=$(/usr/bin/python3 -I -c 'import sys; print(next(p for p in sys.path if p.startswith("/usr/local/") and p.endswith("/dist-packages")))')
sudo mkdir -p "$runtime_path"
sudo cp -a payload/python/. "$runtime_path/"
root=$(mktemp -d)
export HOME="$root/home"
mkdir -m 700 "$HOME" "$root/fresh" "$root/reuse"
node="$PWD/payload/bin/btxd"
cleanup() {
  if [[ -n "${pid:-}" ]] && kill -0 "$pid" 2>/dev/null; then
    kill -TERM "$pid"
    wait "$pid" || true
  fi
  rm -rf -- "$root"
}
trap cleanup EXIT
start() {
  local data=$1 enabled=$2 name=$3
  shift 3
  cli=("$PWD/payload/bin/btx-cli" -regtest "-datadir=$root/$data")
  "$node" -regtest "-datadir=$root/$data" -rpcbind=127.0.0.1 -listen=0 -connect=0 -dnsseed=0 -discover=0 "-swapnet=$enabled" "$@" > "$out/$name-node.log" 2>&1 &
  pid=$!
  timeout 30s "${cli[@]}" -rpcwait getblockchaininfo | jq -e '.chain=="regtest" and .blocks==0'
  test "$(readlink "/proc/$pid/exe")" = "$node"
}
swap_state() {
  local genesis
  genesis=$("${cli[@]}" getblockhash 0)
  "${cli[@]}" getswapnetworkinfo | tee "$out/$1-swapnet.json" | jq -e --arg genesis "$genesis" '.protocol==2 and .in_process==true and .automatic_spend_atoms=="0" and .network==$genesis'
  "${cli[@]}" listswaps | jq -e '.swaps==[]'
}
stop() {
  "${cli[@]}" stop
  timeout 30s tail --pid="$pid" -f /dev/null
  wait "$pid"
  pid=
}
start fresh 1 enabled_empty
swap_state enabled_empty
set +e
"${cli[@]}" -named createwallet wallet_name=swapnet_disposable descriptors=true > "$out/enabled-create.log" 2>&1
create_status=$?
set -e
echo "enabled wallet creation exit $create_status"
if (( create_status != 0 )); then
  grep -F 'Failed to configure serialized threading mode' "$out/enabled-create.log"
else
  jq -e '.name=="swapnet_disposable"' "$out/enabled-create.log"
fi
stop
echo SWAPNET_EMPTY_STARTUP_PASS
start reuse 0 disabled
"${cli[@]}" -named createwallet wallet_name=swapnet_disposable descriptors=true | jq -e '.name=="swapnet_disposable"'
"${cli[@]}" -rpcwallet=swapnet_disposable getwalletinfo | jq -e '.walletname=="swapnet_disposable" and .descriptors==true'
stop
echo WALLET_CREATION_DISABLED_PASS
start reuse 1 enabled_preloaded -wallet=swapnet_disposable -swapnetwallet=swapnet_disposable
swap_state enabled_preloaded
"${cli[@]}" -rpcwallet=swapnet_disposable getwalletinfo | jq -e '.walletname=="swapnet_disposable" and .descriptors==true'
stop
echo SWAPNET_PRELOADED_WALLET_PASS
