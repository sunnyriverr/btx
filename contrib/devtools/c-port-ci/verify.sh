#!/usr/bin/env bash
set -euo pipefail

candidate=$(git rev-parse HEAD)
base=$(git rev-parse HEAD^)
python3 -B test/lint/test_posix_portability.py -v
COMMIT_RANGE="$base..$candidate" python3 -B test/lint/lint-posix-portability.py
printf 'Clean release-range gate passed: %s..%s\n' "$base" "$candidate"

driver=$(cd "$(dirname "$1")" && pwd)/$(basename "$1")
case_root=$(mktemp -d)
trap 'rm -rf "$case_root"' EXIT
mkdir -p "$case_root/repo/test/lint" "$case_root/repo/src"
cp test/lint/{lint-posix-portability.py,lint_ignore_dirs.py} "$case_root/repo/test/lint/"
cd "$case_root/repo"
git init -q
git config user.name 'BTX lint test'
git config user.email lint-test@example.invalid
git config commit.gpgsign false
# The matched fixture uses the actual daemon guard idiom and a declaration
# available on the POSIX target alone. Windows preprocessing needs no SDK.
cat > src/bitcoind.cpp <<'CPP'
#ifndef _WIN32
extern "C" int fork();
#endif
CPP
git add src
git commit -qm base
fixture_base=$(git rev-parse HEAD)

check() {
    local expected=$1 label=$2
    COMMIT_RANGE="$fixture_base..HEAD" bash "$driver" /usr/bin/true "$case_root/$label"
    grep -E "^lint-posix-portability\.py[[:space:]]+$expected[[:space:]]" "$case_root/$label/lint-results.tsv"
    cat "$case_root/$label/logs/lint-posix-portability.py.log"
}

cat >> src/bitcoind.cpp <<'CPP'
#ifndef WIN32
int launch() { return ::fork(); }
#endif
CPP
git add src
git commit -qm guarded
check pass guarded
for target in x86_64-pc-windows-msvc x86_64-w64-windows-gnu; do
    clang++ --target="$target" -DWIN32 -fsyntax-only src/bitcoind.cpp
    printf 'Guarded compile passed: %s\n' "$target"
done

sed -e '/^#ifndef WIN32$/d' -e '$d' src/bitcoind.cpp > "$case_root/unguarded.cpp"
cp "$case_root/unguarded.cpp" src/bitcoind.cpp
git add src
git commit -qm unguarded
check fail unguarded
grep -Fx 'src/bitcoind.cpp:4: POSIX call reachable on Windows: fork' \
    "$case_root/unguarded/logs/lint-posix-portability.py.log"
for target in x86_64-pc-windows-msvc x86_64-w64-windows-gnu; do
    if clang++ --target="$target" -DWIN32 -fsyntax-only src/bitcoind.cpp > "$case_root/compile.log" 2>&1; then
        printf 'Expected the unguarded compile to fail: %s\n' "$target" >&2
        exit 1
    fi
    grep -E "undeclared identifier 'fork'|no member named 'fork' in (the )?global namespace" "$case_root/compile.log"
    printf 'Unguarded compile failed as expected: %s\n' "$target"
done
