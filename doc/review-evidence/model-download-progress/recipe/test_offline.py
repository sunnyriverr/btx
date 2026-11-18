import copy,unittest
from native import validate,NativeDeadline
from results import validate_suite,REQUIRED

def native_fixture(phase):
 r={'complete':True,'clean_cleanup':True,'binary_verified':True,'cases':{}}
 for name,multi in (('progress',False),('progress_multi',True)):
  a=32*1024**2+75;actual=4*1024**2;total=16*1024**2+75;delta=a if phase=='baseline'else 0
  o={'b_exact':True,'a_unchanged':True,'restart_preserved_pieces':True,'stream_attempted':True,'actual':actual,'total':total,'a_bytes':a,'file_count':2 if multi else 1,'reported':actual+delta,'percent':100 if delta else actual*100//total,'eta_present':not bool(delta),'final_reported':total+delta,'resumed':{'inflight':3,'actual':actual,'reported':actual+delta,'percent':100 if delta else actual*100//total}}
  r['cases'][name]={'observation':o,'assertion_failure':phase=='baseline'}
 return r

def xml(suite,fail=False,skip=False):
 names=REQUIRED[suite];raw='<testsuite errors="0" failures="%d" tests="%d" skipped="%d">'%(int(fail),len(names),int(skip))
 for i,n in enumerate(sorted(names)):raw+='<testcase name="'+n+'" classname="'+suite+'">'+('<failure/>'if fail and i==0 else '')+'</testcase>'
 if skip:raw+='<testcase name="filtered-selected" classname="'+suite+'"><skipped/></testcase>'
 return raw+'</testsuite>'
class Offline(unittest.TestCase):
 def test_deadline_escapes_ordinary_handlers(self):
  self.assertFalse(issubclass(NativeDeadline,Exception));self.assertFalse(issubclass(NativeDeadline,OSError))
  with self.assertRaises(NativeDeadline):
   try:raise NativeDeadline()
   except Exception:self.fail("deadline swallowed")
 def test_before_after(self):
  self.assertTrue(validate(native_fixture('baseline'),'baseline'));self.assertTrue(validate(native_fixture('candidate'),'candidate'))
 def test_controls_rejected(self):
  for field in ('a_unchanged','b_exact','restart_preserved_pieces'):
   r=native_fixture('candidate');r['cases']['progress']['observation'][field]=False
   with self.assertRaises(AssertionError):validate(r,'candidate')
 def test_unclean_rejected(self):
  r=native_fixture('candidate');r['clean_cleanup']=False
  with self.assertRaises(AssertionError):validate(r,'candidate')
 def test_bad_resumed_counter_rejected(self):
  r=native_fixture('candidate');r['cases']['progress']['observation']['resumed']['reported']+=1
  with self.assertRaises(AssertionError):validate(r,'candidate')
 def test_baseline_stale_global_value_still_proves_scope(self):
  r=native_fixture('baseline');r['cases']['progress']['observation']['reported']=r['cases']['progress']['observation']['a_bytes']
  self.assertTrue(validate(r,'baseline'))
 def test_resumed_baseline_stale_counter_still_has_unrelated_A(self):
  r=native_fixture('baseline');r['cases']['progress']['observation']['resumed']['reported']=r['cases']['progress']['observation']['a_bytes']
  self.assertTrue(validate(r,'baseline'))
 def test_resumed_baseline_arbitrary_failure_rejected(self):
  r=native_fixture('baseline');r['cases']['progress']['observation']['resumed']['reported']=0
  with self.assertRaises(AssertionError):validate(r,'baseline')
 def test_baseline_range_is_not_arbitrary_failure(self):
  for side in (-1,1):
   r=native_fixture('baseline');o=r['cases']['progress']['observation'];o['reported']=o['a_bytes']-1 if side<0 else o['a_bytes']+o['actual']+1
   with self.assertRaises(AssertionError):validate(r,'baseline')
 def test_wrong_baseline_rejected(self):
  r=native_fixture('baseline');r['cases']['progress']['observation']['reported']=0
  with self.assertRaises(AssertionError):validate(r,'baseline')
 def test_missing_case_rejected(self):
  r=native_fixture('candidate');del r['cases']['progress_multi']
  with self.assertRaises(AssertionError):validate(r,'candidate')
 def test_cpp_suites(self):
  for s in REQUIRED:self.assertTrue(validate_suite(xml(s),0,s))
 def test_cpp_failure_preserved(self):
  for s in REQUIRED:
   with self.assertRaises(AssertionError):validate_suite(xml(s,fail=True),201,s)
 def test_selected_skip_rejected(self):
  for s in REQUIRED:
   with self.assertRaises(AssertionError):validate_suite(xml(s,skip=True),0,s)
if __name__=='__main__':unittest.main()
