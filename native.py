# Disposable PR737 successful-cleanup interruption investigation. No wallet/node.
import os,json,socket,subprocess,time,hashlib,struct,tempfile,signal,threading,http.server,urllib.parse,concurrent.futures,shutil
from pathlib import Path
P=Path(__file__).resolve().parent; OUT=Path(os.environ['BTX737_OUTPUT']);OUT.mkdir(exist_ok=True)
HELPER=Path(os.environ['BTX737_HELPER']).resolve();CREATOR=Path(os.environ['BTX737_CREATOR']).resolve()
EXPECTED=os.environ['BTX737_HELPER_SHA']
assert hashlib.sha256(HELPER.read_bytes()).hexdigest()==EXPECTED
R={'status':'INCOMPLETE','source':'1e2f8b5f12295002334d3390c12cac0bb4ae2aff','helper_sha256':EXPECTED,'provider':'owned HTTP object-store fixture, not MinIO','product_patch':False,'cases':{},'requests':[]}
def save(): (OUT/'result.json').write_text(json.dumps(R,indent=2)+'\n')
objects={};denied=set();mu=threading.Lock()
class Store(http.server.BaseHTTPRequestHandler):
 def log_message(self,*a):pass
 def respond(self,head=False):
  u=urllib.parse.urlsplit(self.path)
  if u.path in denied:
   R['requests'].append([self.command,u.path,503]);save();self.send_response(503);self.send_header('Content-Length','0');self.end_headers();return
  with mu: body=objects.get(u.path)
  R['requests'].append([self.command,u.path,200 if body is not None else 404]);save()
  if body is None:
   self.send_response(404);self.send_header('Content-Length','0');self.end_headers();return
  code=200
  if self.headers.get('Range'):
   a,b=self.headers['Range'][6:].split('-');start=int(a);end=int(b) if b else len(body)-1;whole=len(body);body=body[start:end+1];code=206
  self.send_response(code);self.send_header('Content-Length',str(len(body)));self.send_header('ETag','"'+hashlib.md5(body).hexdigest()+'"')
  if code==206:self.send_header('Content-Range',f'bytes {start}-{start+len(body)-1}/{whole}')
  self.end_headers()
  if not head:self.wfile.write(body)
 def do_HEAD(self):self.respond(True)
 def do_GET(self):self.respond()
 def do_PUT(self):
  n=int(self.headers.get('Content-Length','0'));assert n<8*1024**2
  data=self.rfile.read(n)
  with mu:objects[urllib.parse.urlsplit(self.path).path]=data
  self.send_response(200);self.send_header('Content-Length','0');self.send_header('ETag','"'+hashlib.md5(data).hexdigest()+'"');self.end_headers()
server=http.server.ThreadingHTTPServer(('127.0.0.1',0),Store);threading.Thread(target=server.serve_forever,daemon=True).start()
def rpc(sock,method,params=[]):
 with socket.socket(socket.AF_UNIX) as c:
  c.settimeout(20);c.connect(str(sock));c.sendall((json.dumps({'jsonrpc':'1.0','id':'737','method':method,'params':params})+'\n').encode());c.shutdown(socket.SHUT_WR);b=b''
  while True:
   x=c.recv(65536)
   if not x:break
   b+=x;assert len(b)<8*1024**2
 d=json.loads(b)
 if d.get('error'):raise RuntimeError(str(d['error']))
 return d['result']
