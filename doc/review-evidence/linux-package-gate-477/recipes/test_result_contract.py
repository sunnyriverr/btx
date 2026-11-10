import unittest
from result_contract import classify
class ResultContractTest(unittest.TestCase):
    def setUp(self):
        self.case={'method':'test_selected', 'failure':'AssertionError: RuntimeError not raised'}
        self.passing='test_selected (Fixture) ... ok\nRan 1 test in 0.1s\n\nOK\n'
        self.failing='test_selected (Fixture) ... FAIL\nFAIL: test_selected (Fixture)\nAssertionError: RuntimeError not raised\nRan 1 test in 0.1s\nFAILED (failures=1)\n'
    def test_positive(self):
        self.assertEqual(classify(self.case,'candidate',0,self.passing),'PASS')
        self.assertEqual(classify(dict(self.case,failure=None),'baseline',0,self.passing),'PASS')
    def test_intended_baseline_failure(self):
        self.assertEqual(classify(self.case,'baseline',1,self.failing),'EXPECTED_BASELINE_FAILURE')
    def test_unrelated_failure_is_not_proof(self):
        self.assertEqual(classify(self.case,'baseline',1,self.failing.replace('RuntimeError not raised','different error')),'INCOMPLETE')
    def test_skip_error_missing_and_wrong_count(self):
        for bad in [self.passing+'skipped=1',self.passing+'ERROR',self.passing.replace('Ran 1 test','Ran 0 tests'),self.passing.replace('test_selected','another_case')]:
            with self.subTest(bad=bad):self.assertEqual(classify(self.case,'candidate',0,bad),'INCOMPLETE')
    def test_timeout_and_exit_mismatch(self):
        for code in [1,77,-15]:self.assertEqual(classify(self.case,'candidate',code,self.passing),'INCOMPLETE')
        self.assertEqual(classify(self.case,'candidate',0,self.passing,'timeout'),'INCOMPLETE')
    def test_no_candidate_failure_promotion(self):
        self.assertEqual(classify(self.case,'candidate',1,self.failing),'INCOMPLETE')
if __name__=='__main__':unittest.main()
