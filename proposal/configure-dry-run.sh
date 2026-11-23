#!/usr/bin/env bash
set -euo pipefail
records="$GITHUB_WORKSPACE/records"
build="$GITHUB_WORKSPACE/gui-pilot-runtime/qtbuild"
binaries=("$build/bin/btxd" "$build/bin/btx-cli")
test -f "$records/source-sync.json"
test "$(uname -m)" = x86_64
export BTX_OPENSSL="$GITHUB_WORKSPACE/gui-pilot-runtime/openssl/bin/openssl"
"$BTX_OPENSSL" version > "$records/openssl.log"
grep -q '^OpenSSL 3\.5\.9' "$records/openssl.log"
sha256sum --check "$GITHUB_WORKSPACE/proposal/retained-binaries.sha256"
sha256sum "${binaries[@]}" > "$records/binaries-before.sha256"
: > "$records/compiler-refusals.log"
export BTX_PILOT_COMPILER_LOG="$records/compiler-refusals.log"
for launcher in "$(readlink -f /usr/bin/gcc)" "$(readlink -f /usr/bin/g++)"; do
    mv "$launcher" "$launcher.preflight-real"
    cat > "$launcher" <<'COMPILER'
#!/usr/bin/env bash
set -euo pipefail
case "$*" in
    --version|-dumpmachine|-dumpversion|-dumpfullversion|-print-search-dirs|-print-sysroot)
        exec "$(readlink -f "$0").preflight-real" "$@"
        ;;
    *)
        printf '%s\n' "$0 $*" >> "$BTX_PILOT_COMPILER_LOG"
        exit 97
        ;;
esac
COMPILER
    chmod 755 "$launcher"
done

audit() {
    sha256sum "${binaries[@]}" > "$records/binaries-after.sha256"
    find "$build" -type f -name '*.o' -print0 | sort -z | xargs -0 -r sha256sum > "$records/objects-after.sha256"
}
find "$build" -type f -name '*.o' -print0 | sort -z | xargs -0 -r sha256sum > "$records/objects-before.sha256"
trap audit EXIT
timeout 240 /usr/local/bin/cmake -S "$GITHUB_WORKSPACE/product" -B "$build" \
    > "$records/configure.log" 2>&1 || { tail -65 "$records/configure.log"; exit 1; }
test ! -s "$records/compiler-refusals.log"
cd "$build"
timeout 120 /usr/local/bin/ninja -n -d explain btxd btx-cli > "$records/ninja-dry-run.log" 2>&1 \
    || { tail -65 "$records/ninja-dry-run.log"; exit 1; }
test ! -s "$records/compiler-refusals.log"
grep -q 'Linking CXX executable bin/btxd' "$records/ninja-dry-run.log"
! grep -q 'Re-running CMake' "$records/ninja-dry-run.log"
audit
cmp "$records/binaries-before.sha256" "$records/binaries-after.sha256"
cmp "$records/objects-before.sha256" "$records/objects-after.sha256"
test "$(wc -l < "$records/objects-after.sha256")" -eq 6001
trap - EXIT
printf '%s\n' 'configure and dry run complete' > "$records/dry-run-complete.txt"
