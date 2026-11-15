import json,os,time,subprocess,urllib.request,urllib.error,base64,hashlib,shutil
from pathlib import Path
D=Path(__file__).resolve().parent;R=Path(os.environ['BTX_SNAPSHOT_RUNTIME']);R.mkdir(exist_ok=False);node=R/'node';node.mkdir();lab=R/'lab';lab.mkdir();events=[];seq=0;p=None;log=None
result={'phase':'SETUP','profile':'retained native macOS arm64 integration; exact current lab_api.cpp plus optional atomicity patch; other objects retained','binary_sha256':hashlib.sha256(Path(os.environ['BTX_SNAPSHOT_BINARY']).read_bytes()).hexdigest()}
def save():(R/'result.json').write_text(json.dumps({**result,'events':events},indent=2))
def rpc(method,params=[]):
 cookie=(node/'regtest/.cookie').read_text().strip();req=urllib.request.Request('http://127.0.0.1:39561',data=json.dumps({'jsonrpc':'2.0','id':1,'method':method,'params':params}).encode(),headers={'Authorization':'Basic '+base64.b64encode(cookie.encode()).decode(),'Content-Type':'application/json'})
 try:f=urllib.request.urlopen(req,timeout=10)
 except urllib.error.HTTPError as e:f=e
 r=json.load(f)
 if r.get('error'):raise RuntimeError(r['error']['message'])
 return r['result']
def call(method,body,write=False):
 global seq
 body=dict(body)
 if write:seq+=1;body.update(idempotency_key='snapshot-observation-'+str(seq),expected_state=None)
 try:r=rpc('lab035',[method,body]);r=r.get('result',r);events.append({'method':method,'result':r});save();return r
 except Exception as e:events.append({'method':method,'error':str(e)});save();raise

def start():
 global p,log
 assert shutil.disk_usage(D).free>1.25*1024**3
 log=(R/'node.log').open('a');args=[os.environ['BTX_SNAPSHOT_BINARY'],'-regtest','-datadir='+str(node),'-rpcport=39561','-port=39562','-listen=0','-connect=0','-dnsseed=0','-discover=0','-disablewallet','-modelnet=0','-autoupdate=0','-dbcache=4','-par=1','-server','-printtoconsole=1']
 p=subprocess.Popen(args,env={**os.environ,'BTX035_LAB_DIR':str(lab)},stdout=log,stderr=log)
 for _ in range(100):
  if p.poll() is not None:raise RuntimeError('node exited '+str(p.returncode))
  try:r=rpc('getblockchaininfo');assert r['chain']=='regtest';return
  except Exception:time.sleep(.1)
 raise RuntimeError('startup timeout')
def stop():
 global p,log
 if p:
  try:rpc('stop')
  except Exception:pass
  try:p.wait(timeout=20)
  except subprocess.TimeoutExpired:p.terminate();p.wait(timeout=10)
  p=None
 if log:log.close();log=None

def obj(kind,content):
 raw=content.encode();digest=hashlib.sha384(kind.encode()+b' '+str(len(raw)).encode()+b'\0'+raw).hexdigest()
 return {'kind':kind,'digest':digest,'content':content}
def manifest(kind,content):return json.dumps({'objects':[obj(kind,content)]},separators=(',',':'))
def repo_id(m):return hashlib.sha384(m.encode()).hexdigest()
def exists(id):return call('lab.state_get',{'target_kind':'repository','target_key':id})['exists']
def image():return json.loads((lab/'lab.json').read_text())
try:
 start()
 good=manifest('blob','legitimate snapshot control');gid=repo_id(good)
 assert exists(gid) is False
 accepted=call('lab.snapshot_import',{'manifest':good},True);assert accepted['repository_id']==gid and exists(gid)
 assert gid in image()['repos'];result['valid_import_control']=True
 bad=manifest('piece','not-a-piece');bid=repo_id(bad);assert not exists(bid)
 before=(lab/'lab.json').read_bytes();(R/'before-image.json').write_bytes(before)
 try:call('lab.snapshot_import',{'manifest':bad},True)
 except RuntimeError as e:assert 'BTX035_SCHEMA' in str(e),str(e);result['late_rejection']=str(e)
 else:raise AssertionError('bad import not rejected')
 result['live_partial_after_rejection']=exists(bid);result['disk_unchanged_immediately']=before==(lab/'lab.json').read_bytes()
 assert result['disk_unchanged_immediately']
 call('lab.repository_create',{'label':'ordinary-save','nonce':'save-1','object_format':'git','project_genesis_id':None,'default_ref':'refs/heads/main'},True)
 img=image();(R/'after-save-image.json').write_text(json.dumps(img,indent=2));result['partial_saved_by_later_write']=bid in img['repos'] and bid in img['repo_objects'];result['valid_control_preserved']=gid in img['repos']
 model=obj('model','legitimate model bytes');piece=obj('piece','v1|'+model['digest']+'|0|'+model['content'].encode().hex());models=json.dumps({'objects':[model,piece]},separators=(',',':'));mid=repo_id(models)
 imported=call('lab.snapshot_import',{'manifest':models},True);assert imported['repository_id']==mid
 result['valid_model_import_after_rejection']=exists(mid)
 stop();start();result['valid_model_after_restart']=exists(mid)
 exported=call('lab.snapshot_export',{'repository_id':mid},True);exported_objects=json.loads(exported['manifest'])['objects'];assert all(o in exported_objects for o in [model,piece]);result['valid_model_export_after_restart']=True
 result['partial_after_restart']=exists(bid);result['valid_control_after_restart']=exists(gid)
 result['phase']='IMPORT_ATOMICITY_PASS' if all(result.get(k) is False for k in ['live_partial_after_rejection','partial_saved_by_later_write','partial_after_restart']) and result['valid_control_after_restart'] and result['valid_model_export_after_restart'] else 'IMPORT_ATOMICITY_FAIL'
 assert result['valid_control_after_restart'];assert result['phase']=='IMPORT_ATOMICITY_PASS',result;print(json.dumps({k:v for k,v in result.items() if k!='events'},indent=2))
except Exception as e:result['error']=repr(e);print('OBSERVATION_FAILED',repr(e));raise
finally:stop();result['test_processes_stopped']=True;save()
