from pathlib import Path
import subprocess,os,signal,json,time,hashlib,shutil,tarfile
r=Path('records');r.mkdir(exist_ok=True);out=Path('retained');out.mkdir(exist_ok=True);began=time.monotonic();result={'source_pin':'61f13b8870ed98c7b10db2e32c04fb647023f4ef','targets':['btxd','btx-cli'],'parallel':2,'compile_budget_s':1800,'tests_invoked':False,'binaries_executed':False,'checkpoint_required':True};samples=[]
def memory():return int(next(l.split()[1] for l in Path('/proc/meminfo').read_text().splitlines() if l.startswith('MemAvailable:')))*1024
with (r/'build.log').open('w') as log:
 p=subprocess.Popen(['ninja','-C','build','-j2','btxd','btx-cli'],stdout=log,stderr=subprocess.STDOUT,start_new_session=True);reason=None
 while p.poll() is None:
  elapsed=time.monotonic()-began;free=shutil.disk_usage('.').free;mem=memory();samples.append({'seconds':round(elapsed,1),'free_disk':free,'available_RAM':mem})
  if elapsed>=1800:reason='TIME_BUDGET'
  if free<2*2**30 or mem<768*2**20:reason='RESOURCE_RESERVE'
  if reason:
   os.killpg(p.pid,signal.SIGINT)
   try:p.wait(timeout=20)
   except subprocess.TimeoutExpired:
    os.killpg(p.pid,signal.SIGTERM)
    try:p.wait(timeout=10)
    except subprocess.TimeoutExpired:os.killpg(p.pid,signal.SIGKILL);p.wait(timeout=10)
   break
  try:p.wait(timeout=15)
  except subprocess.TimeoutExpired:pass
  if len(samples)%4==0:
   tail=(r/'build.log').read_text(errors='replace').splitlines()[-1:];print('BUILD_PROGRESS',round(elapsed),tail,flush=True)
result.update(compile_exit=p.returncode,stop_reason=reason,compile_elapsed_s=round(time.monotonic()-began,2),samples=samples)
result['status']='BUILD_PASS' if p.returncode==0 else ('PARTIAL_RETAINED' if reason else 'COMPILER_FAILURE_RETAINED')
# Dry-run only: pending plan after actual compile, never a test or binary launch.
with (r/'remaining-dry-run.log').open('w') as log:subprocess.run(['ninja','-C','build','-n','btxd','btx-cli'],stdout=log,stderr=subprocess.STDOUT,check=True,timeout=120)
result['remaining_plan']=(r/'remaining-dry-run.log').read_text().splitlines()[-12:]
result['binary_sha256']={}
for name in result['targets']:
 f=Path('build/bin')/name
 if f.is_file():
  result['binary_sha256'][name]=hashlib.sha256(f.read_bytes()).hexdigest();shutil.copy2(f,out/name)
result['object_count']=sum(1 for p in Path('build').rglob('*.o'));result['build_bytes']=sum(p.stat().st_size for p in Path('build').rglob('*') if p.is_file());result['source_identity']=subprocess.check_output(['git','-C','source','rev-parse','HEAD'],text=True).strip();assert result['source_identity']==result['source_pin']
result['submodules']=subprocess.check_output(['git','-C','source','submodule','status','--recursive'],text=True)
result['source_files_sha256']={str(p.relative_to('source')):hashlib.sha256(p.read_bytes()).hexdigest() for p in Path('source').rglob('*') if p.is_file() and not p.is_symlink() and '.git' not in p.parts}
# Preserve source timestamps and matching build graph/objects in independent resumable checkpoint.
with (r/'checkpoint-pack.log').open('w') as log:subprocess.run(['tar','--exclude=source/.git','--exclude=source/.github','-I','gzip -1','-cf',str(out/'checkpoint.tar.gz'),'source','build'],stdout=log,stderr=subprocess.STDOUT,check=True,timeout=480)
f=out/'checkpoint.tar.gz';h=hashlib.sha256()
with f.open('rb') as stream:
 for chunk in iter(lambda:stream.read(2**20),b''):h.update(chunk)
result['checkpoint']={'name':f.name,'bytes':f.stat().st_size,'sha256':h.hexdigest(),'root':str(Path.cwd()),'source_git_metadata_included':False,'restore_contract':'Restore under identical source/build absolute paths; verify source hashes/pin/toolchain/cache before continuing, never execute based solely on archive name.'}
result['total_s']=round(time.monotonic()-began,2);(r/'build-result.json').write_text(json.dumps(result,indent=2)+'\n');(out/'producer.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if k!='samples'},indent=2),flush=True)
if p.returncode and not reason:raise SystemExit(1)
