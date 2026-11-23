#!/usr/bin/env bash
set -euo pipefail
root="$GITHUB_WORKSPACE"
tool=$(mktemp -d /tmp/pr939-tools.XXXXXX)
trap 'rm -rf -- "$tool"' EXIT
curl -fsSL --max-time 120 https://github.com/foundry-rs/foundry/releases/download/v1.9.0/foundry_v1.9.0_linux_amd64.tar.gz -o "$tool/foundry.tar.gz"
echo "8d17599b42e3139f1a9c171be3798c4ed8e743ae17b84cc3435e57bf2a51ae99  $tool/foundry.tar.gz" | sha256sum --check
tar -xzf "$tool/foundry.tar.gz" -C "$tool" anvil
echo "cc6b5239d4c0cacc6a5086619eee1e4a9ec6aa7a21bf1df631ebaa7816139d16  $tool/anvil" | sha256sum --check
"$tool/anvil" --version > "$root/records/anvil-version.txt"
sha256sum --check "$root/records/built-binaries.sha256"
py=/opt/hostedtoolcache/Python/3.12.16/x64/bin/python3
"$py" -m pip install --disable-pip-version-check pytest==8.4.2
export PYTHONPATH="$root/product/contrib/swapnet:$root/product/contrib/swapnet/tests"
export BTX_OPENSSL="$root/gui-pilot-runtime/openssl/bin/openssl"
target="$root/gui-pilot-runtime/qtbuild/bin"
timeout --kill-after=15s 180s "$py" -B "$root/proposal/native_case.py" \
    "$target/btxd" "$target/btx-cli" "$tool/anvil" "$root/proposal/SwapNetHTLC.json" candidate \
    2> "$root/records/native-case.stderr" | tee "$root/records/native-result.json"
