#!/usr/bin/env bash
set -euo pipefail
export PATH="/opt/hostedtoolcache/Python/3.12.16/x64/bin:$PATH"
mkdir -p candidate
python3 component-build.py 2>&1 | tee pilot-records/component-tests.log
sha256sum candidate/component-checks > candidate/binaries.sha256
