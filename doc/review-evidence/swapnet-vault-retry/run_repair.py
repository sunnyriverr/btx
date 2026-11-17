from pathlib import Path
import sys,json,hashlib,datetime,platform
P=Path(__file__).resolve().parent;mode=sys.argv[1];root=P/('source' if mode=='before' else 'candidate')
sys.path.append('<home>/Library/Python/3.9/lib/python/site-packages');sys.path[:0]=[str(root),str(root/'tests')]
import pytest
args=[str(root/'tests/test_vault_retry_durability.py'),'-q','--tb=short','-p','no:cacheprovider','--basetemp='+str(P/('runtime-'+mode))]
if mode=='controls':args=[str(root/'tests/test_execution_v2.py'),str(root/'tests/test_evm_vault.py'),str(root/'tests/test_terminal_observation_persistence.py'),'-q','--tb=short','-p','no:cacheprovider','--basetemp='+str(P/'runtime-controls')]
class Record:
 def __init__(self):self.cases=[]
 def pytest_runtest_logreport(self,report):
  if report.when=='call' or report.failed or report.skipped:self.cases.append({'case':report.nodeid,'phase':report.when,'outcome':report.outcome,'seconds':report.duration})
r=Record();code=pytest.main(args,plugins=[r])
import swapnet.vault,swapnet.coordinator,swapnet.drivers
loaded={m.__name__:{'path':m.__file__,'sha256':hashlib.sha256(Path(m.__file__).read_bytes()).hexdigest()} for m in (swapnet.vault,swapnet.coordinator,swapnet.drivers)}
assert all(Path(v['path']).resolve().is_relative_to(root.resolve()) for v in loaded.values())
(P/(mode+'-results.json')).write_text(json.dumps({'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'base':'371013d61dc124a363521df5b94e97f64d2464f2','platform':platform.platform(),'python':sys.version,'mode':mode,'loaded_source':loaded,'cases':r.cases,'exit_code':int(code),'test_sha256':hashlib.sha256((root/'tests/test_vault_retry_durability.py').read_bytes()).hexdigest()},indent=2)+'\n');sys.exit(code)
