import copy,unittest
from native_fixture import classify,BINARY_SHA,CAP
class ResultChecks(unittest.TestCase):
 def sample(self):
  return {'binary_sha256':BINARY_SHA,'expected_binary_sha256':BINARY_SHA,'expected_sha384':'expected','fresh':{'complete':True,'sha384':'expected','cap':CAP},'clean_restart':True,'source_healthy':True,'forced_cleanup':False,'admission':{'cap':CAP,'used':4<<20,'total':(68<<20)+100,'remaining':(64<<20)+100,'incomplete':True,'pieces_verified':True,'manual_job':True},'pieces_preserved_after_restart':True,'insufficient':{'quota_error':True,'cap':64<<20},'same_cap':{'complete':False,'quota_error':True},'larger_cap':{'complete':True,'sha384':'expected','old_pieces_preserved':True}}
 def test_valid_outcomes(self):
  r=self.sample();self.assertEqual(classify(r),'CONFIRMED');r['same_cap'].update(complete=True,sha384='expected');self.assertEqual(classify(r),'DISPROVED')
 def test_missing(self):
  r=self.sample()
  for k in r:
   x=copy.deepcopy(r);del x[k]
   if k!='larger_cap':self.assertEqual(classify(x),'INCOMPLETE',k)
 def test_bad_controls(self):
  for path,value in [('binary_sha256','wrong'),('fresh.cap',1),('fresh.sha384','wrong'),('clean_restart',False),('forced_cleanup',True),('source_healthy',False),('admission.pieces_verified',False),('admission.manual_job',False),('admission.used',0),('admission.total',2*CAP),('pieces_preserved_after_restart',False),('insufficient.quota_error',False),('same_cap.quota_error',False),('larger_cap.sha384','wrong'),('larger_cap.old_pieces_preserved',False)]:
   r=self.sample();parts=path.split('.');x=r
   for k in parts[:-1]:x=x[k]
   x[parts[-1]]=value;self.assertEqual(classify(r),'INCOMPLETE',path)
if __name__=='__main__':unittest.main(verbosity=2)
