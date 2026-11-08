from pathlib import Path
import os,sys,json,subprocess,time,hashlib,tarfile,shutil,signal,re
w=Path(os.environ['GITHUB_WORKSPACE']);out=w/'chunk-records';out.mkdir(exist_ok=True);payload=w/'chunk-checkpoint';payload.mkdir(exist_ok=True);bins=w/'chunk-binaries';bins.mkdir(exist_ok=True);roots=[w/'product',w/'mac-config-build'];state={'btx_compile_started':False,'node_started':False,'samples':0,'peak_owned_rss_bytes':0,'source':'36ab43008cac48aa5c8410e4b70d90a249196a33','bound_seconds':1200};compile_proc=None;start=time.monotonic()
def save():(out/'chunk-result.json').write_text(json.dumps(state,indent=2)+'\n')
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
from process_tracker import OwnedProcesses
trackers={}
def group_empty(proc):
 return not trackers[proc.pid].update()['processes']
def group_stop(proc):
 return trackers[proc.pid].stop()
def inventory():
 result={};total=0
 for root in roots:
  if not root.exists():continue
  for p in [root,*root.rglob('*')]:
   rel=p.relative_to(w)
   if '.git' in rel.parts:continue
   st=p.lstat();v={'mode':st.st_mode&0o777,'mtime_ns':st.st_mtime_ns}
   if p.is_symlink():
    target=os.readlink(p);resolved=p.resolve();assert any(resolved.is_relative_to(r.resolve()) for r in roots),'Checkpoint external symlink: '+str(rel);v.update(type='symlink',target=target,archive_target=os.path.relpath(resolved,p.parent.resolve()) if Path(target).is_absolute() else target)
   elif p.is_dir():v['type']='dir'
   elif p.is_file():v.update(type='file',sha256=sha(p),bytes=st.st_size);total+=st.st_size
   else:raise RuntimeError('Non-regular checkpoint entry '+str(rel))
   result[str(rel)]=v
 assert total<11*1024**3,'Checkpoint live-tree size exceeds planned source+build bound'
 return result,total
