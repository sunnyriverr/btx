from pathlib import Path
import json,os,subprocess,sys,time,hashlib
from test_framework.test_framework import BitcoinTestFramework
from test_framework.authproxy import JSONRPCException

class ConfigurationParity(BitcoinTestFramework):
 def set_test_params(self):
  self.num_nodes=1;self.setup_clean_chain=True;self.root=Path(os.environ['GITHUB_WORKSPACE'])/'rpc-help-live-runtime';self.sock=self.root/'helper.sock'
  self.extra_args=[['-disablewallet','-modelnet=0','-modelbind=off','-modelrpcsocket='+str(self.sock),'-dnsseed=0','-discover=0','-networkactive=0']]
 def run_test(self):
  W=Path(os.environ['GITHUB_WORKSPACE']);O=W/'rpc-help-live-results';build=Path(self.config['environment']['BUILDDIR']);product=Path(self.config['environment']['SRCDIR']);catalog=self.root/'catalog';catalog.mkdir();rec={'calls':[],'snapshots':{},'helper_exits':[]};helper=None;stream=(O/'helper.log').open('wb')
  args=[str(build/'bin/btx-modeld'),'-modeldir='+str(catalog),'-modelrpcsocket='+str(self.sock),'-modelstorage=16MiB','-modelhost=0','-modelseed=off','-modelfollowpeers=0','-modellandiscovery=0','-modelnatpmp=0','-pwcchain=regtest']
  prefix=[str(build/'bin/btx-cli'),'-regtest','-datadir='+str(self.nodes[0].datadir_path),'-conf='+str(self.nodes[0].bitcoinconf),'-rpcclienttimeout=15']
  wrapper=[sys.executable,str(product/'contrib/modelnet/btx-model'),'--socket',str(self.sock),'--json']
  def save(): (O/'observations.json').write_text(json.dumps(rec,indent=2))
  def start():
   nonlocal helper
   helper=subprocess.Popen(args,stdout=stream,stderr=subprocess.STDOUT)
   def ready():
    assert helper.poll() is None,'helper exited'
    try:return self.nodes[0].getmodelnetworkinfo().get('helper_ready') is True
    except JSONRPCException:return False
   self.wait_until(ready,timeout=30)
  def stop():
   if helper and helper.poll() is None:helper.terminate();helper.wait(timeout=20)
   rec['helper_exits'].append(helper.returncode);assert helper.returncode==0
  def call(label,argv):
   p=subprocess.run(argv,capture_output=True,text=True,timeout=25);x={'label':label,'args':argv,'exit':p.returncode,'stdout':p.stdout,'stderr':p.stderr};rec['calls'].append(x);save();return x
  def snap(label):
   files={}
   for name in ['operator_profile.json','mirror.json']:
    matches=list(catalog.rglob(name));assert len(matches)<=1
    if matches:files[name]=json.loads(matches[0].read_text())
   x={'saved':files,'profile':self.nodes[0].getmodelprofile(),'mirror':self.nodes[0].getmodelmirror(),'quota':self.nodes[0].getmodelnetworkinfo().get('quota_bytes')};rec['snapshots'][label]=x;save();return x
  def raw(method,value):return getattr(self.nodes[0],method)(value)
  try:
   start();assert call('CLI connection',prefix+['getblockcount'])['exit']==0
   opts={'profile':'custom','storage_bytes':'8MiB','follow_peers':False,'preserve_rare':False,'seed':'off','upload_bps':'1MiB'}
   extras={k:v for k,v in opts.items() if k!='profile'}
   assert call('wrapper profile',wrapper+['profile','set','custom',json.dumps(extras)])['exit']==0
   self.wait_until(lambda:self.nodes[0].getmodelnetworkinfo().get('quota_bytes')==8*1024**2,timeout=10)
   a=snap('wrapper-profile');assert a['profile']['storage_arg']=='8388608'
   for named in [False,True]:
    before=snap('profile-before-'+str(named));text=json.dumps({**opts,'storage_bytes':'4MiB'})
    argv=prefix+(['-named','setmodelprofile','request='+text] if named else ['setmodelprofile',text]);call('CLI profile '+str(named),argv);after=snap('profile-after-'+str(named));rec.setdefault('profile_effects',[]).append({'named':named,'saved_unchanged':before['saved']==after['saved'],'storage_arg':after['profile'].get('storage_arg')});save()
   assert call('CLI valid bare preset',prefix+['setmodelprofile','custom'])['exit']==0
   raw('setmodelprofile',opts);self.wait_until(lambda:self.nodes[0].getmodelnetworkinfo().get('quota_bytes')==8*1024**2,timeout=10);assert snap('direct-profile')['profile']['storage_arg']=='8388608'
   before=snap('invalid-profile-before')['saved']
   try:raw('setmodelprofile',{**opts,'automatic_spend_atoms':1});raise AssertionError('invalid profile accepted')
   except JSONRPCException as e:rec['invalid_profile']=e.error
   assert snap('invalid-profile-after')['saved']==before
   assert call('wrapper mirror sentinel',wrapper+['mirror','--publisher','sentinel-publisher','--keep-latest','3','--min-independent-origins','3'])['exit']==0
   seeded=snap('wrapper-mirror');assert any(s.get('publisher_id')=='sentinel-publisher' and s.get('keep_latest')==3 for s in seeded['mirror']['selectors'])
   request={'publisher_id':'requested-publisher','keep_latest':2,'min_independent_origins':2,'automatic_spend_atoms':0}
   for named in [False,True]:
    before=snap('mirror-before-'+str(named));text=json.dumps(request);argv=prefix+(['-named','setmodelmirror','request='+text] if named else ['setmodelmirror',text]);call('CLI mirror '+str(named),argv);after=snap('mirror-after-'+str(named));rec.setdefault('mirror_effects',[]).append({'named':named,'requested_selector_saved':any(s.get('publisher_id')==request['publisher_id'] for s in after['mirror']['selectors']),'saved_before':before['saved'],'saved_after':after['saved']});assert any(s.get('publisher_id')=='sentinel-publisher' and s.get('keep_latest')==3 for s in after['mirror']['selectors']);save()
   raw('setmodelmirror',request);good=snap('direct-mirror');assert any(s.get('publisher_id')==request['publisher_id'] and s.get('keep_latest')==2 for s in good['mirror']['selectors'])
   before=good['saved']
   try:raw('setmodelmirror',{**request,'automatic_spend_atoms':1});raise AssertionError('invalid mirror accepted')
   except JSONRPCException as e:rec['invalid_mirror']=e.error
   assert snap('invalid-mirror-after')['saved']==before
   assert self.nodes[0].getmodelnetworkinfo()['automatic_spend_atoms']==0
   stop();start();after=snap('after-helper-restart');assert after['saved']==before;self.wait_until(lambda:self.nodes[0].getmodelnetworkinfo().get('quota_bytes')==8*1024**2,timeout=10)
   assert self.nodes[0].getblockcount()==0;rec['controls_pass']=True;save()
  finally:
   if helper is not None:stop()
   stream.close();self.stop_nodes();rec['node_rpc_shutdown_complete']=True;rec['socket_removed']=not self.sock.exists();save()

if __name__=='__main__':ConfigurationParity(__file__).main()
