#!/usr/bin/env bash
set -euo pipefail
[[ "$(uname -sm)" == 'Linux x86_64' ]]
mkdir -p records
scratch=$(mktemp -d)
trap 'rm -rf -- "$scratch"' EXIT
df -h "$scratch" > records/disk.txt
[[ "$(df -Pk "$scratch" | awk 'NR==2{print $4}')" -ge 2097152 ]]
archive=btx-0.34.17-x86_64-linux-gnu.tar.gz
foundry=foundry_v1.9.0_linux_amd64.tar.gz
curl -fsSL --retry 1 --max-time 120 "https://github.com/btxchain/btx/releases/download/v0.34.17/$archive" -o "$scratch/$archive"
curl -fsSL --retry 1 --max-time 120 "https://github.com/foundry-rs/foundry/releases/download/v1.9.0/$foundry" -o "$scratch/$foundry"
(
  cd "$scratch"
  sha256sum --check <<SUMS
5b1a62706466f1ab42ca36309b7c63653c8aeb8d57acb86a406240596e02b256  $archive
8d17599b42e3139f1a9c171be3798c4ed8e743ae17b84cc3435e57bf2a51ae99  $foundry
SUMS
  tar -xzf "$archive"
  tar -xzf "$foundry" anvil
  echo 'cc6b5239d4c0cacc6a5086619eee1e4a9ec6aa7a21bf1df631ebaa7816139d16  anvil' | sha256sum --check
) | tee records/verified-inputs.txt
target="$scratch/btx-0.34.17/bin"
test -x "$target/btxd"
test -x "$target/btx-cli"
"$target/btxd" -version > records/btxd-version.txt
"$target/btx-cli" -version > records/btx-cli-version.txt
grep -F 'v0.34.17' records/btxd-version.txt
python3 - "$scratch/btx-0.34.17/libexec/btxd.real" <<'PYTHON'
import sys
from pathlib import Path
assert b'18d0b7ff5337' in Path(sys.argv[1]).read_bytes()
print('Published daemon contains 18d0b7ff5337')
PYTHON
"$scratch/anvil" --version > records/anvil-version.txt
python3 -m venv "$scratch/py"
py="$scratch/py/bin/python"
"$py" -m pip install --disable-pip-version-check pytest==8.4.2 cryptography==44.0.3
commit=18d0b7ff5337c2768f5f5e06c674d8c8898bedad
curl -fsSL --max-time 120 "https://codeload.github.com/btxchain/btx/tar.gz/$commit" -o "$scratch/source.tar.gz"
tar -xzf "$scratch/source.tar.gz" -C "$scratch" "btx-$commit/contrib/swapnet"
source_root="$scratch/btx-$commit/contrib/swapnet"
export PYTHONPATH="$source_root:$source_root/tests"
timeout --kill-after=15s 180s "$py" -B native_case.py \
  "$target/btxd" "$target/btx-cli" "$scratch/anvil" SwapNetHTLC.json candidate \
  2>records/native-stderr.txt | tee records/native-result.json
