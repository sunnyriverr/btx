#!/usr/bin/env bash
set -euo pipefail
export DEBIAN_FRONTEND=noninteractive
apt-get -o Acquire::Retries=1 update -qq
apt-get install -y -qq --no-install-recommends ca-certificates python3 libsqlite3-0 libgomp1
export BTX_OPENSSL="$GITHUB_WORKSPACE/gui-pilot-runtime/openssl/bin/openssl"
"$BTX_OPENSSL" version | tee records/openssl.log
ldd current-helper/btx-modeld | tee records/dependencies.log
if grep -q 'not found' records/dependencies.log; then exit 1; fi
timeout --kill-after=15s 300s python3 -B proposal/observe.py --helper "$GITHUB_WORKSPACE/current-helper/btx-modeld" --out "$GITHUB_WORKSPACE/records/native"
