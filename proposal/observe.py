"""Normal configured-contact-only helper observation; no runtime on import."""
from pathlib import Path
import argparse,hashlib,json,os,signal,socket,struct,tempfile,time,shutil
from helpers import Helper,digest,completion,require
EXPECTED='28d7ecb6c611e5676d85de7a64038bc7d07cd0b6b2fb2606390d5e6405838ad2'
class Deadline(BaseException):pass
def preserves(before,after):
 return bool(before) and all(after.get(k,{}).get('sha256')==v['sha256'] and after.get(k,{}).get('bytes')==v['bytes'] for k,v in before.items())
def validate(r):
 require(r.get('complete') is True and r.get('binary_verified') is True,'incomplete/unverified')
 require(r.get('initial_empty') is True,'receiver not empty')
 require(r.get('configured_peer_only') is True and r.get('lan_disabled') is True,'wrong discovery path')
 require(r.get('automatic_job') is True and r.get('acquired_models',0)>=1,'automatic acquisition not proved')
 require(r.get('peer_authenticated_same_chain') is True,'contact/chain not authenticated')
 require(r.get('model_id_matches') is True and r.get('artifact_id_matches') is True,'identity mismatch')
 require(r.get('integrity',{}).get('complete') is True and r['integrity'].get('bytes')==r['source_bytes'] and r['integrity'].get('sha384')==r['source_sha384'],'bytes incomplete/wrong')
 require(r.get('health_polls')==3 and r.get('clean_cleanup') is True and r.get('runtime_removed') is True,'health/cleanup')
 require(len(r.get('process_exits',[]))==3 and all(x==0 for x in r['process_exits']),'helper exits')
 require(not any(c['method']=='getmodel'for c in r.get('follower_calls',[])),'manual getmodel used')
 require(r.get('active_partial_before_stop') is True and r.get('saved_automatic_after_stop') is True and r.get('retained_partial_after_stop') is True and r.get('restart_preserved_pieces') is True,'restart path not proved')
 return True

