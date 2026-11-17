import sys,os,json,hashlib,datetime
from pathlib import Path
sys.path.append('<home>/Library/Python/3.9/lib/python/site-packages')
import pytest
p=Path(__file__).resolve().parent
mode=sys.argv[1];base=p/('source' if mode=='before' else 'candidate')
sys.path[:0]=[str(base),str(base/'tests')]
test=base/'tests/test_restored_refund_fee.py'
args=[str(test),'-q','--tb=short','-p','no:cacheprovider']
if mode=='controls':
 args=[str(base/'tests/test_runtime_recovery_v2.py'),str(base/'tests/test_restored_history.py'),str(base/'tests/test_observation_only.py'),'-q','--tb=short','-p','no:cacheprovider']
if len(sys.argv)>2:args+=sys.argv[2:]
class Receipt:
 def __init__(self):self.results=[]
 def pytest_runtest_logreport(self,report):
  if report.when=='call' or report.failed:self.results.append({'case':report.nodeid,'phase':report.when,'result':report.outcome,'seconds':report.duration})
plugin=Receipt();code=pytest.main(args,plugins=[plugin]);
import swapnet.drivers,swapnet.fee_bump
loaded={m.__name__:{'path':m.__file__,'sha256':hashlib.sha256(Path(m.__file__).read_bytes()).hexdigest()} for m in (swapnet.drivers,swapnet.fee_bump)}
assert all(Path(v['path']).resolve().is_relative_to(base.resolve()) for v in loaded.values()),loaded
(p/(mode+'-results.json')).write_text(json.dumps({'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'mode':mode,'loaded_source':loaded,'python':sys.version,'base':'371013d61dc124a363521df5b94e97f64d2464f2','exit_code':int(code),'test_sha256':hashlib.sha256(test.read_bytes()).hexdigest(),'results':plugin.results},indent=2));sys.exit(code)
