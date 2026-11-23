from pathlib import Path
import os,sys,json,subprocess,tarfile,shutil,time,selectors,signal,hashlib
from checkpoint import sha,restore_timestamps,verify_restored,create
HEAD='d9a9480484cea303649f3eab1e82f8e3d7572c21';OLD='7d65025bb3bff27e4f6c2fdc95f33e4b859a2df5';ARCHIVE='2fae3dc0b4b51c4c5acd08a30ec5070d4aaa2705ab7a237854158edb58db5170'
w=Path(os.environ['GITHUB_WORKSPACE']);out=w/'records';out.mkdir(exist_ok=True);r={'source':HEAD,'checkpoint_source':OLD,'complete':False,'commands':[]};restored=False

def save():(out/'build-result.json').write_text(json.dumps(r,indent=2)+'\n')
def run(cmd,label,limit=120,cwd=None,expected=0):
 p=subprocess.Popen([str(x) for x in cmd],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,cwd=cwd,start_new_session=True);start=time.monotonic();data=[];sel=selectors.DefaultSelector();sel.register(p.stdout,selectors.EVENT_READ)
 with (out/(label+'.log')).open('wb') as f:
  while p.poll() is None or sel.get_map():
   for key,_ in sel.select(.5):
    chunk=os.read(key.fileobj.fileno(),65536)
    if not chunk:sel.unregister(key.fileobj);continue
    f.write(chunk);f.flush();data.append(chunk);sys.stdout.buffer.write(chunk);sys.stdout.flush()
   if (time.monotonic()-start>limit or shutil.disk_usage(w).free<2*1024**3) and p.poll() is None:
    os.killpg(p.pid,signal.SIGTERM)
    try:p.wait(10)
    except subprocess.TimeoutExpired:os.killpg(p.pid,signal.SIGKILL);p.wait()
  p.wait()
 r['commands'].append({'step':label,'exit':p.returncode,'seconds':time.monotonic()-start});save()
 if p.returncode!=expected:raise RuntimeError(label+' exit '+str(p.returncode))
 return b''.join(data).decode(errors='replace')
