import copy,json,subprocess,sys,tempfile,unittest
from pathlib import Path
from classify import classify,COUNTERS
IDENTITY={'source_tree':'synthetic-tree','binary_sha256':'synthetic-binary','harness_sha256':'synthetic-harness'}
def good():
 return dict(schema=1,complete=True,skipped=False,**IDENTITY,process_exit=0,fault_scope_restored=True,
  day_before=20000,day_after=20000,month_before=24296,month_after=24296,budget_path='/disposable/budget.json',
  clean_rollover_control=True,seed=dict(counters=COUNTERS.copy(),valid_json=True,payload='daycap',file_bytes=200),
  healthy_reopen=dict(put_ok=True,get_ok=False,error='cloud origin budget exhausted'),
  fault=dict(no_origin_get=True,write_failure='EFBIG',path='/disposable/budget.json',trace_verified=True,limit_bytes=100,
   init_ok=False,ready=False,error='save failed',committed_bytes_preserved=True,invalid_json_after=False),
  recovered=dict(init_ok=True,put_ok=True,counters_before_get=COUNTERS.copy(),get_ok=False,error='budget exhausted',payload=''),
  rollover=dict(day=20001,month=24296,put_ok=True,first_get_ok=True,payload='daycap',second_get_ok=False,error='budget exhausted',
   counters=dict(day_gets=1,month_gets=2,used_gets=2,day_bytes=6,month_bytes=12,used_bytes=12)),in_memory_control=True)
class Checks(unittest.TestCase):
 def test_safe_and_reproduced(self):
  r=good();self.assertEqual(classify(r,IDENTITY),'PASS')
  r['fault']['path']='/disposable/budget.json.tmp.123';self.assertEqual(classify(r,IDENTITY),'PASS')
  r['fault']['path']='/disposable/budget.json'
  r['fault'].update(init_ok=True,ready=True,error='',committed_bytes_preserved=False,invalid_json_after=True)
  r['recovered'].update(counters_before_get=dict.fromkeys(COUNTERS,0),get_ok=True,error='',payload='daycap')
  self.assertEqual(classify(r,IDENTITY),'REPRODUCED')
 def test_missing_every_required_gate(self):
  r=good()
  for k in r:
   with self.subTest(missing=k):
    x=copy.deepcopy(r);del x[k];self.assertNotEqual(classify(x,IDENTITY),'PASS')
 def test_bad_observations(self):
  cases=[('skipped',True),('process_exit',1),('source_tree','other'),('binary_sha256','other'),('harness_sha256','other'),
   ('fault_scope_restored',False),('day_after',20001),('month_after',24297),('in_memory_control',False),('clean_rollover_control',False),
   ('fault.trace_verified',False),('fault.path','other'),('fault.path','/disposable/budget.json.tmp.123/other'),('fault.path','/elsewhere/budget.json.tmp.123'),('fault.write_failure',''),('fault.limit_bytes',199),
   ('fault.no_origin_get',False),('seed.valid_json',False),('seed.payload','wrong'),
   ('healthy_reopen.put_ok',False),('healthy_reopen.error','not found'),('recovered.put_ok',False),
   ('recovered.get_ok',True),('recovered.error','not found'),('rollover.first_get_ok',False),('rollover.payload','wrong'),
   ('rollover.second_get_ok',True),('rollover.month',24297),('rollover.counters.used_bytes',6)]
  for path,value in cases:
   with self.subTest(path=path):
    x=copy.deepcopy(good());obj=x;parts=path.split('.')
    for k in parts[:-1]:obj=obj[k]
    obj[parts[-1]]=value;self.assertNotEqual(classify(x,IDENTITY),'PASS')
 def test_cli_propagates_failure_and_malformed_input(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d);(p/'identity.json').write_text(json.dumps(IDENTITY))
   for obj,expected in [(good(),0),({**good(),'skipped':True},2),({},2)]:
    (p/'r.json').write_text(json.dumps(obj));c=subprocess.run([sys.executable,str(Path(__file__).with_name('classify.py')),str(p/'r.json'),str(p/'identity.json')],capture_output=True)
    self.assertEqual(c.returncode,expected)
   (p/'r.json').write_text('{');self.assertEqual(subprocess.run([sys.executable,str(Path(__file__).with_name('classify.py')),str(p/'r.json'),str(p/'identity.json')],capture_output=True).returncode,2)
if __name__=='__main__':unittest.main(verbosity=2)