def write_checkpoint(inv,total):
 generation='after' if state.get('baseline_checkpoint_valid') else 'baseline'
 destination=payload/generation;assert not destination.exists()
 free=shutil.disk_usage(w).free;assert free>16*1024**3,'Insufficient room for compressed checkpoint+reserve'
 input_manifest=out/'checkpoint-input.json';input_manifest.write_text(json.dumps(inv))
 cmd=[sys.executable,str(Path(__file__).resolve()),'archive-only',str(input_manifest),str(w/'.mac-checkpoint-candidate.tar.gz')]
 with (out/'checkpoint.log').open('w') as log:
  cp=subprocess.Popen(cmd,cwd=w,env=dict(os.environ,COPYFILE_DISABLE='1'),stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
  trackers[cp.pid]=OwnedProcesses(cp)
  began=time.monotonic()
  while cp.poll() is None:
   candidate=w/'.mac-checkpoint-candidate.tar.gz'
   if time.monotonic()-began>240 or shutil.disk_usage(w).free<10*1024**3 or (candidate.exists() and candidate.stat().st_size>4*1024**3):
    group_stop(cp);raise RuntimeError('Checkpoint creation time/disk/size bound')
   time.sleep(1)
  assert cp.returncode==0
 archive=w/'.mac-checkpoint-candidate.tar.gz';assert archive.stat().st_size<4*1024**3
 with tarfile.open(archive) as t:
  members=t.getmembers();assert len(members)==len(inv)
  for m in members:
   assert not Path(m.name).is_absolute() and '..' not in Path(m.name).parts and Path(m.name).parts[0] in ['product','mac-config-build']
 digest=sha(archive);destination.mkdir()
 (destination/'inventory.json').write_text(json.dumps(inv,indent=2))
 receipt={'sha256':digest,'bytes':archive.stat().st_size,'entries':len(inv),'live_bytes':total,'inventory_sha256':sha(destination/'inventory.json'),'generation':generation}
 archive.replace(destination/'checkpoint.tar.gz')
 (destination/'receipt.json').write_text(json.dumps(receipt,indent=2))
 assert sha(destination/'checkpoint.tar.gz')==digest
 pointer=payload/'selected.tmp';pointer.write_text(json.dumps(receipt,indent=2));pointer.replace(payload/'selected.json')
 state['checkpoint']=receipt;state['checkpoint_retained_locally_on_runner']=True


def archive_worker(inv,archive):
 def accepted(info):
  if '.git' in Path(info.name).parts:return None
  assert info.name.rstrip('/') in inv
  if info.issym():
   target=inv[info.name]['archive_target'];assert not Path(target).is_absolute()
   resolved=(w/info.name).parent.joinpath(target).resolve()
   assert any(resolved.is_relative_to(r.resolve()) for r in roots)
   info.linkname=target
  return info
 with tarfile.open(archive,'w:gz',compresslevel=1) as t:
  for root in roots:
   if root.exists():t.add(root,arcname=root.name,filter=accepted)
if len(sys.argv)>1 and sys.argv[1]=='archive-only':
 archive_worker(json.loads(Path(sys.argv[2]).read_text()),Path(sys.argv[3]));raise SystemExit(0)

try:
 assert all(p.exists() for p in roots)
 gate=json.loads((w/'restore-records/restore-result.json').read_text())
 summary=json.loads((w/'restore-records/resume-summary.json').read_text())
 assert gate.get('complete') and summary['head']==state['source']
 assert summary['command_graph_equal_to_saved'] and summary['original_checkpoint_unchanged']
 assert summary['other_retained_objects_not_scheduled']>=json.loads(Path(__file__).with_name('expected.json').read_text())['target_object_count']-8
 assert set(summary['retained_objects_scheduled'])<=set(json.loads(Path(__file__).with_name('expected.json').read_text())['allowed_generated_rebuilds'])
 assert subprocess.check_output(['git','-C',str(roots[0]),'rev-parse','HEAD'],text=True).strip()==state['source']
 assert not subprocess.check_output(['git','-C',str(roots[0]),'status','--porcelain'],text=True).strip()
 state['resume_gate']=summary
 # Reject unsupported real-tree links before committing to a long compile.
 before,total=inventory();write_checkpoint(before,total);state['baseline_checkpoint_valid']=True;state['initial_inventory_entries']=len(before);state['initial_tree_bytes']=total;save()
 assert shutil.disk_usage(w).free>16*1024**3
 targets=json.loads(Path(__file__).with_name('targets.json').read_text())
 args=['ninja','-C',str(roots[1]),'-j1',*targets];state['compile_args']=args
 with (out/'compile.log').open('w') as log,(out/'resources.jsonl').open('w') as samples:
  proc=subprocess.Popen(args,stdout=log,stderr=subprocess.STDOUT,start_new_session=True);compile_proc=proc;trackers[proc.pid]=OwnedProcesses(proc);state['btx_compile_started']=True;begin=time.monotonic();reason=None
  try:
   while proc.poll() is None:
    observed=trackers[proc.pid].update();rss=observed['rss_bytes']
    free=shutil.disk_usage(w).free;elapsed=time.monotonic()-begin;state['samples']+=1;state['peak_owned_rss_bytes']=max(state['peak_owned_rss_bytes'],rss);state['last_elapsed_seconds']=elapsed
    samples.write(json.dumps({'seconds':round(elapsed,2),'owned_rss_bytes':rss,'owned_processes':observed['processes'],'free_disk_bytes':free})+'\n');samples.flush();save()
    if elapsed>=state['bound_seconds']:reason='time_limit'
    elif rss>int(5.5*1024**3):reason='memory_limit'
    elif free<10*1024**3:reason='disk_limit'
    if reason:group_stop(proc);break
    if state['samples']%30==0:print('CHUNK',round(elapsed), 'seconds; peak RSS',state['peak_owned_rss_bytes'],flush=True)
    time.sleep(2)
  finally:
   if not group_empty(proc):group_stop(proc)
  state['compile_exit']=proc.wait();state['stop_reason']=reason or ('completed' if proc.returncode==0 else 'compile_failure');state['compile_seconds']=round(time.monotonic()-begin,2);state['compile_success']=proc.returncode==0
except Exception as e:
 import traceback
 state['error']=repr(e);(out/'exception.log').write_text(traceback.format_exc())
finally:
 # Independent available outputs first; no node/helper executable is launched.
 safe=compile_proc is None or group_empty(compile_proc);state['observed_owned_processes_stopped']=safe
 finished={}
 try:
  assert safe,'Live owned group: no copying outputs'
  if (roots[1]/'bin').exists():
   for p in (roots[1]/'bin').iterdir():
    if p.is_file() and not p.is_symlink() and p.name.startswith('btx') and os.access(p,os.X_OK):finished[p.name]={'sha256':sha(p),'bytes':p.stat().st_size,'mode':p.stat().st_mode&0o777}
  assert sum(x['bytes'] for x in finished.values())<2*1024**3
  with tarfile.open(bins/'available-executables.tar.gz','w:gz',compresslevel=1) as t:
   for name in finished:t.add(roots[1]/'bin'/name,arcname=name)
  (bins/'manifest.json').write_text(json.dumps(finished,indent=2));state['available_executables']=finished;state['binary_artifact_sha256']=sha(bins/'available-executables.tar.gz')
 except Exception as e:state['binary_retention_error']=repr(e)
 try:
  assert safe,'Live owned group: baseline retained; no mutable checkpoint'
  inv,total=inventory();write_checkpoint(inv,total)
 except Exception as e:state['checkpoint_error']=repr(e)
 state['elapsed_total_seconds']=round(time.monotonic()-start,2);save();(payload/'result.json').write_text(json.dumps(state,indent=2))
# A bounded/failed chunk is not relabelled as a successful BTX build.
sys.exit(0 if state.get('compile_success') and not state.get('checkpoint_error') and not state.get('binary_retention_error') else 1)
