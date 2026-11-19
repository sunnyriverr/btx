#!/usr/bin/env bash
set -euo pipefail
export BTX_OPENSSL="$GITHUB_WORKSPACE/gui-pilot-runtime/openssl/bin/openssl"
"$BTX_OPENSSL" version | tee records/openssl-qualification.log
grep -q '^OpenSSL 3\.5\.9' records/openssl-qualification.log
(cd retained-helper && sha256sum -c SHA256SUMS)
expected="$(cut -d ' ' -f1 retained-helper/SHA256SUMS)"
ldd retained-helper/btx-modeld | tee records/dependencies.log
! grep -q 'not found' records/dependencies.log
set +e
timeout --kill-after=15s 300s python3 -B proposal/observe-alias-save.py \
    --helper "$GITHUB_WORKSPACE/retained-helper/btx-modeld" --expected-helper-sha256 "$expected" \
    --out "$GITHUB_WORKSPACE/records/native"
status=$?
set -e
printf '%s\n' "$status" > records/fixture-exit.txt
test "$status" -eq 0
