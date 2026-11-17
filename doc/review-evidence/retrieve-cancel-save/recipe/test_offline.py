import copy,unittest
from results import validate_suite,CONTROLS,REGRESSION
from native import validate,cancellation_error

def xml(phase='candidate',omit=None,bad=None):
 names=sorted(CONTROLS|{REGRESSION});names=[n for n in names if n!=omit];failed={REGRESSION}if phase=='baseline'else set()
 if bad:failed.add(bad)
 return '<testsuite errors="0" failures="%d" tests="%d" skipped="0">%s</testsuite>'%(len(failed),len(names),''.join('<testcase name="'+n+'" classname="modelnet_first_run_tests">'+('<failure message="real failure"/>'if n in failed else '')+'</testcase>'for n in names))
class Offline(unittest.TestCase):
 def test_candidate(self):self.assertEqual(validate_suite(xml(),0,'candidate')['failure_count'],0)
 def test_baseline(self):self.assertEqual(validate_suite(xml('baseline'),201,'baseline')['failed_cases'],[REGRESSION])
 def test_missing_rejected(self):
  with self.assertRaises(AssertionError):validate_suite(xml(omit=REGRESSION),0,'candidate')
 def test_valid_control_failure_rejected(self):
  with self.assertRaises(AssertionError):validate_suite(xml('baseline',bad=next(iter(CONTROLS))),201,'baseline')
 def test_candidate_failure_rejected(self):
  with self.assertRaises(AssertionError):validate_suite(xml('baseline'),201,'candidate')
 def test_false_pass_rejected(self):
  with self.assertRaises(AssertionError):validate_suite(xml(),0,'baseline')
 def test_selected_skip_rejected(self):
  raw=xml().replace('skipped="0"','skipped="1"').replace('</testsuite>','<testcase name="unexpectedly_skipped" classname="modelnet_first_run_tests"><skipped/></testcase></testsuite>')
  with self.assertRaises(AssertionError):validate_suite(raw,0,'candidate')
 def test_error_contract(self):
  self.assertTrue(cancellation_error({'error':{'code':'IO_ERROR','message':'retry cancelmodeljob'}}));self.assertFalse(cancellation_error({'error':None,'result':{'cancelled':True}}));self.assertFalse(cancellation_error({'error':{'code':'INVALID_PARAMETER','message':'retry cancelmodeljob'}}))
 def test_native_validator(self):
  c={k:True for k in ('persisted_active','partial_verified','live_stopped','pieces_preserved','clean_stop','restart_quiet','no_saved_job')}
  r={'complete':True,'clean_cleanup':True,'binary_verified':True,'native_cases':3,'cases':{'save_failure_retry':c,'healthy_cancel':c,'normal_restart':{'completion_exact':True,'same_job':True,'pieces_preserved':True}},'contract_failures':[]}
  self.assertTrue(validate(r,'candidate'))
  for key in ('live_stopped','restart_quiet','pieces_preserved'):
   broken=copy.deepcopy(r);broken['cases']['save_failure_retry'][key]=False
   with self.assertRaises(RuntimeError):validate(broken,'candidate')
  broken=copy.deepcopy(r);broken['contract_failures']=['failed_cancel_error']
  with self.assertRaises(RuntimeError):validate(broken,'candidate')
  r['contract_failures']=['failed_cancel_error','repeat_cancel_error','retry_saved_snapshot'];self.assertTrue(validate(r,'baseline'))
if __name__=='__main__':unittest.main()
