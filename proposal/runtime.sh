#!/usr/bin/env bash
set -euo pipefail
export BTX_OPENSSL="$GITHUB_WORKSPACE/gui-pilot-runtime/openssl/bin/openssl"
"$BTX_OPENSSL" version | tee records/openssl.log
grep -q '^OpenSSL 3\.5\.9' records/openssl.log
ldd current-helper/btx-modeld | tee records/dependencies.log
! grep -q 'not found' records/dependencies.log
expected=56c2dd1f00a5d89035b60cc600879e98604c45d1dcbffcdf59bcfccf553c9191
set +e
timeout --kill-after=15s 300s python3 -B proposal/observe-alias-save.py \
    --helper "$GITHUB_WORKSPACE/current-helper/btx-modeld" --expected-helper-sha256 "$expected" \
    --out "$GITHUB_WORKSPACE/records/native"
exit_status=$?
set -e
printf '%s\n' "$exit_status" > records/fixture-exit.txt
test "$exit_status" -eq 0 || test "$exit_status" -eq 2
test -s records/native/result.json
