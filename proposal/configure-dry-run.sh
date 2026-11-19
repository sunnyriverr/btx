#!/usr/bin/env bash
set -euo pipefail
records="$GITHUB_WORKSPACE/records"
build="$GITHUB_WORKSPACE/gui-pilot-runtime/qtbuild"
helper="$build/bin/btx-modeld"
test -f "$records/source-sync.json"
test "$(uname -m)" = x86_64
export BTX_OPENSSL="$GITHUB_WORKSPACE/gui-pilot-runtime/openssl/bin/openssl"
"$BTX_OPENSSL" version > "$records/openssl.log"
grep -q '^OpenSSL 3\.5\.9' "$records/openssl.log"
sha256sum "$helper" | awk '{print $1}' > "$records/helper-before.sha256"
: > "$records/compiler-refusals.log"
export BTX_PILOT_COMPILER_LOG="$records/compiler-refusals.log"
launchers=("$(readlink -f /usr/bin/gcc)" "$(readlink -f /usr/bin/g++)")
finish() {
    for launcher in "${launchers[@]}"; do
        if test -f "$launcher.preflight-real"; then mv -f "$launcher.preflight-real" "$launcher"; fi
    done
    sha256sum "$helper" | awk '{print $1}' > "$records/helper-after.sha256"
}
trap finish EXIT
for launcher in "${launchers[@]}"; do
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
timeout 240 /usr/local/bin/cmake -S "$GITHUB_WORKSPACE/product" -B "$build" \
    > "$records/configure.log" 2>&1 || { tail -65 "$records/configure.log"; exit 1; }
test ! -s "$records/compiler-refusals.log"
cd "$build"
timeout 120 /usr/local/bin/ninja -n -d explain btx-modeld > "$records/ninja-dry-run.log" 2>&1 \
    || { tail -65 "$records/ninja-dry-run.log"; exit 1; }
test ! -s "$records/compiler-refusals.log"
grep -q 'Linking CXX executable bin/btx-modeld' "$records/ninja-dry-run.log"
printf '%s\n' 'configure and dry run complete' > "$records/dry-run-complete.txt"
