"""Bounded ordinary single-download observation; no product changes."""
import argparse,hashlib,json,signal,socket,struct,tempfile,time,traceback
from pathlib import Path
from helpers import Helper,completion,digest,require
from observe import make_model,verify_pieces,wait_for,cleanup_helpers,remove_stopped_runtime
EXPECTED='adc65ed9645aa33ca4e6f067164ec824e3cc68ab59ef8c14084e6c989312b8dc'

def make_a(path):
 size=32<<20;header=json.dumps({'a':{'dtype':'U8','shape':[size],'data_offsets':[0,size]}},separators=(',',':')).encode()
 with path.open('wb')as f:
  f.write(struct.pack('<Q',len(header))+header)
  for n in range(32):f.write(hashlib.shake_256(f'static-model-a:{n}'.encode()).digest(1<<20))

def classify(r):
 require(r.get('complete') and r.get('clean_cleanup'),'incomplete observation or cleanup')
 require(r.get('binary_verified') and r.get('a_preserved') and r.get('b_completion_exact'),'failed binary/model control')
 s=r['partial'];require(0<s['verified_b_bytes']<r['b_total_bytes'] and s['job']['status']in('running','queued'),'not an incomplete active B')
 require(s['b_manifest'].get('complete') is False,'B already complete')
 row=s['transfer'];reported=s['job']['bytes_committed'];actual=s['verified_b_bytes'];occupied=r['a_total_bytes']+actual
 if reported==occupied and row.get('bytes_committed')==reported and row.get('percent')==100:
  return 'PROGRESS_INCLUDES_UNRELATED_MODEL_BYTES'
 if reported==actual and row.get('bytes_committed')==actual and row.get('percent')==int(actual*100/r['b_total_bytes']):
  return 'PROGRESS_SCOPED_TO_DOWNLOADED_MODEL'
 raise RuntimeError('unclassified progress values; inspect raw partial snapshot')

def run(binary,out):
 out.mkdir(parents=True,exist_ok=False);helpers=[];root=None;start=time.monotonic();r={'complete':False,'binary_sha256':digest(binary),'binary_verified':digest(binary)==EXPECTED,'clean_cleanup':False}
 def save():r['seconds']=time.monotonic()-start;(out/'result.json').write_text(json.dumps(r,indent=2)+'\n')
 def alarm(*_):raise TimeoutError('15minute native bound')
 signal.signal(signal.SIGALRM,alarm);signal.alarm(900)
 try:
  require(r['binary_verified'],'retained binary mismatch');root=Path(tempfile.mkdtemp(prefix='s2-progress-'));a=root/'a.safetensors';b=root/'b.safetensors';make_a(a);make_model(b);r['a_total_bytes']=a.stat().st_size;r['b_total_bytes']=b.stat().st_size
  with socket.socket()as s:s.bind(('127.0.0.1',0));port=s.getsockname()[1]
  provider=Helper(binary,root/'provider',out,'provider',128<<20,hostport=port);helpers.append(provider);provider.start();ib=provider.ok('importmodel',[str(b),{'pin':True}]);require(ib.get('seeded')is True,'B source not serving')
  receiver=Helper(binary,root/'receiver',out,'receiver',128<<20,peer=f'127.0.0.1:{port}');helpers.append(receiver);receiver.start();ia=receiver.ok('importmodel',[str(a),{'pin':True}]);r['a_before']=completion(receiver,ia['uri'],digest(a,'sha384'));a_pieces=receiver.pieces(ia['artifact_id']);r['a_piece_snapshot']=a_pieces
  job,answer=receiver.request(ib['uri']);require(bool(job),'B request missing job');r['request']=answer;r['job_id']=job
  def partial():
   j=receiver.job(job);require(j.get('status')in('queued','running'),'B terminated before partial capture '+str(j));pieces=receiver.pieces(ib['artifact_id']);return pieces
  wait_for(partial,75,'B produced no verified partial piece')
  def capture():
   before=receiver.pieces(ib['artifact_id']);verify_pieces(b,before)
   j=receiver.job(job);transfers=receiver.ok('getmodeltransfers');rows=[x for x in transfers.get('transfers',[])if x.get('model_id')==j.get('model_id') and x.get('job_id')==job]
   manifest=receiver.ok('getmodelmanifest',[ib['uri']]);after=receiver.pieces(ib['artifact_id'])
   require(j.get('status')in('queued','running') and manifest.get('complete')is False,'B completed before stable partial snapshot')
   if before!=after or len(rows)!=1 or rows[0].get('bytes_committed')!=j.get('bytes_committed'):return None
   require(rows[0].get('bytes')==r['b_total_bytes'],'transfer denominator does not describe B payload')
   return {'job':j,'transfer':rows[0],'b_manifest':manifest,'verified_b_bytes':sum(x['bytes']for x in before.values()),'verified_b_pieces':before,'catalog_used_bytes':transfers.get('used_bytes'),'all_transfers':transfers}
  r['partial']=wait_for(capture,10,'no stable partial snapshot')
  require(receiver.pieces(ia['artifact_id'])==a_pieces,'A changed during B download');save()
  final=receiver.settled(job,180);require(final.get('status')=='done','B did not complete '+str(final));r['b_after']=completion(receiver,ib['uri'],digest(b,'sha384'));r['b_completion_exact']=True;r['a_after']=completion(receiver,ia['uri'],digest(a,'sha384'));r['a_preserved']=receiver.pieces(ia['artifact_id'])==a_pieces and r['a_before']['sha384']==r['a_after']['sha384'];require(r['a_preserved'],'A changed after B completion');r['complete']=True
 except Exception:r['error']=traceback.format_exc()
 finally:
  signal.alarm(0);clean,stopped,errors=cleanup_helpers(helpers);r['clean_cleanup']=clean;r['cleanup_errors']=errors;r['processes_stopped']=stopped;r['runtime_removed']=remove_stopped_runtime(root,stopped);r['helpers']=[{'label':h.label,'starts':h.starts,'forced':h.forced}for h in helpers];save()
 r['classification']=classify(r);save();return r
if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--helper',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args();print(run(a.helper.resolve(),a.out)['classification'])
