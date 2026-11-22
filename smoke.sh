#!/usr/bin/env bash
set -euo pipefail
export LC_ALL=C
. /etc/os-release
test "$ID" = debian
test "$VERSION_ID" = 13
test "$(uname -m)" = x86_64
{
  echo "OS=$PRETTY_NAME"
  uname -smr
  getconf GNU_LIBC_VERSION
  dpkg-query -W libc6 libstdc++6
} | tee /receipt/platform.txt

scratch=$(mktemp -d)
export HOME="$scratch/home"
mkdir "$HOME" "$scratch/data"
pid=
cleanup() {
  if [[ -n "$pid" ]]; then
    kill -TERM "$pid" 2>/dev/null || return 0
    for ((i=0; i<8; i++)); do
      kill -0 "$pid" 2>/dev/null || break
      sleep 1
    done
    if kill -0 "$pid" 2>/dev/null; then kill -KILL "$pid"; fi
    wait "$pid" 2>/dev/null || true
  fi
}
trap cleanup EXIT
tar -xzf /input/btx-0.34.17-x86_64-linux-gnu.tar.gz -C "$scratch"
cd "$scratch/btx-0.34.17"
sha256sum bin/btxd bin/btx-cli > /receipt/entry-points.sha256
timeout 12s bin/btxd -version > /receipt/btxd-version.txt 2>&1
timeout 12s bin/btx-cli -version > /receipt/btx-cli-version.txt 2>&1
grep -m1 'v0.34.17' /receipt/btxd-version.txt
grep -m1 'v0.34.17' /receipt/btx-cli-version.txt

datadir="$scratch/data"
bin/btxd -regtest -datadir="$datadir" -daemon=0 -server=1 -listen=0 \
  -dnsseed=0 -discover=0 -connect=0 -printtoconsole=1 \
  > /receipt/btxd.log 2>&1 &
pid=$!
cli=(bin/btx-cli -regtest -datadir="$datadir")
ready=false
for ((i=0; i<45; i++)); do
  if ! kill -0 "$pid" 2>/dev/null; then
    wait "$pid" && echo 'Daemon exited before RPC' >&2
    exit 1
  fi
  if timeout 3s "${cli[@]}" getblockchaininfo > /receipt/getblockchaininfo.json 2> /receipt/rpc.err; then
    ready=true
    break
  fi
  sleep 1
done
if [[ "$ready" != true ]]; then
  echo 'Regtest RPC did not become ready in the bounded window' >&2
  exit 1
fi
grep -Eq '"chain"[[:space:]]*:[[:space:]]*"regtest"' /receipt/getblockchaininfo.json
readlink "/proc/$pid/exe" > /receipt/daemon-exe.txt
awk '$6 ~ /^\// {print $6}' "/proc/$pid/maps" | sort -u > /receipt/daemon-mapped-files.txt
timeout 10s "${cli[@]}" stop > /receipt/stop.txt 2> /receipt/stop.err
for ((i=0; i<45; i++)); do
  kill -0 "$pid" 2>/dev/null || break
  sleep 1
done
if kill -0 "$pid" 2>/dev/null; then
  echo 'Daemon did not exit after RPC stop' >&2
  exit 1
fi
wait "$pid"
printf 'daemon_exit=0\n' > /receipt/shutdown.txt
printf 'pid=%s absent_after_wait=true\n' "$pid" >> /receipt/shutdown.txt
pid=
grep -E 'Shutdown: (done|In progress)' /receipt/btxd.log | tail -5
echo 'PASS: regtest RPC and clean shutdown' | tee /receipt/verdict.txt
