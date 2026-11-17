#!/usr/bin/env bash
set -euo pipefail
. /etc/os-release
test "$VERSION_ID" = 22.04
export DEBIAN_FRONTEND=noninteractive
apt-get -o Acquire::Retries=1 update -qq
apt-get install -y -qq --no-install-recommends ca-certificates python3 libsqlite3-0 libgomp1
export BTX_OPENSSL="$GITHUB_WORKSPACE/gui-pilot-runtime/openssl/bin/openssl"
"$BTX_OPENSSL" version | tee records/openssl.log
ldd gui-pilot-runtime/qtbuild/bin/btx-modeld | tee records/helper-dependencies.log
if grep -q 'not found' records/helper-dependencies.log; then exit 1; fi
timeout --kill-after=15s 6m python3 -B proposal/native.py --helper "$GITHUB_WORKSPACE/gui-pilot-runtime/qtbuild/bin/btx-modeld" --helper-sha256 ddbdfdfacbbf305f1a4e85f9e2ffbabefb79e43e3c260452162b6a4d525e85bf --expect candidate --out "$GITHUB_WORKSPACE/records/candidate-native"
