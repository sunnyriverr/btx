from pathlib import Path
import unittest,re
from read_detailed_suite import validate
ROOT=Path(__file__).parent
RAW=(ROOT/'attempt2/records/candidate-economy-suite.log').read_text()
NAMES=re.findall(r'BOOST_AUTO_TEST_CASE\((\w+)\)',(ROOT/'attempt2/ci/candidate-modelnet_economy_tests.cpp').read_text())
class Checks(unittest.TestCase):
 def test_actual_saved_result(self):self.assertEqual(validate(RAW,0,NAMES)['cases'],26)
 def test_process_failure(self):
  with self.assertRaises(AssertionError):validate(RAW,201,NAMES)
 def test_real_assertion(self):
  with self.assertRaises(AssertionError):validate(RAW+'\nerror: in "case": failure',0,NAMES)
 def test_failed_case(self):
  text=RAW.replace('Test case "modelnet_economy_tests/'+NAMES[0]+'" has passed with:','Test case "modelnet_economy_tests/'+NAMES[0]+'" has failed with:')
  with self.assertRaises(AssertionError):validate(text,0,NAMES)
 def test_missing_execution(self):
  text=RAW.replace('Entering test case "'+NAMES[0]+'"','Skipped case "'+NAMES[0]+'"')
  with self.assertRaises(AssertionError):validate(text,0,NAMES)
 def test_missing_leave(self):
  with self.assertRaises(AssertionError):validate(RAW.replace('Leaving test case "'+NAMES[0]+'"','Not finished'),0,NAMES)
 def test_duplicate_execution(self):
  with self.assertRaises(AssertionError):validate(RAW+'\nEntering test case "'+NAMES[0]+'"',0,NAMES)
 def test_missing_regression(self):
  with self.assertRaises(AssertionError):validate(RAW,0,[n for n in NAMES if not n.startswith('release_lists_')])
 def test_missing_report(self):
  with self.assertRaises(AssertionError):validate(RAW.split('Test module "')[0],0,NAMES)
 def test_wrong_totals(self):
  with self.assertRaises(AssertionError):validate(RAW.replace('26 test cases out of 26 passed','25 test cases out of 26 passed'),0,NAMES)
 def test_wrong_assertions(self):
  with self.assertRaises(AssertionError):validate(RAW.replace('577 assertions out of 577 passed','576 assertions out of 577 passed'),0,NAMES)
if __name__=='__main__':unittest.main()
