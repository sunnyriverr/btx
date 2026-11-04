from pathlib import Path
import subprocess,tempfile,os,json,socket,time,struct,shutil,concurrent.futures,argparse,hashlib
ap=argparse.ArgumentParser();ap.add_argument('--binary',required=True,type=Path);ap.add_argument('--out',required=True,type=Path);a=ap.parse_args();a.out.mkdir(exist_ok=False);r=Path(__file__).resolve().parent;rows=[]
def rpc(path,method,params=[]):
 with socket.socket(socket.AF_UNIX,socket.SOCK_STREAM) as s:
  s.settimeout(4);s.connect(str(path));s.sendall(json.dumps({'id':1,'method':method,'params':params}).encode()+b'\n');s.shutdown(socket.SHUT_WR);data=b''
  while b'\n' not in data:
   z=s.recv(65536)
   if not z:break
   data+=z
  return json.loads(data)
def wait(f):
 for _ in range(100):
  try:
   x=f()
   if x:return x
  except (ValueError,OSError):pass
  time.sleep(.05)
 raise RuntimeError('startup timeout')
for mode in ['infer','generate','llama','generate-error']:
 d=Path(tempfile.mkdtemp(prefix='btx18c-',dir='/tmp'));os.chmod(d,0o700);sock=d/'rpc';rec=d/'worker.json';release=d/'release';case=a.out/mode;case.mkdir();p=None;obs={'mode':mode,'binary_sha256':hashlib.sha256(a.binary.read_bytes()).hexdigest()}
 with socket.socket() as s:s.bind(('127.0.0.1',0));port=s.getsockname()[1]
 env={k:v for k,v in os.environ.items() if not k.startswith('BTX_')};env.update(BTX_TEST_MODE=mode,BTX_TEST_RECORD=str(rec),BTX_TEST_RELEASE=str(release));env[{'infer':'BTX_MODEL_INFER_CMD','generate':'BTX_MODEL_GENERATE','llama':'BTX_LLAMA_CLI','generate-error':'BTX_MODEL_GENERATE'}[mode]]=str(r/'control')
 if mode=='infer':env['BTX_MODEL_CUDA_LOADER']=str(r.parent/'helper-worker-inheritance/adapter')
 log=(case/'helper.log').open('wb')
 try:
  p=subprocess.Popen([str(a.binary.resolve()),f'-modeldir={d}/model',f'-modelrpcsocket={sock}',f'-modelbind=127.0.0.1:{port}','-modelstorage=8MiB','-modelseed=off','-modelfollowpeers=0','-modellandiscovery=0','-modelnatpmp=0','-pwcchain=regtest'],env=env,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
  wait(lambda:rpc(sock,'getmodelnetworkinfo').get('result'));fixture=d/'fixture';fixture.mkdir()
  if mode=='llama':(fixture/'model.gguf').write_bytes(b'GGUF'+struct.pack('<I',3)+b'\0'*16)
  else:
   h=json.dumps({'weight':{'dtype':'F32','shape':[2,3],'data_offsets':[0,24]}}).encode();(fixture/'model.safetensors').write_bytes(struct.pack('<Q',len(h))+h+struct.pack('<6f',1,2,3,4,5,6));(fixture/'config.json').write_text('{"architectures":["LlamaForCausalLM"],"model_type":"llama"}')
  host=rpc(sock,'hostmodel',[str(fixture),{'publish':False}]);assert not host.get('error'),host;mid=host['result']['model_id'];t=time.monotonic()
  with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
   task=ex.submit(rpc,sock,'loadmodel' if mode=='infer' else 'generatemodel',[mid] if mode=='infer' else [mid,{'prompt':'hello-btx','max_new_tokens':8}]);wait(lambda:rec.exists());probe=rpc(sock,'getmodelnetworkinfo');assert not probe.get('error');reply=task.result(timeout=5)
  obs['elapsed_s']=time.monotonic()-t;assert obs['elapsed_s']>=.9;obs['reply']=reply;obs['worker']=json.loads(rec.read_text());obs['local_rpc_during_worker']=True
  if mode=='generate-error':assert reply['error']['code']=='NOT_RUN',reply
  else:
   assert not reply.get('error'),reply
   if mode=='infer':assert reply['result']['infer_ok'] and reply['result']['infer_stdout']=='infer-ok';assert not rpc(sock,'unloadmodel',[mid]).get('error')
   else:assert reply['result']['text']==('llama:hello-btx' if mode=='llama' else 'echo:hello-btx'),reply
  assert not rpc(sock,'getmodelnetworkinfo').get('error');p.terminate();p.wait(timeout=10);assert p.returncode==0;obs['pass']=True
 except Exception as e:obs['error']=repr(e)
 finally:
  release.write_text('release')
  if p and p.poll() is None:
   p.terminate()
   try:p.wait(timeout=10)
   except subprocess.TimeoutExpired:p.kill();p.wait();obs['forced_cleanup']=True
  log.close();shutil.rmtree(d);obs['helper_exited']=p.poll() is not None if p else True;(case/'result.json').write_text(json.dumps(obs,indent=2)+'\n');rows.append(obs);print(json.dumps({k:obs.get(k) for k in ['mode','pass','error','elapsed_s']}),flush=True)
 if obs.get('error'):break
(a.out/'results.json').write_text(json.dumps(rows,indent=2)+'\n');assert len(rows)==4 and all(x.get('pass') for x in rows)
