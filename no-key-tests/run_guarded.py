"""Run one local unittest module without external processes, sockets or key reads."""
import importlib.util
import json
import os
from pathlib import Path
import sys
import unittest

root = Path(__file__).resolve().parent
os.environ['GNUPGHOME'] = str(root / 'unused-key-home')
for name in ('BTX_GITHUB_TOKEN', 'GITHUB_TOKEN', 'GH_TOKEN'):
    os.environ.pop(name, None)
violations = []


def guard(event, args):
    prohibited = event in ('subprocess.Popen', 'socket.connect', 'socket.getaddrinfo',
                           'os.system', 'os.exec', 'os.posix_spawn')
    if event == 'open' and isinstance(args[0], (str, bytes)):
        path = os.fsdecode(args[0])
        prohibited |= '/.gnupg/' in path or path.endswith('/.gnupg') or 'unused-key-home' in path
    if prohibited:
        violations.append(event)
        raise RuntimeError('No-key test boundary forbids ' + event)


sys.addaudithook(guard)
file = Path(sys.argv[1]).resolve()
spec = importlib.util.spec_from_file_location('guarded_tests', file)
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)
loader = unittest.TestLoader()
suite = (unittest.TestSuite(loader.loadTestsFromName(name, module) for name in sys.argv[2:])
         if len(sys.argv) > 2 else loader.loadTestsFromModule(module))
result = unittest.TextTestRunner(verbosity=2).run(suite)
summary = {'tests': result.testsRun, 'failures': len(result.failures),
           'errors': len(result.errors), 'skipped': len(result.skipped),
           'guard_violations': violations, 'success': result.wasSuccessful() and not violations}
print('GUARDED_RESULT ' + json.dumps(summary, sort_keys=True))
raise SystemExit(0 if summary['success'] else 1)
