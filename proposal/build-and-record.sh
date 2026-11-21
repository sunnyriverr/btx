#!/usr/bin/env bash
set -euo pipefail
records="$GITHUB_WORKSPACE/records"
recipe="$GITHUB_WORKSPACE/proposal"
build="$GITHUB_WORKSPACE/gui-pilot-runtime/qtbuild"
test -f "$records/dry-run-complete.txt"
test ! -s "$records/compiler-refusals.log"
cmp "$records/binaries-before.sha256" "$records/binaries-after.sha256"
cmp "$records/objects-before.sha256" "$records/objects-after.sha256"
LC_ALL=C sed -nE 's/^\[[0-9]+\/[0-9]+\] (.*)$/\1/p' "$records/ninja-dry-run.log" |
    LC_ALL=C sort > "$records/actual-plan.txt"
cmp "$recipe/expected-plan.txt" "$records/actual-plan.txt"
test "$(wc -l < "$records/actual-plan.txt")" -eq 17
for launcher in "$(readlink -f /usr/bin/gcc)" "$(readlink -f /usr/bin/g++)"; do
    test -x "$launcher.preflight-real"
    mv "$launcher.preflight-real" "$launcher"
done
test "$(df -Pk "$build" | awk 'NR==2 {print $4}')" -gt 8388608
export BTX_OPENSSL="$GITHUB_WORKSPACE/gui-pilot-runtime/openssl/bin/openssl"
printf '%s\n' '17-action plan matched' > "$records/build-started.txt"
start=$(date +%s)
set +e
timeout --kill-after=20s 12m /usr/local/bin/ninja -C "$build" -j2 btxd btx-cli 2>&1 | tee "$records/build.log"
codes=("${PIPESTATUS[@]}")
set -e
printf '%s\n' "${codes[0]}" > "$records/build-exit.txt"
printf '%s\n' "$(( $(date +%s) - start ))" > "$records/build-seconds.txt"
test "${codes[0]}" -eq 0
test "${codes[1]}" -eq 0
sha256sum "$build/bin/btxd" "$build/bin/btx-cli" > "$records/built-binaries.sha256"
for file in btxd btx-cli; do
    readelf -h -d "$build/bin/$file" > "$records/$file.elf.txt"
    grep -q 'Advanced Micro Devices X86-64' "$records/$file.elf.txt"
done
