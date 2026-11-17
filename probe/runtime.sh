#!/usr/bin/env bash
set -euo pipefail
. /etc/os-release
test "$VERSION_ID" = 22.04
export DEBIAN_FRONTEND=noninteractive
apt-get -o Acquire::Retries=1 update -qq
apt-get install -y -qq --no-install-recommends ca-certificates python3 libevent-2.1-7 libevent-pthreads-2.1-7 libzmq5 libgomp1 libsqlite3-0
export BTX_OPENSSL="$GITHUB_WORKSPACE/gui-pilot-runtime/openssl/bin/openssl"
"$BTX_OPENSSL" version | tee records/openssl.log
ldd gui-pilot-runtime/qtbuild/bin/btx-modeld | tee records/helper-dependencies.log
if grep -q 'not found' records/helper-dependencies.log; then exit 1; fi
python3 -B probe/offline.py
# No compiler, no node, no wallet, and no peer listeners.
timeout --kill-after=15s 6m python3 -B probe/run.py --helper "$GITHUB_WORKSPACE/gui-pilot-runtime/qtbuild/bin/btx-modeld" --helper-sha256 7f536bfc4447dbb4a437dd603d1172049f9d21b8dfe9a88a5d4e8313ca616898 --out "$GITHUB_WORKSPACE/records/native"
