#!/usr/bin/env bash
set -euo pipefail
export PATH="/opt/hostedtoolcache/Python/3.12.16/x64/bin:$PATH"
python3 -c "import json;r=json.load(open('pilot-records/result.json'));assert r['verdict']=='PREPARATION_PASS';print('HELPER BUILD PLAN ACTIONS',len(r['planned_step_lines']));assert len(r['planned_step_lines'])<=400"
timeout --kill-after=30s 30m cmake --build gui-pilot-runtime/qtbuild --parallel 2 --target btx-modeld > pilot-records/helper-build.log 2>&1
mkdir -p candidate
cp gui-pilot-runtime/qtbuild/bin/btx-modeld candidate/
sha256sum candidate/btx-modeld > candidate/binaries.sha256
