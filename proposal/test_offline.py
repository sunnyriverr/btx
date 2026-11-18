import copy,unittest
from observe import validate,preserves
class ResultChecks(unittest.TestCase):
 def good(self):return {'complete':True,'binary_verified':True,'initial_empty':True,'configured_peer_only':True,'lan_disabled':True,'automatic_job':True,'acquired_models':1,'peer_authenticated_same_chain':True,'model_id_matches':True,'artifact_id_matches':True,'integrity':{'complete':True,'bytes':100,'sha384':'abc'},'source_bytes':100,'source_sha384':'abc','health_polls':3,'clean_cleanup':True,'runtime_removed':True,'process_exits':[0,0,0],'follower_calls':[],'active_partial_before_stop':True,'saved_automatic_after_stop':True,'retained_partial_after_stop':True,'restart_preserved_pieces':True}
 def test_good(self):self.assertTrue(validate(self.good()))
 def test_missing_automatic_marker_rejected(self):
  r=self.good();r['automatic_job']=False;r['acquired_models']=1
  with self.assertRaises(RuntimeError):validate(r)
 def test_failed_conditions(self):
  for k in ['complete','binary_verified','initial_empty','configured_peer_only','lan_disabled','peer_authenticated_same_chain','model_id_matches','artifact_id_matches','clean_cleanup','runtime_removed','active_partial_before_stop','saved_automatic_after_stop','retained_partial_after_stop','restart_preserved_pieces']:
   with self.subTest(k=k):
    r=self.good();r[k]=False
    with self.assertRaises(RuntimeError):validate(r)
 def test_no_auto(self):
  r=self.good();r['acquired_models']=0
  with self.assertRaises(RuntimeError):validate(r)
 def test_manual(self):
  r=self.good();r['follower_calls']=[{'method':'getmodel'}]
  with self.assertRaises(RuntimeError):validate(r)
 def test_bad_bytes(self):
  for k,v in [('complete',False),('bytes',99),('sha384','bad')]:
   r=self.good();r['integrity'][k]=v
   with self.assertRaises(RuntimeError):validate(r)
 def test_bad_exit(self):
  r=self.good();r['process_exits']=[0,-9]
  with self.assertRaises(RuntimeError):validate(r)
 def test_health(self):
  r=self.good();r['health_polls']=0
  with self.assertRaises(RuntimeError):validate(r)
 def test_preservation_boundaries(self):
  old={'0.piece':{'bytes':4,'sha256':'a'}}
  self.assertTrue(preserves(old,old))
  self.assertFalse(preserves(old,{}))
  self.assertFalse(preserves(old,{'0.piece':{'bytes':4,'sha256':'b'}}))
  self.assertFalse(preserves(old,{'0.piece':{'bytes':3,'sha256':'a'}}))
if __name__=='__main__':unittest.main()
