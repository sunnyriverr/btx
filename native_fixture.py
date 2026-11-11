# Copyright (c) 2026 The BTX developers
# Distributed under the MIT software license, see COPYING.
"""Bounded real-helper/PQ1 observation; reuses maintained retrieve fixture shapes."""
from pathlib import Path
import argparse,hashlib,json,os,signal,socket,struct,subprocess,tempfile,time,traceback
PIECE=4<<20
CAP=72<<20
TOTAL_PAYLOAD=68<<20
BINARY_SHA='0412b4d3d09ecd40e954f031ba4d2487e089a078084669af9ec598b041ba1a6c'

def require(x,msg):
 if not x:raise RuntimeError(msg)
def digest(path,alg='sha256'):
 h=hashlib.new(alg)
 with Path(path).open('rb') as f:
  for b in iter(lambda:f.read(1<<20),b''):h.update(b)
 return h.hexdigest()
def classify(r):
 try:
  require(r['binary_sha256']==BINARY_SHA,'identity')
  require(r['fresh']['complete'] and r['fresh']['sha384']==r['expected_sha384'] and r['fresh']['cap']==CAP,'fresh')
  require(r['clean_restart'] and r['source_healthy'] and not r['forced_cleanup'],'lifecycle')
  a=r['admission'];require(a['cap']==CAP and 0<a['used']<a['total']<=CAP and a['used']+a['total']>CAP and a['used']+a['remaining']<=CAP,'arithmetic')
  require(a['incomplete'] and a['pieces_verified'] and a['manual_job'] and r['pieces_preserved_after_restart'],'path')
  require(r['insufficient']['quota_error'] and r['insufficient']['cap']<a['total'],'insufficient')
  if r['same_cap']['complete']:
   require(r['same_cap']['sha384']==r['expected_sha384'],'recovered digest');return 'DISPROVED'
  require(r['same_cap']['quota_error'],'not an established quota refusal')
  require(r['larger_cap']['complete'] and r['larger_cap']['sha384']==r['expected_sha384'] and r['larger_cap']['old_pieces_preserved'],'diagnosis')
  return 'CONFIRMED'
 except (RuntimeError,KeyError,TypeError):return 'INCOMPLETE'

