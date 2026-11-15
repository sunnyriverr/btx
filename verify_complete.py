"""Run actual matrix dispatch against complete tracked candidate scanner inputs.

Only unrelated lint commands and dependency bootstrap are bypassed. Source
membership and checker inputs are real; both mutable inputs are restored even
when a check fails. Reuse the verified complete-source snapshot.
"""
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / 'complete-source'
PYTHON = Path(os.environ.get('BTX_LINT_PYTHON') or shutil.which('python3.11') or sys.executable).resolve()
assert subprocess.check_output([str(PYTHON), '-c', 'import sys; print(sys.version_info[:2])'], text=True).strip() == '(3, 11)'
SCRIPT = SOURCE / 'scripts/ci/run_ci_target.sh'
LIST = SOURCE / 'src/test/fuzz/rpc.cpp'
CHECKER = 'test/lint/lint-rpc-fuzz-lists.py'
original_script = SCRIPT.read_bytes()
original_list = LIST.read_bytes()
assert original_list.count(b'"getblockcount",') == 1
broken = original_list.replace(b'"getblockcount",', b'', 1)
venv = SOURCE / '.ci-lint-venv311'
(venv / 'bin').mkdir(parents=True, exist_ok=True)
version = re.search(r'local deps_version="([^"]+)"', original_script.decode()).group(1)
(venv / '.deps-version').write_text(version)
wrapper = venv / 'bin/python3'
wrapper.write_text('#!/bin/bash\nprintf "%s\\n" "$1" >> "$DISPATCH_TRACE"\n'
                   'if [[ "$1" == "' + CHECKER + '" ]]; then\n'
                   'exec ' + shlex.quote(str(PYTHON)) + ' "$@"\nfi\nexit 0\n')
wrapper.chmod(0o755)
alias = venv / 'bin/python3.11'
if not alias.exists():
    alias.symlink_to(PYTHON)
env = dict(os.environ, PATH=str(venv / 'bin') + ':' + os.environ['PATH'], PYTHONDONTWRITEBYTECODE='1')
rows = []
try:
    for flavor in ('baseline', 'candidate'):
        script = (ROOT / flavor / 'scripts/ci/run_ci_target.sh').read_bytes()
        SCRIPT.write_bytes(script)
        for case, data in [('clean', original_list), ('missing', broken), ('restored', original_list)]:
            LIST.write_bytes(data)
            trace = SOURCE / 'trace.txt'
            trace.write_text('')
            run = subprocess.run(['/bin/bash', 'scripts/ci/run_ci_target.sh', 'lint'], cwd=SOURCE,
                                 env=dict(env, DISPATCH_TRACE=str(trace)), capture_output=True,
                                 text=True, timeout=180)
            (ROOT / ('complete-dispatch-' + flavor + '-' + case + '.log')).write_text(run.stdout + run.stderr)
            calls = trace.read_text().splitlines()
            must_fail = flavor == 'candidate' and case == 'missing'
            assert (run.returncode != 0) == must_fail, (flavor, case, run.stdout, run.stderr)
            assert calls.count(CHECKER) == (1 if flavor == 'candidate' else 0)
            if must_fail:
                assert '"getblockcount"' in run.stdout and 'registered but in neither' in run.stdout
                assert calls[-1] == CHECKER
            row = {'flavor': flavor, 'case': case, 'exit': run.returncode,
                   'checker_calls': calls.count(CHECKER), 'bypassed_commands': [x for x in calls if x != CHECKER]}
            rows.append(row)
            print(flavor, case, 'PASS', run.returncode, flush=True)
finally:
    SCRIPT.write_bytes(original_script)
    LIST.write_bytes(original_list)
assert SCRIPT.read_bytes() == original_script and LIST.read_bytes() == original_list
(ROOT / 'complete-dispatch-results.json').write_text(json.dumps({
    'base': 'f40eb37a6fb8b665340fe92a2f248ff3f23ec7f6', 'profile': __doc__,
    'rows': rows, 'restored': True, 'list_sha256': hashlib.sha256(original_list).hexdigest(),
    'script_sha256': hashlib.sha256(original_script).hexdigest(),
}, indent=2) + '\n')
print('PASS: complete-source dispatcher controls and byte-exact restoration.')
