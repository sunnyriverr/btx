"""Observe named CLI options against typed whole-object controls; never sign."""
from pathlib import Path
import hashlib,json,os,subprocess
from test_framework.test_framework import BitcoinTestFramework
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
  out=Path(os.environ['PSBT_RESULTS']);build=Path(self.config['environment']['BUILDDIR']);node=self.nodes[0];rec={'calls':[],'comparisons':[],'direct_controls':[]};self.rec=rec
  def save():(out/'observations.json').write_text(json.dumps(rec,indent=2)+'\n')
  wallet_name='named-options-disposable'
  assert node.listwallets()==[]
  node.createwallet(wallet_name=wallet_name,disable_private_keys=True,blank=True,descriptors=True,load_on_startup=False)
  wallet=node.get_wallet_rpc(wallet_name);before=wallet.getwalletinfo();assert before['private_keys_enabled'] is False and before['txcount']==0
  rec['wallet_before']={k:before[k] for k in ['walletname','private_keys_enabled','txcount']}
  # Unknown external input, zero-value data output: no funding or chain activity.
  psbt=node.createpsbt([{'txid':'11'*32,'vout':0,'sequence':4294967293}],[{'data':'425458'}],0)
  original=PSBT.from_base64(psbt);raw=original.g.map[PSBT_GLOBAL_UNSIGNED_TX];assert len(original.i)==1 and not original.i[0].map
  rec['input_psbt']=psbt;rec['unsigned_tx_hex']=raw.hex();rec['unsigned_tx_sha256']=hashlib.sha256(raw).hexdigest()
  prefix=[str(build/'bin/btx-cli'),'-regtest','-datadir='+str(node.datadir_path),'-conf='+str(node.bitcoinconf),'-rpcwallet='+wallet_name,'-rpcclienttimeout=15','-named','walletprocesspsbt','psbt='+psbt]
  def valid(result,label):
   assert isinstance(result,dict) and result.get('complete') is False,(label,result)
   returned=PSBT.from_base64(result['psbt']);assert returned.g.map[PSBT_GLOBAL_UNSIGNED_TX]==raw,label
   assert len(returned.i)==1 and not returned.i[0].map,(label,'input acquired fields/signatures')
   assert 'hex' not in result,label
   return {'unsigned_transaction_unchanged':True,'input_map_empty_no_signatures':True,'complete':False,'psbt':result['psbt']}
  def call(label,args):
   p=subprocess.run(prefix+args,capture_output=True,text=True,timeout=25);row={'label':label,'option_args':args,'returncode':p.returncode,'stdout':p.stdout,'stderr':p.stderr}
   if p.returncode==0:row['validated']=valid(json.loads(p.stdout),label)
   rec['calls'].append(row);save();return row
  existing=call('existing named flags',['sign=false','finalize=false']);assert existing['returncode']==0
  for field,value in [('adjust_timelocks',False),('htlc_presign',False),('p2mr_leaf',{})]:
   opts={'sign':False,'finalize':False,field:value};whole=call('whole options '+field,['options='+json.dumps(opts)]);assert whole['returncode']==0,(field,whole)
   direct=wallet.walletprocesspsbt(psbt,opts);rec['direct_controls'].append({'field':field,'result':direct,'validated':valid(direct,'direct '+field)});assert whole['validated']['psbt']==direct['psbt']
   text=json.dumps(value,separators=(',',':'));named=call('named '+field,['sign=false','finalize=false',field+'='+text])
   if named['returncode']==0:outcome='accepted';assert named['validated']['psbt']==whole['validated']['psbt']
   else:
    assert named['returncode']==3 and 'error code: -3' in named['stderr'] and field in named['stderr'] and 'type' in named['stderr'] and 'string' in named['stderr'],named
    outcome='type_error'
   rec['comparisons'].append({'field':field,'value':value,'whole_options_exit':whole['returncode'],'direct_typed_pass':True,'named_exit':named['returncode'],'named_outcome':outcome,'named_error':named['stderr']});save()
  # Deliberately wrong type through an already working route: same server guard.
  bad=call('whole options intentionally wrong Boolean type',['options='+json.dumps({'sign':False,'finalize':False,'adjust_timelocks':'false'})])
  assert bad['returncode']==3 and 'adjust_timelocks' in bad['stderr'] and 'string' in bad['stderr'] and 'type' in bad['stderr']
  after=wallet.getwalletinfo();assert after['private_keys_enabled'] is False and after['txcount']==0
  assert node.getblockcount()==0 and node.getrawmempool()==[] and wallet.listtransactions()==[]
  assert wallet.getbalance()==0 and wallet.listunspent()==[]
  rec['wallet_after']={k:after[k] for k in ['walletname','private_keys_enabled','txcount']};assert rec['wallet_after']==rec['wallet_before']
  rec['type_error_count']=sum(x['named_outcome']=='type_error' for x in rec['comparisons']);rec['verdict']='named_type_failure_confirmed' if rec['type_error_count']==3 else 'partial_named_type_failure' if rec['type_error_count'] else 'hypothesis_disproved'
  rec['signing_disabled_every_request']=True;rec['finalization_disabled_every_request']=True;rec['height']=0;rec['mempool']=[];rec['diagnostic_complete']=True;save()
if __name__=='__main__':NamedOptionsTest(__file__).main()