class Helper:
 def __init__(self,binary,root,out,label,cap,peer=None,hostport=None):
  self.binary=binary;self.root=root;self.out=out;self.label=label;self.cap=cap;self.peer=peer;self.hostport=hostport
  self.store=root/'modeldir';self.sock=root/'rpc.sock';self.proc=None;self.log=None;self.seq=0;self.starts=0;self.calls=[];self.forced=False;self.cleanup_error=None;self.start_info=[]
  self.store.mkdir(parents=True)
 def rpc(self,method,params=None):
  self.seq+=1
  with socket.socket(socket.AF_UNIX) as s:
   s.settimeout(8);s.connect(str(self.sock));s.sendall((json.dumps({'jsonrpc':'1.0','id':self.seq,'method':method,'params':params or []})+'\n').encode());s.shutdown(socket.SHUT_WR)
   with s.makefile('rb') as f:raw=f.readline(2*1024*1024)
  require(len(raw)<2*1024*1024,'RPC size');reply=json.loads(raw);require(reply['id']==self.seq,'RPC id')
  self.calls.append({'at':time.time(),'method':method,'params':params or [],'reply':reply});return reply
 def ok(self,method,params=None):
  r=self.rpc(method,params);require(not r.get('error'),method+': '+str(r.get('error')));return r['result']
 def info(self):return self.ok('getmodelnetworkinfo')
 def start(self):
  require(self.proc is None and not self.sock.exists(),'helper not cleanly stopped');self.starts+=1
  home=self.root/'home';home.mkdir(exist_ok=True)
  args=[str(self.binary),'-modeldir='+str(self.store),'-modelrpcsocket='+str(self.sock),'-modelstorage='+str(self.cap),'-modelfollowpeers=0','-modellandiscovery=0','-modelnatpmp=0','-modelseed='+('auto' if self.hostport else 'off'),'-pwcchain=regtest']
  if self.hostport:args+=['-modelhost','-modelbind=127.0.0.1:'+str(self.hostport),'-modeluploadlimit=1MiB']
  else:args+=['-modelhost=0','-modelpeer='+self.peer]
  self.log=(self.out/(self.label+'-'+str(self.starts)+'.log')).open('wb')
  self.proc=subprocess.Popen(args,stdout=self.log,stderr=subprocess.STDOUT,start_new_session=True,env=dict(os.environ,HOME=str(home),XDG_DATA_HOME=str(home/'data'),XDG_RUNTIME_DIR=str(self.root)))
  end=time.monotonic()+25
  while not self.sock.exists():
   require(self.proc.poll() is None and time.monotonic()<end,'helper startup');time.sleep(.1)
  require(Path('/proc/'+str(self.proc.pid)+'/exe').resolve()==self.binary,'process binary')
  while True:
   info=self.info()
   if info.get('helper_ready') and info.get('pq1_ready'):break
   require(time.monotonic()<end,'helper/PQ1 readiness');time.sleep(.1)
  profile=self.ok('setmodelprofile',['custom',{'storage_bytes':self.cap,'follow_peers':False,'preserve_rare':False,'seed':'auto' if self.hostport else 'off'}]);require(profile.get('applied') is True,'profile unapplied')
  while True:
   info=self.info();pol=info.get('propagation',{})
   if pol.get('storage_quota_bytes')==self.cap and pol.get('follow_configured_peers') is False and pol.get('preserve_rare') is False:break
   require(time.monotonic()<end,'effective storage/follow policy');time.sleep(.1)
  require(info.get('automatic_spend_atoms',0)==0,'automatic spend');self.start_info.append(info)
 def stop(self):
  if self.proc is None:return
  require(self.proc.poll() is None,'unexpected helper exit');self.proc.send_signal(signal.SIGTERM);self.proc.wait(25)
  require(self.proc.returncode==0 and not self.sock.exists(),'unclean helper shutdown');self.proc=None;self.log.close();self.log=None
 def cleanup(self):
  try:self.stop()
  except Exception as e:
   self.cleanup_error=str(e)
   if self.proc and self.proc.poll() is None:
    self.forced=True;os.killpg(self.proc.pid,signal.SIGKILL);self.proc.wait(10)
  if self.log:self.log.close()
  (self.out/(self.label+'-rpc.json')).write_text(json.dumps(self.calls,indent=2)+'\n')
 def row(self,model):
  path=self.store/'catalog.json'
  if not path.exists():return {}
  obj=json.loads(path.read_text())
  return next((x for x in obj.get('models',[]) if x.get('model_id')==model),{})
 def pieces(self,artifact):
  root=self.store/'store/artifacts'/artifact/'0'
  return {x.name:{'bytes':x.stat().st_size,'sha256':digest(x)} for x in sorted(root.glob('*.piece'))}
 def job(self,jid):
  x=self.ok('getmodeljob',[jid])
  if 'jobs' in x:return next((j for j in x['jobs'] if str(j.get('job_id'))==str(jid)),{})
  return x
 def request(self,uri):
  r=self.ok('getmodel',[uri,'FREE_ONLY']);return r.get('job_id'),r
 def settled(self,jid,limit):
  end=time.monotonic()+limit
  while True:
   j=self.job(jid)
   if j.get('status') in ('done','failed','cancelled'):return j
   require(time.monotonic()<end,'job did not settle');time.sleep(.2)

