#!/usr/bin/env bash
set -euo pipefail
[[ "$(uname -sm)" == 'Linux x86_64' ]]
. /etc/os-release
[[ "$VERSION_ID" == '24.04' ]]
records="$GITHUB_WORKSPACE/records"
mkdir "$records"
root=$(mktemp -d /tmp/btx-s1-replace.XXXXXXXX)
export HOME="$root/home"
mkdir "$HOME" "$root/assets"
base=https://github.com/btxchain/btx/releases/download/v0.34.17
archive=btx-0.34.17-x86_64-linux-gnu.tar.gz
for file in "$archive" btx-release-manifest.json SHA256SUMS; do
    curl -fsSL --retry 2 --max-time 90 "$base/$file" -o "$root/assets/$file"
done
(
    cd "$root/assets"
    sha256sum -c - <<'SUMS'
e93be7a55b6f786ec0147aa7b02c06fdaf8e7a04dd1d748a47b2ccd9662a4d9d  btx-0.34.17-x86_64-linux-gnu.tar.gz
ed9787b6dff5b85686e7b9b2741c1c292a02484dd58188241e22f282756067f8  btx-release-manifest.json
392b3602d39568ce5e5e2512ba5dff59acecec1a50a99b41a4b548f1681fb623  SHA256SUMS
SUMS
    [[ "$(stat -c %s "$archive")" == 124582532 ]]
    jq -e '.source_commit == "932a0238c70705b28ea344a7929cee09ada314c8" and .signature_file == null' btx-release-manifest.json
    cp btx-release-manifest.json SHA256SUMS "$records/"
) | tee "$records/intake.log"
commit=932a0238c70705b28ea344a7929cee09ada314c8
curl -fsSL --max-time 45 "https://raw.githubusercontent.com/btxchain/btx/$commit/contrib/faststart/btx-agent-setup.py" -o "$root/installer.py"
# Use the installer’s returned paths, including its nested archive root.
install() {
    python3 -B "$root/installer.py" --release-manifest "$root/assets/btx-release-manifest.json" \
        --asset-base-url "$root/assets" --install-dir "$root/installed" --cache-dir "$root/cache" \
        --platform linux-x86_64 --allow-unsigned-release --no-start-daemon --json "$@"
}
install > "$records/install.json"
mkdir "$root/data"
port=$(python3 -c 'import socket; s=socket.socket(); s.bind(("127.0.0.1",0)); print(s.getsockname()[1])')
pid=
cleanup() {
    if [[ -n "$pid" ]] && kill -0 "$pid" 2>/dev/null; then
        kill -TERM "$pid" || true
        timeout 15s tail --pid="$pid" -f /dev/null || true
    fi
}
trap cleanup EXIT
start() {
    local stage=$1
    daemon=$(jq -er '.btxd' "$records/$stage.json")
    cli=("$(jq -er '.btx_cli' "$records/$stage.json")" -regtest -datadir="$root/data" -rpcport="$port" -rpcclienttimeout=3)
    [[ "$daemon" == "$root/installed/btx-0.34.17/bin/btxd" ]]
    [[ "${cli[0]}" == "$root/installed/btx-0.34.17/bin/btx-cli" ]]
    "$daemon" -regtest -datadir="$root/data" -rpcport="$port" -rpcbind=127.0.0.1 \
        -listen=0 -connect=0 -dnsseed=0 -discover=0 -natpmp=0 -modelnet=0 -swapnet=0 \
        > "$records/$stage-node.log" 2>&1 &
    pid=$!
    for ((attempt=0; attempt<40; attempt++)); do
        if "${cli[@]}" getblockchaininfo > "$records/$stage-ready.json" 2>/dev/null; then
            jq -e '.chain=="regtest"' "$records/$stage-ready.json" >/dev/null
            test "$(readlink "/proc/$pid/exe")" = "$root/installed/btx-0.34.17/libexec/btxd.real"
            return
        fi
        kill -0 "$pid"
        sleep 1
    done
    return 1
}
stop() {
    "${cli[@]}" stop
    timeout 30s tail --pid="$pid" -f /dev/null
    wait "$pid"
    pid=
}
start install
"${cli[@]}" -rpcclienttimeout=45 createwallet fixture > "$records/wallet.json"
addr=$("${cli[@]}" -rpcclienttimeout=30 -rpcwallet=fixture getnewaddress)
"${cli[@]}" -rpcclienttimeout=90 generatetoaddress 1 "$addr" > "$records/minted.json"
"${cli[@]}" getblockchaininfo > "$records/before.json"
jq -e '.blocks == 1 and (.bestblockhash | length == 64)' "$records/before.json" >/dev/null
stop
printf '%s\n' replacement-control > "$root/installed/local-replacement-marker"
install --force > "$records/replace.json"
test ! -e "$root/installed/local-replacement-marker"
start replace
"${cli[@]}" getblockchaininfo > "$records/after.json"
jq -e --slurp '.[0].blocks == .[1].blocks and .[0].bestblockhash == .[1].bestblockhash' \
    "$records/before.json" "$records/after.json" >/dev/null
stop
printf '%s\n' 'PASS replacement, same regtest tip, clean shutdown' | tee "$records/verdict.txt"
