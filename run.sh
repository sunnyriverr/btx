#!/usr/bin/env bash
set -euo pipefail
mkdir -p records
exec > >(tee records/controller.log) 2>&1
test "$(uname -m)" = arm64
git -C product rev-parse HEAD | tee records/source.txt
test "$(cat records/source.txt)" = 7d65025bb3bff27e4f6c2fdc95f33e4b859a2df5
brew install --force-bottle python@3.12 openssl@3
PYTHON=/opt/homebrew/opt/python@3.12/bin/python3.12
"$PYTHON" -m pip install --only-binary=:all: --break-system-packages cryptography==46.0.4
"$PYTHON" -I -c 'from cryptography.hazmat.primitives.ciphers.aead import AESGCM'
"$PYTHON" -m venv "$RUNNER_TEMP/test-env"
"$RUNNER_TEMP/test-env/bin/python" -m pip install --only-binary=:all: cryptography==46.0.4 pyzmq==27.1.0
curl -fsSL --max-time 75 -H "Authorization: Bearer $GH_TOKEN" https://api.github.com/repos/sunnyriverr/btx/actions/artifacts/14736175464/zip -o "$RUNNER_TEMP/btx-fixtures.zip"
unset GH_TOKEN
export BTX_OPENSSL=/opt/homebrew/opt/openssl@3/bin/openssl
"$BTX_OPENSSL" version
"$RUNNER_TEMP/test-env/bin/python" run_cases.py "$RUNNER_TEMP/btx-fixtures.zip"
