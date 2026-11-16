# Disposable PR737 successful-cleanup interruption investigation. No wallet/node.
import os,json,socket,subprocess,time,hashlib,struct,tempfile,signal,threading,http.server,urllib.parse,concurrent.futures,shutil
from pathlib import Path
P=Path(__file__).resolve().parent; OUT=P/'records';OUT.mkdir(exist_ok=True)
HELPER=(P/'binary/baseline/btx-modeld').resolve()
EXPECTED='cb783882585291c6ab7d5f0796129336d36dc3963be3db2310bbd25fe6737eae'
assert hashlib.sha256(HELPER.read_bytes()).hexdigest()==EXPECTED
R={'status':'INCOMPLETE','source':'1e2f8b5f12295002334d3390c12cac0bb4ae2aff','helper_sha256':EXPECTED,'provider':'owned HTTP object-store fixture, not MinIO','product_patch':False,'cases':{},'requests':[]}
def save(): (OUT/'result.json').write_text(json.dumps(R,indent=2)+'\n')
previous=json.loads((P/'previous-normal.json').read_text());assert previous['helper_sha256']==EXPECTED
R['cases']['normal']=previous['normal'];R['normal_control_reused_from']=previous['producer_run']
objects={};mu=threading.Lock()
class Store(http.server.BaseHTTPRequestHandler):
 def log_message(self,*a):pass
 def respond(self,head=False):
  u=urllib.parse.urlsplit(self.path)
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
  n=int(self.headers.get('Content-Length','0'));assert n<4*1024**2
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
 def start(label,md,hook=False):
  md.mkdir(exist_ok=True);env=os.environ.copy()
  if hook:env.update(LD_PRELOAD=str(P/'interruption.so'),BTX737_ARM=str(arm),BTX737_BOUNDARY=str(mark))
  log=(OUT/(label+'.log')).open('wb');logs.append(log)
  p=subprocess.Popen([str(HELPER),f'-modeldir={md}',f'-modelrpcsocket={md}/rpc.sock','-modelstorage=64MiB','-pwcchain=regtest','-modelnatpmp=0','-modellandiscovery=0','-modelfollowpeers=0','-modelpreserverare=0','-modelseed=off'],env=env,stdout=log,stderr=subprocess.STDOUT,start_new_session=True);procs.append(p)
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
 def model(tag):
  d=root/('source-'+tag);d.mkdir();hdr=json.dumps({'t':{'dtype':'U8','shape':[8192],'data_offsets':[0,8192]}},separators=(',',':')).encode();b=struct.pack('<Q',len(hdr))+hdr+hashlib.sha256(tag.encode()).digest()*256;(d/'model.safetensors').write_bytes(b);return d,b
 try:
  for name,interrupt in [('interrupted',True)]:
   md=root/name;p=start(name+'-initial',md,interrupt);sock=md/'rpc.sock'
   cfg={'endpoint':f'http://127.0.0.1:{server.server_port}','bucket':'test737','prefix':name,'region':'us-east-1','provider':'MINIO','layout':'PIECE_OBJECTS','credential_ref':str(creds),'credential_ref_kind':'path','use_fake':False,'allow_http_loopback':True,'automatic_spend_atoms':0,'idempotency_key':name}
   configured=rpc(sock,'setcloudstorage',[cfg]);source,body=model(name);entry=rpc(sock,'importmodel',[str(source),{'publish':False,'pin':True}]);assert entry.get('cloud_uploaded') is True,entry
   art=entry['artifact_id'];mid=entry['model_id'];assert bytes_at(md,art)==body
   # Independent healthy model must remain usable through the fault.
   control_source,control_body=model(name+'-control');control=rpc(sock,'importmodel',[str(control_source),{'publish':False,'pin':True}]);assert control['model_id']!=mid
   stop(p);before_catalog=(md/'catalog.json').read_bytes()
   for x in (md/'store/artifacts'/art).rglob('*.piece'):x.unlink()
   assert (md/'catalog.json').read_bytes()==before_catalog
   p=start(name+'-recover',md,interrupt);case={'entry':entry,'configuration':configured,'original_sha384':hashlib.sha384(body).hexdigest()};R['cases'][name]=case;save()
   if interrupt:
    arm.touch()
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
     f=pool.submit(rpc,sock,'getmodel',[mid])
     for _ in range(150):
      if mark.exists():break
      if f.done():raise RuntimeError('recovery returned before interruption boundary: '+str(f.result()))
      time.sleep(.05)
     assert mark.exists(),'successful-cleanup boundary not reached'
     q=md/'cloud-hydrate-q/artifacts'/art/'0'
     job=Path(mark.read_text());case['boundary']={'job_path':str(job.relative_to(md)),'job_exists':job.is_file(),'job':json.loads(job.read_text()),'quarantine_exists':q.exists(),'live_bytes_match':bytes_at(md,art)==body,'catalog':json.loads((md/'catalog.json').read_text())}
     assert case['boundary']['job_exists'] and not q.exists() and case['boundary']['live_bytes_match']
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
    assert len(case['remaining_jobs'])==1
    # Diagnostic intervention on disposable state only, not a product repair.
    (md/case['remaining_jobs'][0]).unlink()
    p=start(name+'-stale-job-cleared',md)
    case['stale_job_only_removed_recovery']=rpc(sock,'getmodel',[mid]);assert case['stale_job_only_removed_recovery'].get('status')=='local'
    assert bytes_at(md,art)==body
    stop(p);p=start(name+'-repaired-state-restart',md)
    case['after_manual_state_recovery_restart']=rpc(sock,'getmodel',[mid]);assert case['after_manual_state_recovery_restart'].get('status')=='local'
    assert bytes_at(md,art)==body;stop(p);save()
  normal=R['cases']['normal'];assert all(x.get('status')=='local' for x in normal['first_restart_attempts']) and normal['second_restart'].get('status')=='local'
  bad=R['cases']['interrupted'];R['actual_impact_proved']=all(x.get('status')!='local' for x in bad['first_restart_attempts']) and bad['second_restart'].get('status')!='local'
  R['status']='RECOVERY_STALL_REPRODUCED' if R['actual_impact_proved'] else 'HYPOTHESIS_NOT_REPRODUCED';save()
 except Exception as e:R['status']='SETUP_OR_TEST_FAILURE';R['error']=repr(e);save();raise
 finally:
  for p in procs:stop(p,True)
  for l in logs:l.close()
  server.shutdown();R['owned_helpers_exited']=all(p.poll() is not None for p in procs);save()
R['scratch_removed']=True;save();print(json.dumps({'status':R['status'],'actual_impact_proved':R.get('actual_impact_proved')}))
