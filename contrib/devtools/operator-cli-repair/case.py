"""Identical baseline/candidate CLI workflow; real node/helper, disposable state."""
from pathlib import Path
import hashlib,json,os,subprocess
from test_framework.authproxy import JSONRPCException
from test_framework.test_framework import BitcoinTestFramework
class ConfigurationConversion(BitcoinTestFramework):
 def set_test_params(self):
  self.num_nodes=1;self.setup_clean_chain=True;self.root=Path(os.environ['OPERATOR_RUNTIME']);self.sock=self.root/'helper.sock'
  self.extra_args=[['-disablewallet','-modelnet=0','-modelbind=off','-modelrpcsocket='+str(self.sock),'-dnsseed=0','-discover=0','-networkactive=0']]
 def run_test(self):
  O=Path(os.environ['OPERATOR_RESULTS']);build=Path(self.config['environment']['BUILDDIR']);cat=self.root/'catalog';cat.mkdir();node=self.nodes[0]
  prefix=[os.environ['OPERATOR_CLI_BINARY'],'-regtest','-datadir='+str(node.datadir_path),'-conf='+str(node.bitcoinconf),'-rpcclienttimeout=15']
  rec={'cli':[],'requirements':[],'controls':[],'snapshots':{}};proc=None;stream=(O/'helper.log').open('wb')
  def save():(O/'observations.json').write_text(json.dumps(rec,indent=2)+'\n')
  def snap(label):
   value={}
   for name in ['operator_profile.json','mirror.json']:
    p=cat/name
    if p.exists():value[name]={'json':json.loads(p.read_text()),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'mtime_ns':p.stat().st_mtime_ns}
   rec['snapshots'][label]=value;save();return value
  def cli(label,method,value=None,named=False):
   args=prefix+(['-named'] if named else [])+[method]
   if value is not None:
    text=json.dumps(value) if isinstance(value,dict) else value;args+=['request='+text if named else text]
   p=subprocess.run(args,capture_output=True,text=True,timeout=25);row={'label':label,'method':method,'request':value,'named':named,'returncode':p.returncode,'stdout':p.stdout,'stderr':p.stderr};rec['cli'].append(row);save();return row
  def require(label,passed):rec['requirements'].append({'label':label,'passed':bool(passed)});save()
  def control(label,passed):
   rec['controls'].append({'label':label,'passed':bool(passed)});save();assert passed,label
  def quota(value):self.wait_until(lambda:node.getmodelnetworkinfo()['quota_bytes']==value,timeout=10)
  def selector(publisher,keep):return any(x.get('publisher_id')==publisher and x.get('keep_latest')==keep for x in node.getmodelmirror()['selectors'])
  def refused(method,request,message):
   before=snap('before-direct-'+message)
   try:getattr(node,method)(request)
   except JSONRPCException as e:control('direct refusal '+message,message in e.error['message'])
   else:raise AssertionError('invalid direct request accepted '+message)
   control('direct refusal preserves files '+message,snap('after-direct-'+message)==before)
  try:
   proc=subprocess.Popen([str(build/'bin/btx-modeld'),'-modeldir='+str(cat),'-modelrpcsocket='+str(self.sock),'-modelstorage=16MiB','-modelhost=0','-modelseed=off','-modelfollowpeers=0','-modellandiscovery=0','-modelnatpmp=0','-pwcchain=regtest'],stdout=stream,stderr=subprocess.STDOUT)
   self.wait_until(lambda:node.getmodelnetworkinfo().get('helper_ready') is True,timeout=30)
   for named in [False,True]:control('bare custom accepted '+str(named),cli('bare preset','setmodelprofile','custom',named)['returncode']==0)
   initial={'profile':'custom','storage_bytes':'8MiB','follow_peers':False,'seed':'off','upload_bps':'1MiB','preserve_rare':False}
   node.setmodelprofile(initial);quota(8*1024**2)
   for named,size in [(False,4),(True,6)]:
    request={**initial,'storage_bytes':str(size)+'MiB'};before=snap('profile-before-'+str(named));result=cli('object profile','setmodelprofile',request,named)
    stored=node.getmodelprofile();saved=json.loads((cat/'operator_profile.json').read_text())
    require('profile object saved '+str(named),result['returncode']==0 and stored['storage_arg']==str(size*1024**2) and saved['storage_arg']==str(size*1024**2))
    if result['returncode']==0:quota(size*1024**2)
    else:control('failed profile preserves files '+str(named),snap('profile-refused-'+str(named))==before)
    # Independent direct-object control leaves equivalent state for the next case.
    node.setmodelprofile(request);quota(size*1024**2);control('direct profile and quota '+str(named),node.getmodelprofile()['storage_arg']==str(size*1024**2))
   node.setmodelmirror({'publisher_id':'sentinel','keep_latest':3,'min_independent_origins':3,'idempotency_key':'sentinel'})
   for named in [False,True]:
    request={'publisher_id':'cli-'+str(named),'keep_latest':2,'min_independent_origins':2,'automatic_spend_atoms':0,'idempotency_key':'retry=key/'+str(named)}
    before=snap('mirror-before-'+str(named));result=cli('object mirror','setmodelmirror',request,named);saved=json.loads((cat/'mirror.json').read_text())
    require('mirror object saved '+str(named),result['returncode']==0 and selector(request['publisher_id'],2) and any(x.get('publisher_id')==request['publisher_id'] and x.get('keep_latest')==2 for x in saved['selectors']))
    if result['returncode']!=0:control('failed mirror preserves files '+str(named),snap('mirror-refused-'+str(named))==before)
    control('sentinel preserved '+str(named),selector('sentinel',3));node.setmodelmirror(request)
    os.utime(cat/'mirror.json',ns=(1_000_000_000,1_000_000_000));before=snap('replay-before-'+str(named));result=cli('mirror replay','setmodelmirror',request,named)
    require('keyed replay accepted '+str(named),result['returncode']==0);control('replay never rewrites '+str(named),snap('replay-after-'+str(named))==before)
    result=cli('mirror conflicting reuse','setmodelmirror',{**request,'keep_latest':7},named)
    require('key conflict reason '+str(named),result['returncode']!=0 and 'IDEMPOTENCY_CONFLICT' in result['stderr']);control('conflict preserves files '+str(named),snap('conflict-after-'+str(named))==before)
   before=snap('invalid-cli-before')
   for named in [False,True]:
    for method,request,reason in [('setmodelprofile',{**initial,'automatic_spend_atoms':1},'automatic_spend_atoms'),('setmodelmirror',{'publisher_id':'invalid-no-key','keep_latest':5},'idempotency_key required'),('setmodelmirror',{'publisher_id':'invalid-spend','keep_latest':5,'automatic_spend_atoms':1,'idempotency_key':'spend-'+str(named)},'automatic_spend_atoms must remain 0')]:
     result=cli('invalid '+reason,method,request,named);control('invalid refused '+method+str(named),result['returncode']!=0);require('specific rejection '+method+reason+str(named),reason in result['stderr']);control('invalid preserves files '+method+str(named),snap('invalid-after-'+str(len(rec['cli'])))==before)
   refused('setmodelprofile',{**initial,'automatic_spend_atoms':1},'automatic_spend_atoms')
   refused('setmodelmirror',{'keep_latest':7},'idempotency_key required')
   refused('setmodelmirror',{'keep_latest':7,'automatic_spend_atoms':1,'idempotency_key':'direct-spend'},'automatic_spend_atoms must remain 0')
   control('read-only preserves files',snap('readonly-before')==before and cli('read-only profile','getmodelprofile')['returncode']==0 and cli('read-only mirror','getmodelmirror')['returncode']==0 and snap('readonly-after')==before)
   control('zero spend and unchanged chain',node.getmodelnetworkinfo()['automatic_spend_atoms']==0 and node.getblockcount()==0)
   rec['controls_complete']=True;rec['acceptance_pass']=all(x['passed'] for x in rec['requirements']);save()
   assert rec['acceptance_pass'],'Operator CLI requirements failed: '+str([x['label'] for x in rec['requirements'] if not x['passed']])
  finally:
   try:
    if proc is not None:
     if proc.poll() is None:proc.terminate()
     proc.wait(timeout=20);rec['helper_returncode']=proc.returncode
   finally:
    stream.close();self.stop_nodes();rec['node_rpc_shutdown_complete']=True;rec['helper_socket_after_stop']=self.sock.exists();save()
if __name__=='__main__':ConfigurationConversion(__file__).main()