procs=[];logs=[]
with tempfile.TemporaryDirectory(prefix='btx737-',dir='/tmp') as temp:
 root=Path(temp);arm=root/'arm';mark=root/'boundary';creds=root/'credentials';creds.write_text('access_key_id=BTX_TEST_ACCESS_SENTINEL\nsecret_access_key=BTX_TEST_SECRET_SENTINEL\n');creds.chmod(0o600)
 def start(label,md,hook=False,producer=False):
  md.mkdir(exist_ok=True);env=os.environ.copy()
  if hook:env.update(LD_PRELOAD=str(P/'interruption.so'),BTX737_ARM=str(arm),BTX737_BOUNDARY=str(mark))
  log=(OUT/(label+'.log')).open('wb');logs.append(log)
  p=subprocess.Popen([str(CREATOR if producer else HELPER),f'-modeldir={md}',f'-modelrpcsocket={md}/rpc.sock','-modelstorage=64MiB','-pwcchain=regtest','-modelnatpmp=0','-modellandiscovery=0','-modelfollowpeers=0','-modelpreserverare=0','-modelseed=off'],env=env,stdout=log,stderr=subprocess.STDOUT,start_new_session=True);procs.append(p)
  for _ in range(100):
   assert p.poll() is None, f'helper exit {p.returncode}'
   try:rpc(md/'rpc.sock','getcloudstorageinfo',[{}]);return p
   except (OSError,ValueError,RuntimeError):time.sleep(.1)
  raise RuntimeError('readiness timeout')
 def stop(p,kill=False):
  if p.poll() is None:
   os.killpg(p.pid,signal.SIGKILL if kill else signal.SIGTERM)
   try:p.wait(10)
   except subprocess.TimeoutExpired:os.killpg(p.pid,signal.SIGKILL);p.wait(5)
 def bytes_at(md,art):return b''.join(x.read_bytes() for x in sorted((md/'store/artifacts'/art).rglob('*.piece')))
 def model(tag,large=False):
  n=4194304+8192 if large else 8192
  d=root/('source-'+tag);d.mkdir();hdr=json.dumps({'t':{'dtype':'U8','shape':[n],'data_offsets':[0,n]}},separators=(',',':')).encode();payload=(hashlib.sha256(tag.encode()).digest()*((n+31)//32))[:n];b=struct.pack('<Q',len(hdr))+hdr+payload;(d/'model.safetensors').write_bytes(b);return d,b
 try:
  for name,interrupt in [('normal',False),('interrupted',True),('legacy',True)]:
   md=root/name;p=start(name+'-initial',md,interrupt,name=='legacy');sock=md/'rpc.sock'
   cfg={'endpoint':f'http://127.0.0.1:{server.server_port}','bucket':'test737','prefix':name,'region':'us-east-1','provider':'MINIO','layout':'PIECE_OBJECTS','credential_ref':str(creds),'credential_ref_kind':'path','use_fake':False,'allow_http_loopback':True,'automatic_spend_atoms':0,'idempotency_key':name}
   configured=rpc(sock,'setcloudstorage',[cfg]);source,body=model(name);entry=rpc(sock,'importmodel',[str(source),{'publish':False,'pin':True}]);assert entry.get('cloud_uploaded') is True,entry
   art=entry['artifact_id'];mid=entry['model_id'];assert bytes_at(md,art)==body
   # Independent healthy model must remain usable through the fault.
   control_source,control_body=model(name+'-control');control=rpc(sock,'importmodel',[str(control_source),{'publish':False,'pin':True}]);assert control['model_id']!=mid
   stop(p);before_catalog=(md/'catalog.json').read_bytes()
   for x in (md/'store/artifacts'/art).rglob('*.piece'):x.unlink()
   assert (md/'catalog.json').read_bytes()==before_catalog
   p=start(name+'-recover',md,interrupt,name=='legacy');case={'entry':entry,'configuration':configured,'original_sha384':hashlib.sha384(body).hexdigest()};R['cases'][name]=case;save()
   if interrupt:
    mark.unlink(missing_ok=True);arm.touch()
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
     f=pool.submit(rpc,sock,'getmodel',[mid])
     for _ in range(150):
      if mark.exists():break
      if f.done():raise RuntimeError('recovery returned before interruption boundary: '+str(f.result()))
      time.sleep(.05)
     assert mark.exists(),'successful-cleanup boundary not reached'
     q=md/'cloud-hydrate-q/artifacts'/art/'0'
     job=Path(mark.read_text());case['boundary']={'job_path':str(job.relative_to(md)),'job_exists':job.is_file(),'job':json.loads(job.read_text()),'quarantine_exists':q.exists(),'live_bytes_match':bytes_at(md,art)==body,'catalog':json.loads((md/'catalog.json').read_text())}
     assert case['boundary']['job_exists'] and case['boundary']['live_bytes_match']
     if name=='legacy':assert not q.exists()
     save();stop(p,True);arm.unlink()
     try:f.result(timeout=5)
     except Exception as e:case['interrupted_rpc_error']=type(e).__name__
    p=start(name+'-restart-1',md)
   else:
    case['recovery']=rpc(sock,'getmodel',[mid]);assert case['recovery'].get('status')=='local',case
    stop(p);p=start(name+'-restart-1',md)
   attempts=[]
   for iteration in range(3):
    got=rpc(sock,'getmodel',[mid]);attempts.append(got);assert bytes_at(md,art)==body
    time.sleep(.2)
   case['first_restart_attempts']=attempts
   stop(p);p=start(name+'-restart-2',md);case['second_restart']=rpc(sock,'getmodel',[mid])
   case['healthy_control']=rpc(sock,'getmodel',[control['model_id']]);assert case['healthy_control'].get('status')=='local';assert bytes_at(md,control['artifact_id'])==control_body
   case['exact_live_bytes_preserved']=bytes_at(md,art)==body;case['remaining_jobs']=[str(x.relative_to(md)) for x in (md/'file_stream_jobs').glob('*')];stop(p);save()
   if interrupt:
    import urllib.request
    key=next(k for k,v in objects.items() if art in k and k.endswith('/0.piece'))
    with urllib.request.urlopen(f'http://127.0.0.1:{server.server_port}'+key,timeout=5) as reply:
     assert reply.status==200 and reply.read()==body
    case['independent_origin_read_matches']=True
  for name,corrupt in [('partial',False),('integrity',True)]:
   md=root/name;p=start(name+'-initial',md);sock=md/'rpc.sock'
   cfg={'endpoint':f'http://127.0.0.1:{server.server_port}','bucket':'test737','prefix':name,'region':'us-east-1','provider':'MINIO','layout':'PIECE_OBJECTS','credential_ref':str(creds),'credential_ref_kind':'path','use_fake':False,'allow_http_loopback':True,'automatic_spend_atoms':0,'idempotency_key':name}
   rpc(sock,'setcloudstorage',[cfg]);src,body=model(name,True);entry=rpc(sock,'importmodel',[str(src),{'publish':False,'pin':True}]);assert entry.get('cloud_uploaded') is True
   art=entry['artifact_id'];mid=entry['model_id'];key=next(k for k in objects if art in k and k.endswith('/1.piece'));denied.add(key)
   stop(p)
   for piece in (md/'store/artifacts'/art).rglob('*.piece'):piece.unlink()
   p=start(name+'-partial',md);got=rpc(sock,'getmodel',[mid]);assert got.get('status')=='not_local' and 'cloud_hydrate_error' in got,got
   stop(p);qfile=md/'cloud-hydrate-q/artifacts'/art/'0/0.piece';assert qfile.read_bytes()==body[:4194304]
   jobs=list((md/'file_stream_jobs').glob('*.json'));assert len(jobs)==1
   job=json.loads(jobs[0].read_text());assert job['next_piece']==1 and job['resume_offset']==4194304
   count=sum(1 for method,path,status in R['requests'] if method=='GET' and art in path and path.endswith('/0.piece'))
   case={'partial_job':job,'first_attempt':got,'prefix_sha384':hashlib.sha384(qfile.read_bytes()).hexdigest()};R['cases'][name]=case;save()
   if corrupt:
    altered=bytearray(qfile.read_bytes());altered[1024]^=1;qfile.write_bytes(altered)
   denied.remove(key);p=start(name+'-resume',md);got=rpc(sock,'getmodel',[mid]);case['resumed']=got
   if corrupt:
    assert got.get('status')=='not_local' and got.get('cloud_hydrate_error')=='file SHA-384 mismatch',got
    assert not list((md/'store/artifacts'/art).rglob('*.piece'))
    case['corrupt_checkpoint_refused']=True
    got=rpc(sock,'getmodel',[mid]);case['corrected_retry']=got
   else:
    after_count=sum(1 for method,path,status in R['requests'] if method=='GET' and art in path and path.endswith('/0.piece'))
    assert after_count==count;case['prefix_not_downloaded_again']=True
   assert got.get('status')=='local' and got.get('model_id')==mid and got.get('artifact_id')==art,got
   assert bytes_at(md,art)==body
   stop(p);p=start(name+'-healthy-restart',md);case['healthy_restart']=rpc(sock,'getmodel',[mid]);assert case['healthy_restart'].get('status')=='local' and bytes_at(md,art)==body;stop(p);save()
  normal=R['cases']['normal'];assert all(x.get('status')=='local' for x in normal['first_restart_attempts']) and normal['second_restart'].get('status')=='local'
  failures=[]
  for name in ['interrupted','legacy']:
   case=R['cases'][name]
   if not all(x.get('status')=='local' for x in case['first_restart_attempts']) or case['second_restart'].get('status')!='local':failures.append(name+'_restart_not_local')
  R['failures']=failures;R['status']='PASS' if not failures else 'FAIL';save()
 except Exception as e:R['status']='SETUP_OR_TEST_FAILURE';R['error']=repr(e);save();raise
 finally:
  for p in procs:stop(p,True)
  for l in logs:l.close()
  server.shutdown();R['owned_helpers_exited']=all(p.poll() is not None for p in procs);save()
R['scratch_removed']=True;save();print(json.dumps({'status':R['status'],'failures':R.get('failures')}));raise SystemExit(0 if R['status']=='PASS' else 1)
