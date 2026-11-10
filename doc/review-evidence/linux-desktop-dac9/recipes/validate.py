"""Offline synthetic result-contract controls, no app/VM/network execution."""
import ast, copy, hashlib, json, tempfile, unittest
from pathlib import Path
from result_handling import ARCHIVE, verdict
P=Path(__file__).parent
class Contract(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
  image=self.root/'synthetic.png';image.write_bytes(b'synthetic test evidence, not an Atlas screenshot')
  proof={'file':image.name,'sha256':hashlib.sha256(image.read_bytes()).hexdigest()}
  self.s={'normal_gate_pass':True,'qt_window_pass':True,'qt_main_image':proof,'app_alive':True,'launch_image':proof,'connected_image':proof,'launch_text':'The node is the network. NOT CONNECTED', 'native_confirmation_checked':True,'rpc_control':{'chain':'regtest','blocks':0,'peers':0},'connected_observations':[{'time':1,'text':'LIVE LOCAL regtest 0 blocks'},{'time':6,'text':'LIVE LOCAL regtest 0 blocks'}],'archive_sha256':ARCHIVE,'package_before':{'app':'exact'},'package_after':{'app':'exact'},'cleanup_remaining':[],'cleanup_signals':[],'runtime_removed':True}
 def test_new_gate_controls(self):
  for key in ['normal_gate_pass','qt_window_pass','qt_main_image']:
   s=copy.deepcopy(self.s);s.pop(key);self.assertNotEqual(verdict(s,self.root)['overall'],'PASS')
 def test_complete(self):self.assertEqual(verdict(self.s,self.root)['overall'],'PASS')
 def test_survival_only(self):
  self.s.pop('launch_text');self.assertEqual(verdict(self.s,self.root)['launch'],'INCOMPLETE')
 def test_launch_only(self):
  self.s['connected_observations']=[];r=verdict(self.s,self.root);self.assertEqual((r['launch'],r['connection'],r['overall']),('PASS','INCOMPLETE','INCOMPLETE'))
 def test_no_confirmation(self):
  self.s['native_confirmation_checked']=False;self.assertNotEqual(verdict(self.s,self.root)['overall'],'PASS')
 def test_wrong_chain(self):
  self.s['rpc_control']['chain']='main';self.assertNotEqual(verdict(self.s,self.root)['overall'],'PASS')
 def test_missing_repeated_observation(self):
  self.s['connected_observations']=self.s['connected_observations'][:1];self.assertNotEqual(verdict(self.s,self.root)['overall'],'PASS')
 def test_too_short(self):
  self.s['connected_observations'][1]['time']=2;self.assertNotEqual(verdict(self.s,self.root)['overall'],'PASS')
 def test_demo_not_live(self):
  self.s['connected_observations'][1]['text']='SYNTHETIC DEMO';self.assertNotEqual(verdict(self.s,self.root)['overall'],'PASS')
 def test_wrong_archive(self):
  self.s['archive_sha256']='old';self.assertFalse(verdict(self.s,self.root)['integrity_ok'])
 def test_changed_package(self):
  self.s['package_after']={'app':'changed'};self.assertNotEqual(verdict(self.s,self.root)['overall'],'PASS')
 def test_cleanup_controls(self):
  for key,val in [('cleanup_remaining',[123]),('cleanup_signals',[123]),('runtime_removed',False)]:
   s=copy.deepcopy(self.s);s[key]=val;self.assertNotEqual(verdict(s,self.root)['overall'],'PASS')
 def test_missing_image(self):
  (self.root/'synthetic.png').unlink();self.assertNotEqual(verdict(self.s,self.root)['overall'],'PASS')
 def test_changed_image(self):
  (self.root/'synthetic.png').write_bytes(b'changed');self.assertNotEqual(verdict(self.s,self.root)['overall'],'PASS')
 def test_failure_precedence(self):
  self.s['failure']='real failure';self.assertEqual(verdict(self.s,self.root)['overall'],'FAIL')
 def test_crash(self):
  self.s['app_crashed']=True;self.assertEqual(verdict(self.s,self.root)['overall'],'FAIL')
 def test_error_prevents_pass(self):
  self.s['error']='wrapper exception';self.assertNotEqual(verdict(self.s,self.root)['overall'],'PASS')
 def test_setup_blocked(self):
  self.s['setup_blocker']='missing display';self.assertEqual(verdict(self.s,self.root)['overall'],'BLOCKED')
 def test_empty_skip_cannot_pass(self):
  for state in ({},{'skipped':True},{'overall':'PASS'}):self.assertNotEqual(verdict(state,self.root)['overall'],'PASS')
 def test_syntax_and_actual_consumer(self):
  for name in ('run.py','ui.py','result_handling.py'):ast.parse((P/name).read_text())
  runner=(P/'run.py').read_text();self.assertIn('state.update(verdict(state,out))',runner)
  self.assertIn("if __name__=='__main__'",runner)
 def test_real_finalizer_writes_verdict(self):
  tree=ast.parse((P/'run.py').read_text())
  main=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='main')
  block=next(n for n in main.body if isinstance(n,ast.Try))
  tail=block.finalbody[-2:]
  for change in (False,True):
   state=copy.deepcopy(self.s)
   if change:state['error']='GUI incomplete'
   scope={'state':state,'out':self.root,'verdict':verdict,'json':json}
   exec(compile(ast.Module(body=tail,type_ignores=[]),'actual-finalizer','exec'),scope)
   saved=json.loads((self.root/'result.json').read_text())
   self.assertEqual(saved['overall'],'INCOMPLETE' if change else 'PASS')
if __name__=='__main__':unittest.main(verbosity=2)
