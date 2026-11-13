#!/usr/bin/env bash
set -euo pipefail
out="$PWD/records"
mkdir -p "$out"
exec > >(tee "$out/controls.log") 2>&1
case "${1:?}" in
  baseline) source=88aeaac965f6ad0031aa6d8a062bfae23a45c4e0 ;;
  candidate) source=8d6d8b1aabf371b12f2b1f5797b950fed7962d4e
             sha256sum -c payload/patch-sha256.txt ;;
  *) exit 2 ;;
esac
test "$(cat payload/source.txt)" = "$source"
cp payload/source.txt "$out/"
(cd payload && sha256sum -c SHA256SUMS >/dev/null)
cp payload/SHA256SUMS "$out/"
chmod +x payload/bin/{btxd,btx-cli}
sudo apt-get install -y --no-install-recommends libevent-dev libsqlite3-0 libzmq5 python3
ext=$(/usr/bin/python3 -I -c 'import _sqlite3; print(_sqlite3.__file__)')
ldd "$ext" > "$out/python-sqlite-ldd.txt"
ldd payload/bin/btxd > "$out/btxd-ldd.txt"
for f in python-sqlite btxd; do
  awk '$1 ~ /^libsqlite3[.]so/ {print $3}' "$out/$f-ldd.txt" | xargs -r realpath > "$out/$f-sqlite-path.txt"
  test -s "$out/$f-sqlite-path.txt"
done
cmp "$out/python-sqlite-sqlite-path.txt" "$out/btxd-sqlite-path.txt"
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

wallet=swapnet_disposable
create_wallet() {
  "${cli[@]}" -named createwallet wallet_name="$wallet" descriptors=true load_on_startup=false
}
wallet_lifecycle() {
  local address
  address=$("${cli[@]}" -rpcwallet="$wallet" getnewaddress lifecycle)
  "${cli[@]}" -named unloadwallet wallet_name="$wallet" load_on_startup=false
  "${cli[@]}" listwallets | jq -e '.==[]'
  if [[ $1 == enabled ]]; then
    swap_state after_unload
    local genesis expiry
    genesis=$("${cli[@]}" getblockhash 0)
    expiry=$(($(date +%s) + 600))
    local mandate
    mandate=$(jq -nc --arg asset "btx:$genesis:0:native" --argjson expiry "$expiry" --arg nonce "$(printf '%064d' 1)" '{mandate:{principal:"owner:cookie",asset:$asset,max_total_atoms:"1",max_trade_atoms:"1",max_fee_atoms:"0",expires_at:$expiry,nonce:$nonce}}')
    "${cli[@]}" createswapmandate "$mandate" | jq -e '.mandate_id | length==64'
    "${cli[@]}" getswaphealth | jq -e '.database_schema==2 and (.last_tick_error==null or .last_tick_error=="")'
  fi
  "${cli[@]}" -named loadwallet filename="$wallet" load_on_startup=false | jq -e --arg wallet "$wallet" '.name==$wallet'
  "${cli[@]}" -rpcwallet="$wallet" getaddressinfo "$address" | jq -e '.ismine==true and (.labels|index("lifecycle")!=null)'
}
start fresh 1 enabled_empty
swap_state enabled_empty
set +e
create_wallet > "$out/enabled-create.log" 2>&1
status=$?
set -e
if [[ $1 == baseline ]]; then
  test "$status" -ne 0
  grep -F 'Failed to configure serialized threading mode' "$out/enabled-create.log"
  echo EXPECTED_FIRST_WALLET_FAILURE
else
  if (( status != 0 )); then cat "$out/enabled-create.log"; exit "$status"; fi
  jq -e --arg wallet "$wallet" '.name==$wallet' "$out/enabled-create.log"
  wallet_lifecycle enabled
  swap_state after_reopen
  echo ENABLED_WALLET_LIFECYCLE_PASS
fi
stop

start reuse 0 disabled
create_wallet | jq -e --arg wallet "$wallet" '.name==$wallet'
wallet_lifecycle disabled
if "${cli[@]}" getswapnetworkinfo > "$out/disabled-swapnet.log" 2>&1; then exit 1; fi
grep -F 'SwapNet is disabled' "$out/disabled-swapnet.log"
stop
echo DISABLED_WALLET_LIFECYCLE_PASS
start reuse 1 enabled_preloaded -wallet="$wallet" -swapnetwallet="$wallet"
swap_state enabled_preloaded
"${cli[@]}" -rpcwallet="$wallet" getwalletinfo | jq -e --arg wallet "$wallet" '.walletname==$wallet and .descriptors==true'
stop
echo PRELOADED_STARTUP_PASS
