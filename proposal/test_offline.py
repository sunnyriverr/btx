import copy,unittest
from observe import validate,contains,LABELS,VIEWS,eligible
class Checks(unittest.TestCase):
 def good(self,broken=True):
  phases={p:{v:{l:(not(p in ('hidden','hidden_restart') and l.endswith('target')) if v=='search' or not broken else True) for l in eligible(v)} for v in VIEWS} for p in ('before','hidden','hidden_restart','unhidden')}
  violations=[{'phase':p,'view':v,'model':l} for p in ('hidden','hidden_restart') for v in VIEWS[1:] for l in eligible(v) if l.endswith('target') and phases[p][v][l]]
  return dict(complete=True,binary_verified=True,secret_disclosed=True,models={l:str(i)*96 for i,l in enumerate(LABELS)},phases=phases,direct_lookup_preserved=True,campaign_state_preserved=True,hide_acknowledged=True,unhide_acknowledged=True,process_exits=[0,0],clean_cleanup=True,runtime_removed=True,violations=violations,verdict='REPRODUCED_LISTING_INCONSISTENCY' if violations else 'NOT_REPRODUCED')
 def test_valid_both_outcomes(self):
  for broken in (True,False):self.assertTrue(validate(self.good(broken)))
 def test_empty_setup_rejected(self):
  r=self.good();r['phases']['before']['unlocked']['released_target']=False
  with self.assertRaises(RuntimeError):validate(r)
 def test_missing_unrelated_rejected(self):
  r=self.good();r['phases']['hidden']['fundable']['open_control']=False
  with self.assertRaises(RuntimeError):validate(r)
 def test_search_control_rejected(self):
  r=self.good();r['phases']['hidden_restart']['search']['open_target']=True
  with self.assertRaises(RuntimeError):validate(r)
 def test_unhide_rejected(self):
  r=self.good();r['phases']['unhidden']['recent_local']['open_target']=False
  with self.assertRaises(RuntimeError):validate(r)
 def test_required_gates(self):
  for k in ('complete','binary_verified','secret_disclosed','direct_lookup_preserved','campaign_state_preserved','hide_acknowledged','unhide_acknowledged','clean_cleanup','runtime_removed'):
   r=self.good();r[k]=False
   with self.subTest(k=k),self.assertRaises(RuntimeError):validate(r)
 def test_missing_restart(self):
  r=self.good();r['phases']['hidden_restart']['unlocked']['released_target']=None
  with self.assertRaises(RuntimeError):validate(r)
 def test_bad_exit(self):
  r=self.good();r['process_exits']=[0,-9]
  with self.assertRaises(RuntimeError):validate(r)
 def test_no_false_pass(self):
  r=self.good();r['verdict']='NOT_REPRODUCED'
  with self.assertRaises(RuntimeError):validate(r)
 def test_wrong_violations(self):
  r=self.good();r['violations']=[]
  with self.assertRaises(RuntimeError):validate(r)
 def test_exact_membership(self):
  self.assertFalse(contains([{'model_id':'x'+'a'*96}], 'a'*96));self.assertTrue(contains([{'model':{'id':'a'*96}}],'a'*96))
if __name__=='__main__':unittest.main()
