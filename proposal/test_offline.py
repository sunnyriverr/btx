import unittest
from observe import classify,NODE_SHA
class Validator(unittest.TestCase):
 def result(self):return {'complete':True,'clean_shutdown':True,'ordinary_control':True,'funding_confirmed':True,'node_sha256':NODE_SHA,'source_files_match_current':True,'reader_results':{m:{'error':{'message':'returned incorrect type: modelnet key returned that was not in doc'}}for m in ['gettransaction','listtransactions','listsinceblock']}}
 def test_expected(self):self.assertEqual(classify(self.result()),'REPRODUCED_FUNDING_METADATA_RESULT_FAILURE')
 def test_setup_not_proof(self):
  r=self.result();r['funding_confirmed']=False
  with self.assertRaises(AssertionError):classify(r)
 def test_ordinary_failure_not_proof(self):
  r=self.result();r['ordinary_control']=False
  with self.assertRaises(AssertionError):classify(r)
 def test_unrelated_rpc_error_not_proof(self):
  r=self.result();r['reader_results']['gettransaction']['error']['message']='wallet missing'
  with self.assertRaises(AssertionError):classify(r)
 def test_no_failure_not_proof(self):
  r=self.result();r['reader_results']['gettransaction']['error']=None
  with self.assertRaises(AssertionError):classify(r)
 def test_wrong_binary_not_proof(self):
  r=self.result();r['node_sha256']='wrong'
  with self.assertRaises(AssertionError):classify(r)
if __name__=='__main__':unittest.main()
