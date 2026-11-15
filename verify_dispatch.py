"""Focused dispatcher contract; unrelated checks/bootstrap are bypassed.

Uses the real Bash dispatcher, real Python 3.11 checker and real git index,
but a minimal registration fixture. This is not the full-candidate baseline.
"""
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parent
interpreter = (os.environ.get('BTX_LINT_PYTHON') or shutil.which('python3.11') or
               (sys.executable if sys.version_info[:2] == (3, 11) else None))
if not interpreter:
    raise SystemExit('Run with Python3.11 or set BTX_LINT_PYTHON to its executable.')
PYTHON = Path(interpreter).resolve()
version = subprocess.check_output([str(PYTHON), '-c', 'import sys; print(sys.version_info[:2])'], text=True)
if version.strip() != '(3, 11)':
    raise SystemExit('Focused profile requires a real Python3.11 interpreter.')
CHECKER = 'test/lint/lint-rpc-fuzz-lists.py'
REGISTER = 'inline void RegisterAllCoreRPCCommands(CRPCTable& t) { RegisterProbeRPCCommands(t); }\n'
SERVER = '''RPCHelpMan probe_rpc() { return RPCHelpMan{"probe_rpc", "", {}, {}, {}}; }
void RegisterProbeRPCCommands(CRPCTable& t) {
static const CRPCCommand commands[] = {{"test", &probe_rpc},};
}
'''
LISTS = '''const char* RPC_COMMANDS_NOT_SAFE_FOR_FUZZING{"probe_rpc"};
const char* RPC_COMMANDS_SAFE_FOR_FUZZING{"fixture_only"};
'''
CASES = {
    'valid': (SERVER, LISTS, ''),
    'missing': (SERVER, LISTS.replace('"probe_rpc"', ''), 'registered but in neither'),
    'both': (SERVER, LISTS.replace('"fixture_only"', '"fixture_only", "probe_rpc"'), 'is in both'),
    'duplicate': (SERVER, LISTS.replace('"probe_rpc"', '"probe_rpc", "probe_rpc"'), 'is listed twice'),
    'unresolved': (SERVER.replace('RPCHelpMan probe_rpc()', 'RPCHelpMan unregistered_rpc()'), LISTS,
                   'could not find the RPCHelpMan definition'),
    'restored': (SERVER, LISTS, ''),
}
results = []
for flavor in ('baseline', 'candidate'):
    root = ROOT / flavor
    for file, text in {'src/rpc/register.h': REGISTER, 'src/rpc/server.cpp': SERVER,
                       'src/test/fuzz/rpc.cpp': LISTS}.items():
        path = root / file
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
    subprocess.run(['git', 'init', '-q', str(root)], check=True)
    subprocess.run(['git', '-C', str(root), 'add', 'src', 'scripts', 'test'], check=True)
    script = (root / 'scripts/ci/run_ci_target.sh').read_text()
    version = re.search(r'local deps_version="([^"]+)"', script).group(1)
    venv = root / '.ci-lint-venv311'
    (venv / 'bin').mkdir(parents=True, exist_ok=True)
    (venv / '.deps-version').write_text(version)
    python = venv / 'bin/python3'
    python.write_text('#!/bin/bash\n'
                      'printf "%s\\n" "$1" >> "$DISPATCH_TRACE"\n'
                      'if [[ "$1" == "' + CHECKER + '" ]]; then\n'
                      '  exec ' + shlex.quote(str(PYTHON)) + ' "$@"\n'
                      'fi\n'
                      '# Explicit focused-profile bypass, not executed lint coverage.\n'
                      'exit 0\n')
    python.chmod(0o755)
    alias = venv / 'bin/python3.11'
    if not alias.exists():
        alias.symlink_to(PYTHON)
    env = dict(os.environ, PATH=str(venv / 'bin') + ':' + os.environ['PATH'])
    for case, (server, lists, diagnostic) in CASES.items():
        (root / 'src/rpc/server.cpp').write_text(server)
        (root / 'src/test/fuzz/rpc.cpp').write_text(lists)
        direct = subprocess.run([str(PYTHON), CHECKER], cwd=root, capture_output=True, text=True)
        expected = bool(diagnostic)
        assert (direct.returncode != 0) == expected, (flavor, case, direct.stdout, direct.stderr)
        if diagnostic:
            assert diagnostic in direct.stdout and 'probe_rpc' in direct.stdout
        trace = root / 'trace.txt'
        trace.write_text('')
        run = subprocess.run(['/bin/bash', 'scripts/ci/run_ci_target.sh', 'lint'], cwd=root,
                             env=dict(env, DISPATCH_TRACE=str(trace)), capture_output=True, text=True)
        calls = trace.read_text().splitlines()
        assert calls.count(CHECKER) == (1 if flavor == 'candidate' else 0)
        assert (run.returncode != 0) == (expected and flavor == 'candidate'), (flavor, case, run.stdout, run.stderr)
        if expected and flavor == 'candidate':
            assert diagnostic in run.stdout and calls[-1] == CHECKER
        results.append({'flavor': flavor, 'case': case, 'direct_exit': direct.returncode,
                        'matrix_exit': run.returncode, 'checker_calls': calls.count(CHECKER),
                        'bypassed_checks': [c for c in calls if c != CHECKER]})
        (ROOT / ('dispatch-' + flavor + '-' + case + '.log')).write_text(
            'DIRECT\n' + direct.stdout + direct.stderr + '\nMATRIX\n' + run.stdout + run.stderr)
    subprocess.run(['/bin/bash', '-n', 'scripts/ci/run_ci_target.sh'], cwd=root, check=True)
(ROOT / 'dispatch-results.json').write_text(json.dumps({'profile': __doc__, 'python': str(PYTHON),
                                                       'rows': results}, indent=2) + '\n')
print('PASS: 12 direct checks and 12 actual dispatcher cases; valid restoration and failure propagation verified.')
