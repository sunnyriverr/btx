#!/usr/bin/env bash
set -euo pipefail
records="$GITHUB_WORKSPACE/records"
recipe="$GITHUB_WORKSPACE/proposal"
build="$GITHUB_WORKSPACE/gui-pilot-runtime/qtbuild"
retained="$GITHUB_WORKSPACE/retained-helper"
test -f "$records/dry-run-complete.txt"
test ! -s "$records/compiler-refusals.log"
cmp "$records/helper-before.sha256" "$records/helper-after.sha256"
test ! -e "$(readlink -f /usr/bin/gcc).preflight-real"
test ! -e "$(readlink -f /usr/bin/g++).preflight-real"
LC_ALL=C sed -nE 's/^\[[0-9]+\/[0-9]+\] (.*)$/\1/p' "$records/ninja-dry-run.log" |
    LC_ALL=C sort > "$records/actual-plan.txt"
cmp "$recipe/expected-plan.txt" "$records/actual-plan.txt"
test "$(wc -l < "$records/actual-plan.txt")" -eq 313
read -r free_kb < <(df -Pk "$build" | awk 'NR==2 {print $4}')
test "$free_kb" -gt 3145728
printf '%s\n' '313-action comparison passed' > "$records/build-gate.txt"
cd "$build"
timeout --kill-after=20s 40m /usr/local/bin/ninja -j3 btx-modeld 2>&1 | tee "$records/build.log"
test -x bin/btx-modeld
mkdir "$retained"
install -m 755 bin/btx-modeld "$retained/btx-modeld"
(cd "$retained" && sha256sum btx-modeld > SHA256SUMS && sha256sum -c SHA256SUMS)
test "$(cut -d " " -f 1 "$retained/SHA256SUMS")" != "$(cat "$records/helper-before.sha256")"
readelf -h -d "$retained/btx-modeld" > "$records/helper-elf.txt"
grep -q 'Advanced Micro Devices X86-64' "$records/helper-elf.txt"
cp "$retained/SHA256SUMS" "$records/built-helper.sha256"
printf '%s\n' 'c97c9a8d00ea37359b8691fd25c783725c1f4021' > "$retained/SOURCE"
cp "$retained/SOURCE" "$records/built-source.txt"
