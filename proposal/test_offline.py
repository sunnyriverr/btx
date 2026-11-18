import copy,unittest
from observe import classify,SHA
class Results(unittest.TestCase):
 def valid(self):return {'complete':True,'clean_shutdown':True,'controls':{'normal':True,'cancel_before_start':True},'helper_sha256':SHA,'originals_unchanged':True,'attempts':[{'index':0,'copy_seen':1.,'cancel':{'cancelled':True,'state':'CANCELLED'},'cancel_returned':2.,'execute_returned':3.,'final':{'state':'MODEL_READY'}}]}
 def test_proof(self):self.assertEqual(classify(self.valid())['verdict'],'CANCELLATION_OVERWRITTEN')
 def test_late_cancel_not_proof(self):
  r=self.valid();r['attempts'][0]['cancel_returned']=4.;self.assertEqual(classify(r)['verdict'],'RACE_NOT_OBSERVED')
 def test_no_copy_not_proof(self):
  r=self.valid();r['attempts'][0].pop('copy_seen');self.assertEqual(classify(r)['verdict'],'RACE_NOT_OBSERVED')
 def test_preserved_cancel(self):
  r=self.valid();r['attempts'][0]['final']['state']='CANCELLED';self.assertEqual(classify(r)['verdict'],'RACE_NOT_OBSERVED')
 def test_incomplete(self):
  r=self.valid();r['complete']=False
  with self.assertRaises(AssertionError):classify(r)
 def test_control_fail(self):
  r=self.valid();r['controls']['normal']=False
  with self.assertRaises(AssertionError):classify(r)
 def test_setup_error(self):
  r=self.valid();r['attempts'][0]['error']='refused'
  with self.assertRaises(AssertionError):classify(r)
 def test_originals_changed(self):
  r=self.valid();r['originals_unchanged']=False
  with self.assertRaises(AssertionError):classify(r)
if __name__=='__main__':unittest.main()
