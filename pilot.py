"""Verify configured cache, bounded helper-only compile, retain outputs on failure."""
from pathlib import Path
import os,json,sys,subprocess,hashlib,shutil,tarfile,signal,time,selectors
from checkpoint import sha,restore_timestamps,verify_restored,create
HEAD='f40eb37a6fb8b665340fe92a2f248ff3f23ec7f6'
ARCHIVE='b5915b3c1574027c664d97789c1cd2201988080f32b62d1f74618492bfb904b1'
def build_ready(r):
 return all(r.get(k) is True for k in ['archive_verified','restored','source_verified','toolchain_verified','plan_verified']) and r.get('source')==HEAD and r.get('planned_actions',1000)<=60

def main():
 w=Path(os.environ['GITHUB_WORKSPACE']);out=w/'records';out.mkdir(exist_ok=True)
 r={'source':HEAD,'compiled':False,'commands':[]};restored=False
 def save():(out/'build-result.json').write_text(json.dumps(r,indent=2)+'\n')
 def run(args,label,limit=120,cwd=None):
  p=subprocess.Popen(list(map(str,args)),stdout=subprocess.PIPE,stderr=subprocess.STDOUT,cwd=cwd,start_new_session=True)
  start=time.monotonic();stop=None;last=0;chunks=[];sel=selectors.DefaultSelector();sel.register(p.stdout,selectors.EVENT_READ)
  with (out/(label+'.log')).open('wb') as f:
   while p.poll() is None or sel.get_map():
    for key,_ in sel.select(.5):
     data=os.read(key.fileobj.fileno(),65536)
     if not data:sel.unregister(key.fileobj);continue
     f.write(data);f.flush();chunks.append(data);sys.stdout.buffer.write(data);sys.stdout.flush()
    elapsed=time.monotonic()-start
    if elapsed>limit:stop='timeout'
    if shutil.disk_usage(w).free<2*1024**3:stop='disk_reserve'
    if elapsed-last>=15:
     last=elapsed
     with (out/'resources.jsonl').open('a') as z:z.write(json.dumps({'step':label,'seconds':elapsed,'disk_free':shutil.disk_usage(w).free,'meminfo':Path('/proc/meminfo').read_text().splitlines()[:4]})+'\n')
    if stop and p.poll() is None:
     os.killpg(p.pid,signal.SIGTERM)
     try:p.wait(10)
     except subprocess.TimeoutExpired:os.killpg(p.pid,signal.SIGKILL);p.wait()
   p.wait()
  r['commands'].append({'label':label,'exit':p.returncode,'stop':stop,'seconds':time.monotonic()-start});save()
  if p.returncode or stop:raise RuntimeError(label+': '+str(stop or p.returncode))
  return b''.join(chunks).decode(errors='replace')
 try:
  assert hasattr(tarfile,'data_filter') and shutil.disk_usage(w).free>=10*1024**3
  saved=w/'saved-checkpoint';m=json.loads((saved/'manifest.json').read_text());tar=saved/'build-state.tar.gz'
  assert sha(tar)==ARCHIVE==m['archive_sha256'] and m['identity']['source']==HEAD
  assert Path(m['workspace'])==w and not (w/'product').exists()
  r['archive_verified']=True
  with tarfile.open(tar) as t:t.extractall(w,filter='data')
  restore_timestamps(w,m);verify_restored(w,m);restored=True;r['restored']=True;r['objects_restored']=sum(k.endswith('.o') for k in m['rows']);save()
  src=w/'product';accepted=w/'accepted-source';build=w/'gui-pilot-runtime/qtbuild'
  assert run(['git','rev-parse','HEAD'],'accepted-head',cwd=accepted).strip()==HEAD
  assert not run(['git','status','--porcelain'],'accepted-clean',cwd=accepted).strip()
  names=run(['git','ls-files'],'accepted-files',cwd=accepted).splitlines()
  for name in names:
   a=accepted/name;b=src/name
   if a.is_symlink():assert b.is_symlink() and os.readlink(a)==os.readlink(b),name
   else:assert b.is_file() and not b.is_symlink() and sha(a)==sha(b) and a.stat().st_mode&0o777==b.stat().st_mode&0o777,name
  shutil.copytree(accepted/'.git',src/'.git')
  assert not run(['git','status','--porcelain','--untracked-files=no'],'product-clean',cwd=src).strip();r['source_verified']=True
  assert run(['g++','-dumpfullversion'],'gcc').strip()=='11.4.0'
  assert 'OpenSSL 3.5.9' in run([w/'gui-pilot-runtime/openssl/bin/openssl','version'],'openssl')
  assert '3.31.6' in run(['cmake','--version'],'cmake')
  r['toolchain_verified']=True
  cache=(build/'CMakeCache.txt').read_text();assert 'WITH_MODELNET:BOOL=ON' in cache
  glob=run(['cmake','-P',build/'CMakeFiles/VerifyGlobs.cmake'],'verify-globs',cwd=build)
  assert 'GLOB mismatch!' not in glob
  observed=out/'observed.ninja';shutil.copy2(build/'build.ninja',observed)
  dry=run(['ninja','-C',build,'-f',observed,'-d','explain','-n','btx-modeld'],'dry-plan')
  steps=[l for l in dry.splitlines() if l.startswith('[')];r['planned_actions']=len(steps);r['plan']=steps
  assert steps and len(steps)<=60 and 'Re-running CMake' not in dry and 'Re-checking globbed' not in dry
  r['plan_verified']=True;assert build_ready(r);save()
  r['compile_started']=True;save()
  run(['cmake','--build',build,'--parallel','2','--target','btx-modeld'],'helper-build',1200)
  binary=build/'bin/btx-modeld';assert binary.is_file();candidate=w/'candidate';candidate.mkdir(exist_ok=True)
  shutil.copy2(binary,candidate/'btx-modeld');digest=sha(candidate/'btx-modeld')
  (candidate/'binaries.sha256').write_text(digest+'  candidate/btx-modeld\n')
  r['compiled']=True;r['helper_sha256']=digest
  (candidate/'source.json').write_text(json.dumps({'source':HEAD,'helper_sha256':digest,'target':'btx-modeld','toolchain':'Ubuntu22/GCC11.4/OpenSSL3.5.9/CMake3.31.6','tests_run':False},indent=2))
  run(['ldd',candidate/'btx-modeld'],'ldd');assert 'not found' not in (out/'ldd.log').read_text()
 except Exception as e:r['error']=repr(e)
 finally:
  if restored:
   try:
    m2=create(w,w/'resume-checkpoint',{'source':HEAD,'purpose':'bounded integrated helper compile; see result for completion'})
    r['retained_checkpoint_sha256']=m2['archive_sha256']
   except Exception as e:r['retention_error']=repr(e)
  save()
 return 0 if r.get('compiled') and not r.get('error') and not r.get('retention_error') else 1
if __name__=='__main__':sys.exit(main())
