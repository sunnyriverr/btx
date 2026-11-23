#!/usr/bin/env bash
set -euo pipefail
records="$GITHUB_WORKSPACE/records"
build="$GITHUB_WORKSPACE/gui-pilot-runtime/qtbuild"
test -f "$records/dry-run-complete.txt"
test ! -s "$records/compiler-refusals.log"
cmp "$records/binaries-before.sha256" "$records/binaries-after.sha256"
cmp "$records/objects-before.sha256" "$records/objects-after.sha256"
LC_ALL=C sed -nE 's/^\[[0-9]+\/[0-9]+\] (.*)$/\1/p' "$records/ninja-dry-run.log" > "$records/actual-plan.txt"
steps=$(wc -l < "$records/actual-plan.txt")
test "$steps" -gt 0
test "$steps" -le 90
grep -q 'Generating swapnet-generated/swapnet/frozen_sources.h' "$records/actual-plan.txt"
grep -q 'Linking CXX executable bin/btxd' "$records/actual-plan.txt"
for launcher in "$(readlink -f /usr/bin/gcc)" "$(readlink -f /usr/bin/g++)"; do
    test -x "$launcher.preflight-real"
    mv "$launcher.preflight-real" "$launcher"
done
test "$(df -Pk "$build" | awk 'NR==2 {print $4}')" -gt 8388608
export BTX_OPENSSL="$GITHUB_WORKSPACE/gui-pilot-runtime/openssl/bin/openssl"
printf '%s\n' "$steps admitted build actions" > "$records/build-started.txt"
set +e
timeout --kill-after=20s 12m /usr/local/bin/ninja -C "$build" -j2 btxd btx-cli 2>&1 | tee "$records/build.log"
codes=("${PIPESTATUS[@]}")
set -e
printf '%s\n' "${codes[0]}" > "$records/build-exit.txt"
test "${codes[0]}" -eq 0
test "${codes[1]}" -eq 0
sha256sum "$build/bin/btxd" "$build/bin/btx-cli" > "$records/built-binaries.sha256"
