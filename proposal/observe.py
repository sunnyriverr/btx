"""Bounded real regtest producer and transaction-reader observation; no repair."""
import argparse,base64,hashlib,json,os,socket,subprocess,tempfile,time,traceback
from pathlib import Path
from urllib.request import Request,urlopen
from urllib.error import HTTPError
NODE_SHA='00636dbeac1c75f808b06ad254b129270e60ccb9551b908eaf64ec18cc870995'
GENESIS='521ad0951ed299e9c56aeb7db8188972772067560351b8e55adf71dbed532360'
def classify(r):
 assert r['complete'] and r['clean_shutdown'] and r['ordinary_control'] and r['funding_confirmed']
 assert r['node_sha256']==NODE_SHA and r['source_files_match_current']
 for method in ['gettransaction','listtransactions','listsinceblock']:
  row=r['reader_results'][method];err=row.get('error');assert err is not None,(method,'no expected rejection')
  msg=err['message'];assert 'returned incorrect type' in msg and 'modelnet' in msg and 'key returned that was not in doc' in msg,(method,msg)
 return 'REPRODUCED_FUNDING_METADATA_RESULT_FAILURE'
def main():
 p=argparse.ArgumentParser();p.add_argument('--node',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(exist_ok=True,parents=True)
 r={'complete':False,'node_sha256':hashlib.sha256(a.node.read_bytes()).hexdigest(),'source_files_match_current':json.loads(Path('records/staging.json').read_text())['source_files_match_current'],'reader_results':{},'scope':'Retained Linux371profile-candidate node with relevant currenta97 source matches; diagnostic regtest, no helper, test funds only.'};proc=None;calls=[];start=time.monotonic()
 try:
  assert r['node_sha256']==NODE_SHA
  with tempfile.TemporaryDirectory(prefix='mf-',dir='/tmp')as tmp:
   root=Path(tmp);home=root/'home';home.mkdir();data=root/'data';data.mkdir();sock=socket.socket();sock.bind(('127.0.0.1',0));port=sock.getsockname()[1];sock.close();cookie=data/'regtest/.cookie';url=f'http://127.0.0.1:{port}'
   env={k:v for k,v in os.environ.items()if k not in ['GH_TOKEN','GITHUB_TOKEN','PYTHONPATH','PYTHONHOME','LD_PRELOAD','DYLD_INSERT_LIBRARIES']};env['HOME']=str(home)
   def rpc(method,*params,wallet=None,record=True):
    assert time.monotonic()-start<240,'global runtime bound'
    auth=base64.b64encode(cookie.read_bytes().strip()).decode();req=Request(url+('/wallet/'+wallet if wallet else''),json.dumps({'jsonrpc':'1.0','id':method,'method':method,'params':params}).encode(),{'Authorization':'Basic '+auth,'Content-Type':'application/json'})
    try:response=urlopen(req,timeout=25)
    except HTTPError as e:response=e
    with response:row=json.load(response)
    if record:calls.append({'method':method,'wallet':wallet,'params':params,'reply':({'error':row.get('error'),'result':'public key omitted'} if method=='exportpqkey' else row)})
    return row
   def ok(method,*params,wallet=None,record=True):
    row=rpc(method,*params,wallet=wallet,record=record);assert row.get('error')is None,(method,row);return row['result']
   def w(method,*params,record=True):return ok(method,*params,wallet='fund',record=record)
   args=[str(a.node.resolve()),'-regtest',f'-datadir={data}',f'-rpcport={port}','-rpcbind=127.0.0.1','-rpcallowip=127.0.0.1','-server=1','-listen=0','-connect=0','-dnsseed=0','-discover=0','-autoupdate=0','-swapnet=0','-modelnet=0','-modelbind=off','-rpcdoccheck=1','-autoshieldcoinbase=0','-fallbackfee=0.0002','-dbcache=16','-par=1','-regtestmatmulbindingheight=2147483647','-regtestmatmulproductdigestheight=2147483647','-regtestmatmulv4height=2147483647','-regtestmatmulrequireproductpayload=0']
   r['flags']=args[1:]
   with(a.out/'node.log').open('wb')as log:
    proc=subprocess.Popen(args,env=env,stdout=log,stderr=subprocess.STDOUT)
    try:
     deadline=time.monotonic()+40
     while True:
      assert proc.poll()is None,'node exited before ready'
      try:info=ok('getblockchaininfo',record=False);break
      except (FileNotFoundError,ConnectionError,OSError,AssertionError):
       if time.monotonic()>deadline:raise
       time.sleep(.1)
     assert info['chain']=='regtest' and ok('getblockhash',0)==GENESIS
     r['registered_rpc']=ok('help','preparemodelfunding')[:200]
     ok('createwallet','fund')
     addr=w('getnewaddress');blocks=ok('generatetoaddress',101,addr);assert len(blocks)==101
     coinbase=ok('getblock',blocks[0],1)['tx'][0]
     ordinary=w('gettransaction',coinbase);r['ordinary_control']=ordinary['txid']==coinbase and ordinary['confirmations']>=100;assert r['ordinary_control'];r['ordinary_txid']=coinbase
     claimant=w('exportpqkey',w('getnewaddress'))['pubkey'];refund=w('exportpqkey',w('getnewaddress'))['pubkey']
     opts={'key_hash':hashlib.sha256(bytes.fromhex('42'*32)).hexdigest(),'claimant':claimant,'refund_pubkey':refund,'refund_height':max(ok('getblockcount')+1000,1024),'amount_atoms':10000000,'auto_pay':False,'assurance':'KEY_RELEASE_ONLY','assurance_mode':'KEY_RELEASE_ONLY'}
     frozen=w('preparemodelfunding',opts);assert frozen['automatic_spend']==0 and frozen['htlc']=='htlc_sha256'
     signed=w('signmodelfunding',frozen['unsigned_hex'],frozen);assert signed['complete'] and signed['automatic_spend']==0
     submitted=w('submitmodelfunding',signed['hex'],frozen);assert submitted['submitted'] and not submitted['duplicate'];txid=submitted['txid'];r['funding_txid']=txid
     assert txid in ok('getrawmempool');bh=ok('generatetoaddress',1,addr)[0];block=ok('getblock',bh,1);r['funding_confirmed']=txid in block['tx'];assert r['funding_confirmed']
     r['reader_results']['gettransaction']=rpc('gettransaction',txid,wallet='fund')
     r['reader_results']['listtransactions']=rpc('listtransactions','*',1000,0,True,wallet='fund')
     r['reader_results']['listsinceblock']=rpc('listsinceblock',blocks[-1],1,True,False,wallet='fund')
     # Ordinary query must remain valid after the failing funding queries.
     assert w('gettransaction',coinbase)['txid']==coinbase
     r['ordinary_control_after']=True
    finally:
     if proc.poll()is None:
      try:ok('stop')
      finally:
       try:proc.wait(timeout=20)
       except subprocess.TimeoutExpired:
        proc.terminate()
        try:proc.wait(timeout=5)
        except subprocess.TimeoutExpired:proc.kill();proc.wait(timeout=5)
        raise AssertionError('node failed clean stop')
     r['node_exit']=proc.returncode;r['clean_shutdown']=proc.returncode==0
   r['complete']=True;r['verdict']=classify(r)
 except Exception:r['complete']=False;r['error']=traceback.format_exc();r['verdict']='SETUP_OR_INCOMPLETE'
 finally:
  if proc is not None and proc.poll()is None:proc.kill();proc.wait();r['forced_cleanup']=True
  r['seconds']=time.monotonic()-start;(a.out/'calls.json').write_text(json.dumps(calls,indent=2)+'\n');(a.out/'result.json').write_text(json.dumps(r,indent=2)+'\n')
 print(json.dumps({'verdict':r['verdict'],'seconds':r['seconds'],'error':r.get('error')}));return 0 if r['complete']else 2
if __name__=='__main__':raise SystemExit(main())
