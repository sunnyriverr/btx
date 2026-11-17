import sys,os,json,hashlib
from pathlib import Path
p=Path(__file__).resolve().parent;base=p/'candidate';sys.path[:0]=[str(base),str(base/'tests')];sys.path.append('<home>/Library/Python/3.9/lib/python/site-packages');os.environ['PYTEST_DISABLE_PLUGIN_AUTOLOAD']='1'
import pytest
class Receipt:
 def __init__(self):self.rows=[]
 def pytest_runtest_logreport(self,report):
  if report.when=='call' or report.failed or report.skipped:self.rows.append({'case':report.nodeid,'phase':report.when,'result':report.outcome})
r=Receipt();tests=[str(base/'tests/test_runtime_recovery_v2.py')+'::test_encrypted_recovery_roundtrip',str(base/'tests/test_runtime_recovery_v2.py')+'::test_recovery_wrong_password_network_and_nonempty_refused',str(base/'tests/test_restore_tool.py')]
code=pytest.main(tests+['-q','--tb=short','--import-mode=importlib','-p','no:cacheprovider','--basetemp='+str(p/'restore-runtime')],plugins=[r]);import swapnet.application,swapnet.journal
loaded={m.__name__:{'path':m.__file__,'sha256':hashlib.sha256(Path(m.__file__).read_bytes()).hexdigest()} for m in [swapnet.application,swapnet.journal]};assert all(Path(v['path']).resolve().is_relative_to(base.resolve()) for v in loaded.values());(p/'restore-results.json').write_text(json.dumps({'exit_code':int(code),'loaded':loaded,'cases':r.rows},indent=2)+'\n');sys.exit(code)
