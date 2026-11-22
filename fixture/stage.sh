#!/usr/bin/env bash
set -euo pipefail
mkdir new old tools records
python3 -B fixture/stage.py
curl --fail --silent --show-error --location --max-time 120 \
  https://github.com/btxchain/btx/releases/download/v0.34.16/btx-0.34.16-x86_64-linux-gnu.tar.gz -o old-release.tar.gz
curl --fail --silent --show-error --location --max-time 120 \
  https://github.com/foundry-rs/foundry/releases/download/v1.9.0/foundry_v1.9.0_linux_amd64.tar.gz -o foundry.tar.gz
sha256sum --check <<'EOF'
9bbfff065299b3d6e863ecdeb0e54917788c1c0395cfa1d2b61bc40bf364932b  old-release.tar.gz
8d17599b42e3139f1a9c171be3798c4ed8e743ae17b84cc3435e57bf2a51ae99  foundry.tar.gz
EOF
tar -xzf old-release.tar.gz -C old
tar -xzOf foundry.tar.gz anvil > tools/anvil
chmod 700 new/btxd new/btx-cli tools/anvil
