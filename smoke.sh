#!/usr/bin/env bash
set -euo pipefail
out="$PWD/records"
exec > >(tee "$out/smoke.log") 2>&1
(cd payload && sha256sum -c SHA256SUMS >/dev/null)
root=$(mktemp -d)
chmod 700 "$root"
export HOME="$root/home"
mkdir -m 700 "$HOME" "$root/data"
node="$PWD/payload/bin/btxd"
cli=("$PWD/payload/bin/btx-cli" -regtest "-datadir=$root/data")
cleanup() {
  if [[ -n "${pid:-}" ]] && kill -0 "$pid" 2>/dev/null; then
    kill -TERM "$pid"
    wait "$pid" || true
  fi
  rm -rf -- "$root"
}
trap cleanup EXIT
"$node" -regtest "-datadir=$root/data" -rpcbind=127.0.0.1 -listen=0 -connect=0 -dnsseed=0 -discover=0 -swapnet=1 > "$out/node.log" 2>&1 &
pid=$!
timeout 30s "${cli[@]}" -rpcwait getblockchaininfo | jq -e '{chain,blocks} | select(.chain=="regtest" and .blocks==0)' | tee "$out/chain.json"
test "$(readlink "/proc/$pid/exe")" = "$node"
genesis=$("${cli[@]}" getblockhash 0)
"${cli[@]}" -named createwallet wallet_name=swapnet_disposable descriptors=true | jq -e '.name=="swapnet_disposable"'
"${cli[@]}" listwallets | jq -e '.==["swapnet_disposable"]'
"${cli[@]}" getswapnetworkinfo | tee "$out/swapnet.json" | jq -e --arg genesis "$genesis" '.protocol==2 and .in_process==true and .automatic_spend_atoms=="0" and .network==$genesis'
"${cli[@]}" listswaps | jq -e '.swaps==[]'
"${cli[@]}" stop
timeout 30s tail --pid="$pid" -f /dev/null
wait "$pid"
pid=
(cd payload && sha256sum -c SHA256SUMS >/dev/null)
echo SWAPNET_REGTEST_STARTUP_PASS