def run(binary,out):
 out.mkdir(parents=True,exist_ok=False);root=Path(tempfile.mkdtemp(prefix='s2cfg-'));helpers=[];r={'complete':False,'binary_verified':digest(binary)==EXPECTED,'automatic_job':False,'clean_cleanup':False,'runtime_removed':False};start=time.monotonic()
 def save():(out/'result.json').write_text(json.dumps(r,indent=2)+'\n')
 def alarm(*_):raise Deadline('600second observation deadline')
 signal.signal(signal.SIGALRM,alarm);signal.alarm(600)
 try:
  require(r['binary_verified'],'wrong helper binary')
  with socket.socket()as s:s.bind(('127.0.0.1',0));port=s.getsockname()[1]
  endpoint='127.0.0.1:'+str(port)
  for name in ('provider','follower'):(root/name).mkdir()
  provider=Helper(binary,root/'provider',out,'provider',64<<20,hostport=port);helpers.append(provider);provider.start()
  src=root/'model.safetensors';n=8<<20;header=json.dumps({'t':{'dtype':'U8','shape':[n],'data_offsets':[0,n]}},separators=(',',':')).encode();src.write_bytes(struct.pack('<Q',len(header))+header+hashlib.shake_256(b'configured-first').digest(n))
  imported=provider.ok('importmodel',[str(src),{'pin':True}]);mid=imported['model_id'];uri=imported['uri'];manifest=provider.ok('getmodelmanifest',[uri]);aid=manifest['artifact_id'];require(manifest['complete'] is True,'publisher incomplete')
  r.update(source_bytes=src.stat().st_size,source_sha384=digest(src,'sha384'),model_id=mid,artifact_id=aid,endpoint=endpoint)
  follower=Helper(binary,root/'follower',out,'follower',64<<20,peer=endpoint);helpers.append(follower)
  r['initial_empty']=not (follower.store/'catalog.json').exists() and not list(follower.store.rglob('*.piece'))
  follower.start();r['configured_peer_only']=follower.ok('getmodelpeers')['peers']==[endpoint];require(r['configured_peer_only'],'unexpected configured contacts');r['launch_args']={h.label:h.launch_args for h in helpers};r['startup_info']={h.label:h.start_info for h in helpers};r['lan_disabled']=True
  def sample():
   require(follower.ok('getmodelpeers')['peers']==[endpoint],'contacts changed');info=follower.info();np=info['native_participation'];require(np['network']=='regtest'and np['lan_enabled'] is False and np['hint_count']==0,'unexpected chain/LAN hints')
   require(int(info.get('automatic_spend_atoms',0))==0,'spend')
   peers=[p for p in np['peer_observations']if p['endpoint']==endpoint and len(p['transport_pin'])==96 and mid in p['advertised_models']]
   if peers:r['peer_authenticated_same_chain']=True
   r['acquired_models']=np['acquired_models'];r.setdefault('samples',[]).append(info)
   path=follower.store/'retrieve_jobs.json'
   if path.exists():
    jobs=json.loads(path.read_text()).get('jobs',[])
    if any(j.get('model_id')==mid and j.get('automatic') is True for j in jobs):r['automatic_job']=True;r['automatic_job_snapshot']=jobs
   return follower.row(mid)
  # Interrupt only once actual automatic work has committed a proper prefix.
  end=time.monotonic()+120
  while time.monotonic()<end:
   row=sample();pieces=follower.pieces(aid);actual=sum(p['bytes']for p in pieces.values())
   jobs=follower.ok('getmodeljob').get('jobs',[])
   active=[j for j in jobs if j.get('model_id')==mid and j.get('status')=='running']
   if r['automatic_job'] and active and 0<actual<=src.stat().st_size//2:
    r['active_partial_before_stop']=True;r['before_stop_pieces']=pieces;r['before_stop_jobs']=active;break
   require(not(row.get('bytes_verified')is True and row.get('incomplete')is False),'fixture missed active partial boundary');time.sleep(.2)
  else:raise RuntimeError('No active automatic partial boundary; no restart test ran')
  oldproc=follower.proc;follower.stop();r['first_exit']=oldproc.returncode
  retained=follower.pieces(aid);r['retained_partial_after_stop']=0<sum(p['bytes']for p in retained.values())<src.stat().st_size
  require(r['retained_partial_after_stop'],'fixture transfer finished before stop')
  require(preserves(r['before_stop_pieces'],retained),'normal stop lost a sampled piece')
  saved=json.loads((follower.store/'retrieve_jobs.json').read_text()).get('jobs',[])
  r['saved_after_stop']=saved;r['saved_automatic_after_stop']=any(j.get('model_id')==mid and j.get('automatic')is True for j in saved)
  require(r['saved_automatic_after_stop'],'no automatic saved job after normal stop')
  follower.start();r['after_restart_startup']=follower.start_info[-1]
  r['post_restart_samples_begin']=len(r.get('samples',[]))
  end=time.monotonic()+180
  while time.monotonic()<end:
   row=sample();save()
   if row.get('bytes_verified') is True and row.get('incomplete') is False:break
   require(follower.proc.poll() is None,'follower exited');time.sleep(.5)
  else:raise RuntimeError('No verified automatic model within300s; inspect observations, not a defect verdict')
  final_pieces=follower.pieces(aid);r['restart_preserved_pieces']=preserves(retained,final_pieces)
  r['integrity']=completion(follower,uri,r['source_sha384']);r['model_id_matches']=r['integrity']['manifest']['model_id']==mid;r['artifact_id_matches']=r['integrity']['manifest']['artifact_id']==aid
  r['health_polls']=0
  for _ in range(3):require(sample().get('incomplete') is False,'model became incomplete');r['health_polls']+=1;time.sleep(.5)
  r['complete']=True
 except Deadline as e:r['error']=str(e)
 except Exception as e:r['error']=repr(e)
 finally:
  signal.alarm(0);r['process_exits']=[];r['cleanup_errors']=[]
  for h in reversed(helpers):
   proc=h.proc;h.cleanup();r['process_exits'].append(proc.poll()if proc else None)
   if h.cleanup_error or h.forced:r['cleanup_errors'].append({'helper':h.label,'error':h.cleanup_error,'forced':h.forced})
   if h.label=='follower':r['follower_calls']=h.calls
  if 'first_exit'in r:r['process_exits'].append(r['first_exit'])
  r['clean_cleanup']=not r['cleanup_errors']and len(helpers)==2 and all(x==0 for x in r['process_exits'])
  if all(h.proc is None or h.proc.poll()is not None for h in helpers):shutil.rmtree(root);r['runtime_removed']=True
  r['seconds']=time.monotonic()-start;save()
 validate(r)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--helper',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();run(a.helper.resolve(),a.out.resolve())
