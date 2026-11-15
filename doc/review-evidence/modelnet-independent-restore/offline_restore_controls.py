import unittest, tempfile, pathlib, importlib.util, os, copy
P=pathlib.Path
spec=importlib.util.spec_from_file_location('driver',P(__file__).with_name('independent_restore.py'));d=importlib.util.module_from_spec(spec);spec.loader.exec_module(d)
class Controls(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.root=P(self.tmp.name);self.payload=self.root/'payload';self.payload.mkdir();self.f=self.payload/'a';self.f.write_bytes(b'abc');self.files=[{'path':'a','size':3,'sha384':d.digest(self.f)}]
 def tearDown(self):self.tmp.cleanup()
 def test_valid(self):self.assertEqual(set(d.verify_payload(self.payload,self.files)),{'a'})
 def test_bad_hash(self):
  self.f.write_bytes(b'xyz')
  with self.assertRaises(ValueError):d.verify_payload(self.payload,self.files)
 def test_missing(self):
  self.f.unlink()
  with self.assertRaises(ValueError):d.verify_payload(self.payload,self.files)
 def test_extra(self):
  (self.payload/'extra').write_text('x')
  with self.assertRaises(ValueError):d.verify_payload(self.payload,self.files)
 def test_traversal(self):
  with self.assertRaises(ValueError):d.verify_payload(self.payload,[dict(self.files[0],path='../a')])
 def test_symlink(self):
  self.f.unlink();self.f.symlink_to(self.root/'absent')
  with self.assertRaises(ValueError):d.verify_payload(self.payload,self.files)
 def test_hardlink_rejected(self):
  dest=self.root/'link';os.link(self.f,dest)
  with self.assertRaises(ValueError):d.verify_independent(dest,self.f)
 def test_copy_valid(self):
  dest=self.root/'copy';dest.write_bytes(self.f.read_bytes());d.verify_independent(dest,self.f)
 def test_verdict(self):
  good={'status':'PASS','cleanup':True,'rows':{k:'PASS' for k in d.REQUIRED}}
  self.assertTrue(d.qualified(good))
  for k in d.REQUIRED:
   for status in ('FAIL','SKIP','TIMEOUT','BLOCKED'):
    bad=copy.deepcopy(good);bad['rows'][k]=status;self.assertFalse(d.qualified(bad))
  for field,value in [('cleanup',False),('failure','exception'),('status','INCOMPLETE')]:
   bad=copy.deepcopy(good);bad[field]=value;self.assertFalse(d.qualified(bad))
if __name__=='__main__':unittest.main(verbosity=2)