def quota_error(job):return 'disk quota' in json.dumps(job).lower() and job.get('status')=='failed'
def completion(h,uri,expected):
 m=h.ok('getmodelmanifest',[uri]);require(m.get('complete') is True,'manifest incomplete');require(len(m['files'])==1,'file count');f=m['files'][0];root=h.store/'store/artifacts'/m['artifact_id']/'0';d=hashlib.sha384();n=0
 for i in range((int(f['size'])+PIECE-1)//PIECE):
  b=(root/(str(i)+'.piece')).read_bytes();d.update(b);n+=len(b)
 require(n==int(f['size']) and d.hexdigest()==f['sha384']==expected,'assembled bytes differ')
 return {'complete':True,'bytes':n,'sha384':d.hexdigest(),'manifest':m,'cap':h.cap}

def run(binary,out):
 r={'schema':1,'result':'INCOMPLETE','binary_sha256':digest(binary),'source':'dac9aee53520bd49ed320ec7a49b9072fc7d88d9','forced_cleanup':False};helpers=[];root=Path(tempfile.mkdtemp(prefix='btxquota-'));started=time.monotonic()
 def save(): (out/'observations.json').write_text(json.dumps(r,indent=2)+'\n')
 def phase(name):r['phase']=name;save();print(name,flush=True)
 def expired(*a):raise RuntimeError('native observation300s bound')
 signal.signal(signal.SIGALRM,expired);signal.alarm(300)
 try:
  require(r['binary_sha256']==BINARY_SHA,'wrong saved binary');require(len(str(root/'journey/rpc.sock'))<100,'Unix path')
  with socket.socket() as s:s.bind(('127.0.0.1',0));port=s.getsockname()[1]
  endpoint='127.0.0.1:'+str(port)
  source=Helper(binary,root/'source',out,'source',512<<20,hostport=port);helpers.append(source);phase('source startup');source.start()
  path=root/'model.safetensors';header=json.dumps({'t':{'dtype':'U8','shape':[TOTAL_PAYLOAD],'data_offsets':[0,TOTAL_PAYLOAD]}},separators=(',',':')).encode();d=hashlib.sha384()
  with path.open('wb') as f:
   b=struct.pack('<Q',len(header))+header;f.write(b);d.update(b)
   for offset in range(0,TOTAL_PAYLOAD,1<<20):b=hashlib.shake_256(('quota:'+str(offset)).encode()).digest(min(1<<20,TOTAL_PAYLOAD-offset));f.write(b);d.update(b)
  r['expected_sha384']=d.hexdigest();r['source_input_bytes']=path.stat().st_size
  imp=source.ok('importmodel',[str(path),{'pin':True}]);require(imp.get('seeded') is True,'source not sharing imported model');r['source_import']=imp;uri=imp['uri'];artifact=imp['artifact_id'];model=imp['model_id'];r.update(uri=uri,artifact_id=artifact,model_id=model)
  fresh=Helper(binary,root/'fresh',out,'fresh',CAP,peer=endpoint);helpers.append(fresh);phase('fresh-fit control');fresh.start();jid,_=fresh.request(uri);r['fresh_job']=fresh.settled(jid,105);require(r['fresh_job']['status']=='done','fresh control failed');r['fresh']=completion(fresh,uri,r['expected_sha384']);fresh.stop();save()
  low=Helper(binary,root/'insufficient',out,'insufficient',64<<20,peer=endpoint);helpers.append(low);phase('insufficient-cap control');low.start();jid,_=low.request(uri);j=low.settled(jid,15);r['insufficient']={'cap':low.cap,'quota_error':quota_error(j),'job':j};require(r['insufficient']['quota_error'],'insufficient control did not refuse quota');low.stop()
  journey=Helper(binary,root/'journey',out,'journey',CAP,peer=endpoint);helpers.append(journey);phase('committing interrupted prefix');journey.start();jid,initial=journey.request(uri);end=time.monotonic()+30
  while True:
   pieces=journey.pieces(artifact);used=sum(x['bytes'] for x in pieces.values());job=journey.job(jid);row=journey.row(model)
   if used>0 and used<r['source_input_bytes'] and used+r['source_input_bytes']>CAP:
    require(row.get('incomplete') is True and job.get('status') in ('queued','running'),'partial/manual boundary');break
   require(job.get('status') in ('queued','running') and time.monotonic()<end,'no intended partial pieces');time.sleep(.1)
  saved_jobs=None
  for attempt in range(5):
   try:saved_jobs=json.loads((journey.store/'retrieve_jobs.json').read_text());break
   except (FileNotFoundError,ValueError):time.sleep(.1)
  require(saved_jobs is not None,'persisted manual job missing')
  saved_manual=next((x for x in saved_jobs.get('jobs',[]) if str(x.get('job_id'))==str(jid)),{})
  require(saved_manual.get('automatic') is False,'manual flag not established')
  r['persisted_manual_job']=saved_manual
  r['pre_stop_pieces']=pieces;r['pre_stop_job']=job;phase('clean receiver stop');journey.stop()
  pieces=journey.pieces(artifact);used=sum(x['bytes'] for x in pieces.values())
  with path.open('rb') as original:
   for name,meta in pieces.items():
    index=int(name.removesuffix('.piece'));original.seek(index*PIECE);part=original.read(PIECE)
    require(len(part)==meta['bytes'] and hashlib.sha256(part).hexdigest()==meta['sha256'],'committed piece differs from source')
  all_used=sum(x.stat().st_size for x in (journey.store/'store/artifacts').rglob('*.piece'))
  require(all_used==used,'unaccounted stored pieces')
  r['retained_pieces']=pieces;r['admission']={'cap':CAP,'total':r['source_input_bytes'],'used':used,'remaining':r['source_input_bytes']-used,'incomplete':journey.row(model).get('incomplete') is True,'pieces_verified':bool(pieces),'manual_job':saved_manual.get('automatic') is False};require(0<used<r['source_input_bytes']<=CAP and used+r['source_input_bytes']>CAP,'admission arithmetic');save()
  phase('same-cap normal restart');journey.start();r['clean_restart']=True
  # Saved work may resume at startup. An explicit ordinary manual retry is also
  # supported and deduplicates against an already-running job.
  jid,retry=journey.request(uri);j=journey.settled(jid,20);r['same_cap']={'job':j,'retry':retry,'complete':j.get('status')=='done','quota_error':quota_error(j)}
  kept=journey.pieces(artifact);r['pieces_preserved_after_restart']=all(kept.get(k)==v for k,v in pieces.items());r['source_healthy']=source.info().get('pq1_ready') is True
  if r['same_cap']['complete']:r['same_cap'].update(completion(journey,uri,r['expected_sha384']))
  else:
   require(r['same_cap']['quota_error'],'restart failure is not quota-specific');require(r['pieces_preserved_after_restart'],'retained pieces lost')
   phase('larger-cap diagnostic recovery');journey.stop();journey.cap=128<<20;journey.start();jid,_=journey.request(uri);r['larger_job']=journey.settled(jid,105);require(r['larger_job']['status']=='done','larger-cap diagnosis failed');r['larger_cap']=completion(journey,uri,r['expected_sha384']);kept=journey.pieces(artifact);r['larger_cap']['old_pieces_preserved']=all(kept.get(k)==v for k,v in pieces.items())
  require(digest(path,'sha384')==r['expected_sha384'],'source input changed');r['result']=classify(r)
  require(r['result']!='INCOMPLETE','unclassified observation')
 except Exception as e:r['error']=str(e);r['traceback']=traceback.format_exc();r['result']='INCOMPLETE'
 finally:
  signal.alarm(0)
  for h in reversed(helpers):
   h.cleanup();r['forced_cleanup']|=h.forced
  r['elapsed_seconds']=time.monotonic()-started
  r['cleanup_errors']={h.label:h.cleanup_error for h in helpers if h.cleanup_error}
  if r['forced_cleanup'] or r['cleanup_errors']:r['result']='INCOMPLETE'
  r['helper_start_observations']={h.label:h.start_info for h in helpers};save()
 return 0 if r['result'] in ('CONFIRMED','DISPROVED') else 1
if __name__=='__main__':
 a=argparse.ArgumentParser();a.add_argument('--binary',type=Path,required=True);a.add_argument('--output',type=Path,required=True);args=a.parse_args();args.output.mkdir(parents=True,exist_ok=True);raise SystemExit(run(args.binary.resolve(),args.output.resolve()))
