import copy,unittest
from progress import classify

def fixture():
 return {'complete':True,'clean_cleanup':True,'binary_verified':True,'a_preserved':True,'b_completion_exact':True,'a_total_bytes':32*1024**2+75,'b_total_bytes':16*1024**2+75,'partial':{'verified_b_bytes':4*1024**2,'job':{'status':'running','bytes_committed':36*1024**2+75},'transfer':{'bytes_committed':36*1024**2+75,'percent':100},'b_manifest':{'complete':False}}}
class Offline(unittest.TestCase):
 def test_reproduction(self):self.assertEqual(classify(fixture()),'PROGRESS_INCLUDES_UNRELATED_MODEL_BYTES')
 def test_correct_control(self):
  r=fixture();p=r['partial'];p['job']['bytes_committed']=p['verified_b_bytes'];p['transfer'].update(bytes_committed=p['verified_b_bytes'],percent=int(p['verified_b_bytes']*100/r['b_total_bytes']));self.assertEqual(classify(r),'PROGRESS_SCOPED_TO_DOWNLOADED_MODEL')
 def test_required_controls(self):
  for k in ('complete','clean_cleanup','binary_verified','a_preserved','b_completion_exact'):
   r=fixture();r[k]=False
   with self.assertRaises(RuntimeError):classify(r)
 def test_incomplete_capture(self):
  r=fixture();r['partial']['b_manifest']['complete']=True
  with self.assertRaises(RuntimeError):classify(r)
 def test_wrong_byte_count(self):
  r=fixture();r['partial']['job']['bytes_committed']+=1
  with self.assertRaises(RuntimeError):classify(r)
 def test_terminal_capture(self):
  r=fixture();r['partial']['job']['status']='done'
  with self.assertRaises(RuntimeError):classify(r)
if __name__=='__main__':unittest.main()
