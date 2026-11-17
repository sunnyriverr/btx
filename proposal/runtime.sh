#!/usr/bin/env bash
set -euo pipefail
. /etc/os-release
test "$VERSION_ID" = 22.04
test "$(uname -m)" = x86_64
export DEBIAN_FRONTEND=noninteractive
apt-get -o Acquire::Retries=1 update -qq
apt-get install -y -qq --no-install-recommends ca-certificates python3 libsqlite3-0 libgomp1
export BTX_OPENSSL="$GITHUB_WORKSPACE/gui-pilot-runtime/openssl/bin/openssl"
"$BTX_OPENSSL" version | tee records/openssl.log
ldd gui-pilot-runtime/qtbuild/bin/btx-modeld | tee records/helper-dependencies.log
if grep -q 'not found' records/helper-dependencies.log; then exit 1; fi
timeout --kill-after=20s 20m python3 -B proposal/observe.py --helper "$GITHUB_WORKSPACE/gui-pilot-runtime/qtbuild/bin/btx-modeld" --out "$GITHUB_WORKSPACE/records/native" --source-receipt "$GITHUB_WORKSPACE/proposal/source-receipt.json"