try:
 m=json.loads((w/'saved-checkpoint/manifest.json').read_text());arc=w/'saved-checkpoint/build-state.tar.gz'
 assert sha(arc)==ARCHIVE==m['archive_sha256'] and m['identity']['source']==OLD
 assert m['workspace']==str(w) and shutil.disk_usage(w).free>10*1024**3
 with tarfile.open(arc) as t:t.extractall(w,filter='data')
 restore_timestamps(w,m);verify_restored(w,m);restored=True;r['checkpoint_verified']=True;save()
 source=w/'product';accepted=w/'accepted-source';build=w/'gui-pilot-runtime/qtbuild'
 assert run(['git','rev-parse','HEAD'],'accepted-head',cwd=accepted).strip()==HEAD
 names=run(['git','ls-files'],'accepted-files',cwd=accepted).splitlines();current=set(names)
 # Preserve generated/untracked cache files; remove only audited deleted tracked files.
 for entry in json.loads((w/'removed.json').read_text()):
  if entry['status']=='removed':
   b=source/entry['filename']
   if b.exists() or b.is_symlink():b.unlink()
 changed=[]
 for name in names:
  a=accepted/name;b=source/name
  same=(a.is_symlink() and b.is_symlink() and os.readlink(a)==os.readlink(b)) or (not a.is_symlink() and b.is_file() and not b.is_symlink() and sha(a)==sha(b))
  if not same:
   b.parent.mkdir(parents=True,exist_ok=True)
   if b.is_symlink():b.unlink()
   if a.is_symlink():b.symlink_to(os.readlink(a))
   else:shutil.copy2(a,b)
   changed.append(name)
  if not a.is_symlink():os.chmod(b,a.stat().st_mode & 0o777)
  assert (b.is_symlink() and a.is_symlink() and os.readlink(a)==os.readlink(b)) or (not a.is_symlink() and sha(a)==sha(b) and (a.stat().st_mode&0o777)==(b.stat().st_mode&0o777)),name
 assert set(changed) == {row['filename'] for row in json.loads((w/'source-delta.json').read_text())}
 r['changed_source_files']=changed;r['source_verified']=True
 r['patch_sha256']=sha(w/'candidate.patch')
 if (source/'.git').exists():shutil.rmtree(source/'.git')
 shutil.copytree(accepted/'.git',source/'.git')
 assert 'OpenSSL 3.5.9' in run([w/'gui-pilot-runtime/openssl/bin/openssl','version'],'openssl')
 assert run(['g++','-dumpfullversion'],'gcc').strip()=='11.4.0'
 assert '3.31.6' in run(['cmake','--version'],'cmake')
 extra='\n# Qualification-only target, excluded from the product patch.\nadd_executable(rehost-regression "${CMAKE_SOURCE_DIR}/../regression.cpp")\ntarget_link_libraries(rehost-regression core_interface)\ntarget_link_btx_linux_archive_group(rehost-regression bitcoin_modelnet ${BTX_BASE_ARCHIVES})\n'
 with (source/'src/modelnet/CMakeLists.txt').open('a') as f:f.write(extra)
 # Establish the baseline from accepted source, with the same maintained cases.
 run(['cmake','-S',source,'-B',build],'baseline-configure',180)
 run(['cmake','-P',build/'CMakeFiles/VerifyGlobs.cmake'],'baseline-verify-globs',120,cwd=build)
 dry=run(['ninja','-C',build,'-n','rehost-regression'],'baseline-dry',120)
 steps=[x for x in dry.splitlines() if x.startswith('[')];assert 0<len(steps)<=450,len(steps)
 run(['cmake','--build',build,'--parallel','2','--target','rehost-regression'],'baseline-build',1350)
 run([build/'bin/rehost-regression',w/'baseline-regression-data'],'baseline-regression',60,expected=1)
 baseline_log=(out/'baseline-regression.log').read_text();assert 'FAIL line' in baseline_log and 'ReadFileBytes(piece_path) == expected' in baseline_log and 'file sha384 mismatch' in baseline_log and 'CASE ABORT' not in baseline_log and 'ASSERTIONS=' in baseline_log
 run(['git','apply','--check',w/'candidate.patch'],'patch-check',cwd=source)
 run(['git','apply',w/'candidate.patch'],'patch-apply',cwd=source)
 run(['cmake','-S',source,'-B',build],'candidate-configure',180)
 globs=run(['cmake','-P',build/'CMakeFiles/VerifyGlobs.cmake'],'candidate-verify-globs',120,cwd=build)
 assert 'GLOB mismatch!' not in globs
 observed=out/'candidate-observed.ninja';shutil.copy2(build/'build.ninja',observed)
 dry=run(['ninja','-C',build,'-f',observed,'-d','explain','-n','rehost-regression'],'candidate-dry',120)
 assert 'Re-running CMake' not in dry
 steps=[x for x in dry.splitlines() if x.startswith('[')];assert 0<len(steps)<=450,len(steps)
 r['planned_steps']=len(steps);save()
 dest=w/'binaries/candidate';dest.mkdir(parents=True)
 run(['cmake','--build',build,'--parallel','2','--target','rehost-regression'],'candidate-build',1200)
 for name in ('rehost-regression',):shutil.copy2(build/'bin'/name,dest/name)
 r['binary_sha256']={f.name:sha(f) for f in dest.iterdir()};save()
 run([dest/'rehost-regression',w/'candidate-regression-data'],'candidate-regression',60)
 r['complete']=True
except Exception as e:r['error']=repr(e);print('BUILD ERROR',repr(e),flush=True)
finally:
 save()
raise SystemExit(0 if r['complete'] and not r.get('error') and not r.get('retention_error') else 1)
