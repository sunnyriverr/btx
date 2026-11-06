"""Observe named CLI options against typed whole-object controls; never sign."""
from pathlib import Path
import hashlib,json,os,subprocess
from test_framework.test_framework import BitcoinTestFramework
from test_framework.address import program_to_witness
from test_framework.psbt import PSBT,PSBT_GLOBAL_UNSIGNED_TX
class NamedOptionsTest(BitcoinTestFramework):
 def set_test_params(self):
  self.num_nodes=1;self.setup_clean_chain=True;self.wallet_names=[]
  self.extra_args=[['-modelnet=0','-modelbind=off','-networkactive=0','-dnsseed=0','-discover=0','-walletbroadcast=0']]
 def add_options(self,parser):
  self.add_wallet_options(parser,descriptors=True,legacy=False)
 def skip_test_if_missing_module(self):
  self.skip_if_no_wallet()
 def run_test(self):
  try:self.observe()
  finally:
   self.stop_nodes()
   if hasattr(self,"rec"):
    self.rec["node_rpc_shutdown_complete"]=True
    (Path(os.environ["PSBT_RESULTS"])/"observations.json").write_text(json.dumps(self.rec,indent=2)+"\n")
 def observe(self):
  out=Path(os.environ['PSBT_RESULTS']);build=Path(self.config['environment']['BUILDDIR']);node=self.nodes[0];rec={'calls':[],'comparisons':[],'direct_controls':[],'requirements':[]};self.rec=rec
  def save():(out/'observations.json').write_text(json.dumps(rec,indent=2)+'\n')
  wallet_name='named-options-disposable'
  assert node.listwallets()==[]
  node.createwallet(wallet_name=wallet_name,disable_private_keys=True,blank=True,descriptors=True,load_on_startup=False)
  wallet=node.get_wallet_rpc(wallet_name);before=wallet.getwalletinfo();assert before['private_keys_enabled'] is False and before['txcount']==0
  rec['wallet_before']={k:before[k] for k in ['walletname','private_keys_enabled','txcount']}
  # Valid BTX P2MR output and unknown input; this PSBT is never funded or sent.
  destination=program_to_witness(2,bytes.fromhex('22'*32))
  info=node.validateaddress(destination);assert info['isvalid'] and info['witness_version']==2
  rec['destination']={'address':destination,'witness_version':info['witness_version'],'scriptPubKey':info['scriptPubKey']}
  psbt=node.createpsbt([{'txid':'11'*32,'vout':0,'sequence':4294967293}],{destination:'0.00000100'},0)
  decoded=node.decodepsbt(psbt)['tx'];assert decoded['vout'][0]['scriptPubKey']['hex']=='5220'+'22'*32
  original=PSBT.from_base64(psbt);raw=original.g.map[PSBT_GLOBAL_UNSIGNED_TX];assert len(original.i)==1 and not original.i[0].map
  rec['input_psbt']=psbt;rec['unsigned_tx_hex']=raw.hex();rec['unsigned_tx_sha256']=hashlib.sha256(raw).hexdigest()
  prefix=[os.environ['PSBT_CLI_BINARY'],'-regtest','-datadir='+str(node.datadir_path),'-conf='+str(node.bitcoinconf),'-rpcwallet='+wallet_name,'-rpcclienttimeout=15']
  def valid(result,label):
   assert isinstance(result,dict) and result.get('complete') is False,(label,result)
   returned=PSBT.from_base64(result['psbt']);assert returned.g.map[PSBT_GLOBAL_UNSIGNED_TX]==raw,label
   assert len(returned.i)==1 and not returned.i[0].map,(label,'input acquired fields/signatures')
   assert 'hex' not in result,label
   return {'unsigned_transaction_unchanged':True,'input_map_empty_no_signatures':True,'complete':False,'psbt':result['psbt']}
  def call(label,args,named=True):
   argv=prefix+(['-named','walletprocesspsbt','psbt='+psbt]+args if named else ['walletprocesspsbt',psbt]+args)
   p=subprocess.run(argv,capture_output=True,text=True,timeout=25);row={'label':label,'option_args':args,'named':named,'returncode':p.returncode,'stdout':p.stdout,'stderr':p.stderr}
   if p.returncode==0:row['validated']=valid(json.loads(p.stdout),label)
   rec['calls'].append(row);save();return row
  def require(label,passed):rec['requirements'].append({'label':label,'passed':bool(passed)});save()
  existing=call('existing named flags',['sign=false','finalize=false']);assert existing['returncode']==0
  legacy=call('legacy positional',['false','ALL','false','false'],named=False);assert legacy['returncode']==0
  for field,value in [('adjust_timelocks',False),('htlc_presign',False),('p2mr_leaf',{})]:
   opts={'sign':False,'finalize':False,field:value};whole=call('whole options '+field,['options='+json.dumps(opts)]);assert whole['returncode']==0,(field,whole)
   direct=wallet.walletprocesspsbt(psbt,opts);rec['direct_controls'].append({'field':field,'result':direct,'validated':valid(direct,'direct '+field)});assert whole['validated']['psbt']==direct['psbt']
   text=json.dumps(value,separators=(',',':'));named=call('named '+field,['sign=false','finalize=false',field+'='+text])
   if named['returncode']==0:outcome='accepted';assert named['validated']['psbt']==whole['validated']['psbt']
   else:
    assert named['returncode']==3 and 'error code: -3' in named['stderr'] and field in named['stderr'] and 'type' in named['stderr'] and 'string' in named['stderr'],named
    outcome='type_error'
   require('named option accepted '+field,named['returncode']==0)
   rec['comparisons'].append({'field':field,'value':value,'whole_options_exit':whole['returncode'],'direct_typed_pass':True,'named_exit':named['returncode'],'named_outcome':outcome,'named_error':named['stderr']});save()
  # Deliberately wrong type through an already working route: same server guard.
  bad=call('whole options intentionally wrong Boolean type',['options='+json.dumps({'sign':False,'finalize':False,'adjust_timelocks':'false'})])
  assert bad['returncode']==3 and 'adjust_timelocks' in bad['stderr'] and 'string' in bad['stderr'] and 'type' in bad['stderr']
  # Wrong JSON types must still be rejected after CLI conversion.
  for field,text in [('adjust_timelocks','"false"'),('htlc_presign','"false"'),('p2mr_leaf','[]')]:
   invalid=call('named wrong type '+field,['sign=false','finalize=false',field+'='+text])
   assert invalid['returncode']==3 and field in invalid['stderr'] and 'type' in invalid['stderr'],invalid
  # An explicitly disabled signer must still reject a presigning request.
  guarded={'sign':False,'finalize':False,'htlc_presign':True}
  whole_guard=call('whole options presign guard',['options='+json.dumps(guarded)])
  assert whole_guard['returncode']==8 and 'htlc_presign requires sign=true' in whole_guard['stderr'],whole_guard
  named_guard=call('named presign guard',['sign=false','finalize=false','htlc_presign=true'])
  assert named_guard['returncode']!=0,named_guard
  require('named presign reaches existing safety guard',named_guard['returncode']==8 and 'htlc_presign requires sign=true' in named_guard['stderr'])
  funding_guard=call('whole options funding guard',['options='+json.dumps({'sign':False,'finalize':False,'min_confirmations':1})])
  assert funding_guard['returncode']==8 and 'apply only with htlc_presign' in funding_guard['stderr'],funding_guard
  after=wallet.getwalletinfo();assert after['private_keys_enabled'] is False and after['txcount']==0
  assert node.getblockcount()==0 and node.getrawmempool()==[] and wallet.listtransactions()==[]
  assert wallet.getbalance()==0 and wallet.listunspent()==[]
  rec['wallet_after']={k:after[k] for k in ['walletname','private_keys_enabled','txcount']};assert rec['wallet_after']==rec['wallet_before']
  rec['controls_complete']=True;rec['signing_disabled_every_request']=True;rec['finalization_disabled_every_request']=True;rec['height']=0;rec['mempool']=[]
  rec['acceptance_pass']=all(x['passed'] for x in rec['requirements']);save()
  assert rec['acceptance_pass'],'Named PSBT CLI requirements failed: '+str([x['label'] for x in rec['requirements'] if not x['passed']])
if __name__=='__main__':NamedOptionsTest(__file__).main()
