import sys,os,json,hashlib,datetime
from pathlib import Path
p=Path(__file__).resolve().parent;mode=sys.argv[1];base=p/mode
sys.path[:0]=[str(base),str(base/'tests')];sys.path.append('<home>/Library/Python/3.9/lib/python/site-packages')
os.environ['PYTEST_DISABLE_PLUGIN_AUTOLOAD']='1'
import pytest
import swapnet.application,swapnet.journal,swapnet.coordinator
class Receipt:
 def __init__(self):self.rows=[]
 def pytest_runtest_logreport(self,report):
  if report.when=='call' or report.failed or report.skipped:self.rows.append({'case':report.nodeid,'phase':report.when,'result':report.outcome,'seconds':report.duration})
r=Receipt();test=p/'candidate/tests/test_inbox_commit_recovery.py';args=[str(test),'-q','--tb=short','--import-mode=importlib','-p','no:cacheprovider','--basetemp='+str(p/(mode+'-runtime'))]+sys.argv[2:]
code=pytest.main(args,plugins=[r]);mods=[swapnet.application,swapnet.journal,swapnet.coordinator];loaded={m.__name__:{'path':m.__file__,'sha256':hashlib.sha256(Path(m.__file__).read_bytes()).hexdigest()} for m in mods};assert all(Path(v['path']).resolve().is_relative_to(base.resolve()) for v in loaded.values()),loaded
(p/(mode+'-results.json')).write_text(json.dumps({'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'mode':mode,'source':'bd847e2b986722c1723b4cd60988d4f4908452d4','python':sys.version,'test_sha256':hashlib.sha256(test.read_bytes()).hexdigest(),'loaded':loaded,'exit_code':int(code),'results':r.rows},indent=2)+'\n');sys.exit(code)
