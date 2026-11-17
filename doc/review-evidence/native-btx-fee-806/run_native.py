from pathlib import Path
from types import SimpleNamespace
from decimal import Decimal
import sys,json,subprocess,time,hashlib,sqlite3,shutil
P=Path(__file__).resolve().parent;R=P/'runtime';S=P/'source';sys.path.insert(0,str(S))
from swapnet.rpcclient import LocalRPC
from swapnet.drivers import UTXODriver
from swapnet.errors import SwapError
OLD=P.parent/'swapnet-financial-rollback-admission/native-btx';B=OLD/'saved949-package/btx-0.34.16/bin/btxd';REAL=B.parent.parent/'libexec/btxd.real'
assert hashlib.sha256(REAL.read_bytes()).hexdigest()=='ac96c05d6a83a09dbb902f0d89fd04049897a0ac659660c228926a1ed31b9e6f'
port=json.loads((P/'port.json').read_text())['port'];rpc=LocalRPC('http://127.0.0.1:'+str(port),cookie_path=R/'regtest/.cookie',timeout=10)
wrpc=LocalRPC(rpc.url+'/wallet/presence',cookie_path=rpc.cookie_path,timeout=10)
allowed={'getblockchaininfo','getblockhash','getblockcount','getrawtransaction','getblockheader','decoderawtransaction','gettransaction','listwallets','loadwallet','stop'};calls=[]
def measured(method,*args):
 assert method in allowed,method
 calls.append({'method':method,'arg_count':len(args)});return rpc(method,*args)
def wallet(method,*args):
 assert method in allowed,method
 calls.append({'method':'wallet:'+method,'arg_count':len(args)});return wrpc(method,*args)
result={'status':'INCOMPLETE','native_source':'949a98e34222cc4cdb5b1d5bd650aa3b7bcbff72','python_source':'bd847e2b986722c1723b4cd60988d4f4908452d4','scope':'NativeBTXfeeRPC boundary on retained ordinaryP2MRpayment, notHTLC/fullSwap/nativecurrentbinary/defaultMatMul'};proc=None
try:
 with (P/'node.log').open('wb') as log:
  args=[str(B),'-regtest','-datadir='+str(R.resolve()),'-conf='+str((R/'btx.conf').resolve()),'-rpcport='+str(port),'-listen=0','-connect=0','-dnsseed=0','-discover=0','-autoupdate=0','-swapnet=0','-modelnet=0','-autoshieldcoinbase=0','-regtestmatmulbindingheight=2147483647','-regtestmatmulproductdigestheight=2147483647','-regtestmatmulv4height=2147483647','-regtestmatmulrequireproductpayload=0','-dbcache=16','-par=1','-printtoconsole=1','-debuglogfile=0']
  proc=subprocess.Popen(args,stdout=log,stderr=log)
  until=time.monotonic()+45
  while True:
   try:info=measured('getblockchaininfo');break
   except SwapError:
    if proc.poll() is not None:raise RuntimeError('Copied node exited before RPC readiness')
    if time.monotonic()>until:raise RuntimeError('Startup exceeded45second bound')
    time.sleep(.2)
  assert info['chain']=='regtest';height=measured('getblockcount')
  if 'presence' not in measured('listwallets'):measured('loadwallet','presence')
  prior=json.loads((OLD/'qualified949-result.json').read_text());txid=prior['txid'];entry=wallet('gettransaction',txid,True)
  assert hashlib.sha256(bytes.fromhex(entry['hex'])).hexdigest()==json.loads((OLD/'qualified949-receipt.json').read_text())['raw_sha256']
  tx=measured('decoderawtransaction',entry['hex']);assert tx['txid']==txid
  output=next(v for v in tx['vout'] if v['value']==Decimal('0.00100000'))
  genesis=measured('getblockhash',0);asset='btx:'+genesis+':0:native'
  driver=UTXODriver(asset,measured,wallet,wallet,None,None,network=genesis)
  terms=SimpleNamespace(asset=asset,lock_commitment=output['scriptPubKey']['hex'],amount_atoms='100000')
  ref={'txid':txid,'vout':output['n']};fee=driver.historical_funding_fee(terms,ref)
  expected=-entry['fee']*Decimal(100000000);assert expected==expected.to_integral_value() and expected>0
  assert fee==str(int(expected))
  wrong=SimpleNamespace(asset=asset,lock_commitment='00',amount_atoms=terms.amount_atoms)
  try:driver.historical_funding_fee(wrong,ref)
  except SwapError as error:assert error.code=='RECOVERY_CONFLICT'
  else:raise AssertionError('Wrong output unexpectedly accepted')
  try:driver.historical_funding_fee(terms,{'txid':'ff'*32,'vout':0})
  except SwapError as error:assert error.code=='FUNDING_FEE_UNKNOWN'
  else:raise AssertionError('Unknown transaction unexpectedly suppliedfee')
  assert measured('getblockcount')==height
  result.update(status='PASS',native_source='949a98e34222cc4cdb5b1d5bd650aa3b7bcbff72',native_binary_sha256=hashlib.sha256(REAL.read_bytes()).hexdigest(),txid=txid,original_raw_hash_verified=True,selected_vout=output['n'],original_amount_atoms='100000',native_fee_atoms=fee,independent_locally_sent_wallet_fee_oracle_atoms=str(int(expected)),wallet_fee_used_by_production=False,wrong_output_refusal='RECOVERY_CONFLICT',unknown_native_transaction_refusal='FUNDING_FEE_UNKNOWN',height_unchanged=height,new_funding_mining_signing=0,initial_ibd=info['initialblockdownload'])
except Exception as e:
 import traceback
 result.update(status='FAIL',error_type=type(e).__name__,error=str(e),traceback=traceback.format_exc())
finally:
 if proc is not None and proc.poll() is None:
  try:measured('stop');proc.wait(timeout=20)
  except Exception as e:result['shutdown_error']=str(e)
 result['own_node_stopped']=proc is not None and proc.poll() is not None
 result['calls']=calls
 import swapnet.drivers,swapnet.rpcclient
 result['loaded_python']={m.__name__:{'path':m.__file__,'sha256':hashlib.sha256(Path(m.__file__).read_bytes()).hexdigest()} for m in (swapnet.drivers,swapnet.rpcclient)}
 (P/'result.json').write_text(json.dumps(result,indent=2)+'\n')
 print(json.dumps({k:v for k,v in result.items() if k not in {'calls','loaded_python'}},indent=2))
 if not result['own_node_stopped']:raise RuntimeError('Cleanup requires own live node attention; do not delete runtime')
 if result['status']!='PASS':sys.exit(1)
