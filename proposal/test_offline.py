import unittest,difflib,ast,re
from pathlib import Path
ROOT=Path(__file__).resolve().parent
KEYS={'modelnet','model_output_script','model_output_vout','model_key_hash','model_release_id','model_descriptor','model_refund_pubkey','model_refund_height','model_claimant'}
def result_gate(bcode,blog,ccode,clog,same_test,unchanged_checker):
 assert bcode==1 and 'returned incorrect type'in blog and 'modelnet'in blog and 'key returned that was not in doc'in blog and 'assert_funding_readers'in blog
 assert ccode==0 and 'Test passed'in clog and 'Test failed'not in clog
 assert same_test and unchanged_checker
 return True
class Offline(unittest.TestCase):
 def args(self):return [1,'assert_funding_readers returned incorrect type modelnet key returned that was not in doc',0,'Test passed',True,True]
 def test_result(self):self.assertTrue(result_gate(*self.args()))
 def test_setup_error(self):
  a=self.args();a[1]='configuration failed'
  with self.assertRaises(AssertionError):result_gate(*a)
 def test_skip(self):
  a=self.args();a[2]=77
  with self.assertRaises(AssertionError):result_gate(*a)
 def test_failed_candidate(self):
  a=self.args();a[2]=1
  with self.assertRaises(AssertionError):result_gate(*a)
 def test_changed_test(self):
  a=self.args();a[4]=False
  with self.assertRaises(AssertionError):result_gate(*a)
 def test_changed_checker(self):
  a=self.args();a[5]=False
  with self.assertRaises(AssertionError):result_gate(*a)
 def test_narrow_typed_additions(self):
  before=(ROOT/'baseline-transactions.cpp').read_text().splitlines(True);after=(ROOT/'candidate-transactions.cpp').read_text().splitlines(True)
  diff=list(difflib.ndiff(before,after));removed=[x for x in diff if x.startswith('- ')];added=[x[2:]for x in diff if x.startswith('+ ')]
  self.assertEqual(removed,[]);self.assertEqual(len(added),9)
  found=set()
  for line in added:
   m=re.search(r'RPCResult::Type::STR, "([^"]+)", /\*optional=\*/true',line);self.assertIsNotNone(m);found.add(m[1]);self.assertNotIn('ELISION',line);self.assertNotIn('skip_type_check',line)
  self.assertEqual(found,KEYS)
 def test_maintained_regression(self):
  s=(ROOT/'wallet_modelnet_funding.py').read_text();ast.parse(s);self.assertNotIn('rpcdoccheck=0',s);self.assertIn('assert_funding_readers',s);self.assertIn('assert matches',s);self.assertIn('ordinary_txid',s)
if __name__=='__main__':unittest.main()
