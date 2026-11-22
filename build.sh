#!/usr/bin/env bash
set -euo pipefail

cmp expected-actions.txt records/planned-actions.txt
targets=(generate_shielded_relay_fixture_tx btxd btx-cli)
ninja -C mac-config-build -j2 "${targets[@]}" 2>&1 | tee records/targeted-build.log
stage=$(mktemp -d)
for name in gen_shielded_relay_fixture_tx btxd btx-cli; do
    bin="mac-config-build/bin/$name"
    test -x "$bin"
    test "$(lipo -archs "$bin")" = arm64
    otool -L "$bin" > "records/$name.dependencies.txt"
    cp -p "$bin" "$stage/"
done
git -C product rev-parse HEAD > "$stage/source.txt"
(
    cd "$stage"
    shasum -a 256 gen_shielded_relay_fixture_tx btxd btx-cli > SHA256SUMS
    shasum -a 256 -c SHA256SUMS
)
cp "$stage/SHA256SUMS" records/binaries.sha256
mkdir retained
tar -czf retained/mac-arm-7d65025b-shielded-fixture.tar.gz -C "$stage" .
(cd retained && shasum -a 256 mac-arm-7d65025b-shielded-fixture.tar.gz > SHA256SUMS)
