#!/usr/bin/env bash
set -euo pipefail
export PATH="/opt/hostedtoolcache/Python/3.12.16/x64/bin:$PATH"
python3 -c "import json;r=json.load(open('pilot-records/result.json'));assert r['verdict']=='PREPARATION_PASS';print('HELPER BUILD PLAN ACTIONS',len(r['planned_step_lines']));assert len(r['planned_step_lines'])<=400"
timeout --kill-after=30s 40m cmake --build gui-pilot-runtime/qtbuild --parallel 4 --target btx-modeld 2>&1 | tee pilot-records/helper-build.log
mkdir -p candidate
cp gui-pilot-runtime/qtbuild/bin/btx-modeld candidate/
sha256sum candidate/btx-modeld > candidate/binaries.sha256

python3 component-build.py 2>&1 | tee pilot-records/component-tests.log
# Retain the newly compiled helper cache so later connected checks need not repeat compilation.
python3 - <<'PY2'
from checkpoint import create
from pathlib import Path
import os
w=Path(os.environ['GITHUB_WORKSPACE'])
create(w,w/'resume-checkpoint',{'source':'3a9effab0b623c1a6cc19257ecd0ddf936185a20','purpose':'cloud resume helper build'})
PY2
