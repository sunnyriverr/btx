from pathlib import Path
import os,sys,json,subprocess,tarfile,shutil,time,selectors,signal,hashlib
from checkpoint import sha,restore_timestamps,verify_restored,create
HEAD='1e2f8b5f12295002334d3390c12cac0bb4ae2aff';ARCHIVE='4e808f8daa32bba48561d5d87b05a7743d1f0cba12d75333794f0acebdcb3013'
w=Path(os.environ['GITHUB_WORKSPACE']);P=w/'controls/contrib/devtools/windows-main-preflight/governor-repair';out=w/'records';out.mkdir(exist_ok=True)
r={'source':HEAD,'complete':False,'commands':[],'scope':'Native POSIX actual governor preservation and seed transport, no wallet/node/production'};restored=False

def save():(out/'result.json').write_text(json.dumps(r,indent=2)+'\n')
def run(cmd,label,limit=120,cwd=None,expected=0):
 p=subprocess.Popen([str(x) for x in cmd],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,cwd=cwd,start_new_session=True);start=time.monotonic();budget_stop=None;sel=selectors.DefaultSelector();sel.register(p.stdout,selectors.EVENT_READ)
 with (out/(label+'.log')).open('wb') as f:
  while p.poll() is None or sel.get_map():
   for key,_ in sel.select(.5):
    block=os.read(key.fileobj.fileno(),65536)
    if not block:sel.unregister(key.fileobj);continue
    f.write(block);f.flush()
    if label!='accepted-files':sys.stdout.buffer.write(block);sys.stdout.flush()
   if time.monotonic()-start>limit or shutil.disk_usage(w).free<2*1024**3:
    budget_stop='TIME_BUDGET' if time.monotonic()-start>limit else 'DISK_RESERVE'
    try:os.killpg(p.pid,signal.SIGTERM)
    except ProcessLookupError:pass
    try:p.wait(65 if label.endswith('-native') else 10)
    except subprocess.TimeoutExpired:
     try:os.killpg(p.pid,signal.SIGKILL)
     except ProcessLookupError:pass
     p.wait()
    for key in list(sel.get_map().values()):sel.unregister(key.fileobj)
    break
  p.wait()
 r['commands'].append({'step':label,'exit':p.returncode,'seconds':round(time.monotonic()-start,3),'budget_stop':budget_stop});save()
 if budget_stop or p.returncode!=expected:raise RuntimeError(label+' exit '+str(p.returncode))
 return (out/(label+'.log')).read_text(errors='replace')

def freeze_plan(phase):
 run(['cmake','-P',build/'CMakeFiles/VerifyGlobs.cmake'],phase+'-verify-globs',120,cwd=build)
 plan=out/(phase+'-full-generated.ninja');shutil.copy2(build/'build.ninja',plan);assert sha(plan)==sha(build/'build.ninja')
 text=run(['ninja','-C',build,'-f',plan,'-n','btx-modeld'],phase+'-dry-run',120,cwd=build)
 actions=[v for v in text.splitlines() if v.startswith('[')];r[phase+'_plan']={'graph_sha256':sha(plan),'actions':actions};save()
 assert len(actions)<=100 and 'Re-running CMake' not in text,actions
 return plan

def native(phase):
 target=out/(phase+'-native.json')
 run([sys.executable,P/'test-governor-permit.py','--helper',w/'binaries'/phase/'btx-modeld','--output',target],phase+'-native',360,expected=1 if phase=='baseline' else 0)
 result=json.loads(target.read_text());r[phase+'_native']=result;save()
 assert result['clean_shutdown'] and result['private_runtime_removed']
 assert result['helper_sha256']==sha(w/'binaries'/phase/'btx-modeld')
 required=['valid_pause','valid_pause_second_model','same_first_model_recovery','same_second_model_recovery','fresh_enabled_acquisition']
 assert all(result['controls'][key]['passed'] for key in required)
 if phase=='baseline':assert result['status']=='FAIL' and set(result['failures'])=={'malformed_permit_enabled_preservation','unreadable_permit_enabled_preservation'}
 else:assert result['status']=='PASS' and not result['failures'] and result['controls']['malformed_pause']['passed'] and result['controls']['unreadable_pause']['passed']

try:
 m=json.loads((w/'saved-checkpoint/manifest.json').read_text());arc=w/'saved-checkpoint/build-state.tar.gz'
 assert sha(arc)==ARCHIVE==m['archive_sha256'] and m['identity']['source']==HEAD
 assert m['workspace']==str(w) and shutil.disk_usage(w).free>10*1024**3
 with tarfile.open(arc) as archive:archive.extractall(w,filter='data')
 restore_timestamps(w,m);verify_restored(w,m);restored=True;r['checkpoint_verified']=True;save()
 source=w/'product';accepted=w/'accepted-source';build=w/'gui-pilot-runtime/qtbuild'
 assert run(['git','rev-parse','HEAD'],'accepted-head',cwd=accepted).strip()==HEAD
 files=run(['git','ls-files'],'accepted-files',cwd=accepted).splitlines();changed=[]
 for name in files:
  a=accepted/name;b=source/name
  same=(a.is_symlink() and b.is_symlink() and os.readlink(a)==os.readlink(b)) or (not a.is_symlink() and b.is_file() and not b.is_symlink() and sha(a)==sha(b))
  if not same:
   b.parent.mkdir(parents=True,exist_ok=True)
   if b.is_symlink():b.unlink()
   if a.is_symlink():b.symlink_to(os.readlink(a))
   else:shutil.copy2(a,b)
   changed.append(name)
  if not a.is_symlink():os.chmod(b,a.stat().st_mode&0o777)
  assert (a.is_symlink() and b.is_symlink() and os.readlink(a)==os.readlink(b)) or (not a.is_symlink() and sha(a)==sha(b)),name
 r['baseline_restored_files']=changed
 if (source/'.git').exists():shutil.rmtree(source/'.git')
 shutil.copytree(accepted/'.git',source/'.git')
 assert 'OpenSSL 3.5.9' in run([w/'gui-pilot-runtime/openssl/bin/openssl','version'],'openssl')
 assert run(['g++','-dumpfullversion'],'gcc').strip()=='11.4.0'
 assert '3.31.6' in run(['cmake','--version'],'cmake')
 manifest=json.loads((P/'source-manifest.json').read_text());assert sha(source/'src/modelnet/helper.cpp')==manifest['baseline_sha256'];assert sha(P/'helper.cpp')==manifest['candidate_sha256']
 generated=build/'src/matmul-rc-production-golden-manifest-data.h'
 header_before={'sha256':sha(generated),'mtime_ns':generated.stat().st_mtime_ns} if generated.exists() else None
 run(['cmake','-S',source,'-B',build],'baseline-configure',180)
 if header_before and sha(generated)==header_before['sha256']:
  os.utime(generated,ns=(generated.stat().st_atime_ns,header_before['mtime_ns']))
  r['unchanged_generated_header_mtime_preserved']=header_before;save()
 plan=freeze_plan('baseline');run(['ninja','-C',build,'-f',plan,'-j2','btx-modeld'],'baseline-build',600)
 dest=w/'binaries/baseline';dest.mkdir(parents=True);shutil.copy2(build/'bin/btx-modeld',dest/'btx-modeld')
 native('baseline')
 shutil.copyfile(P/'helper.cpp',source/'src/modelnet/helper.cpp')
 r['candidate_helper_source_sha256']=sha(source/'src/modelnet/helper.cpp');assert r['candidate_helper_source_sha256']==manifest['candidate_sha256'];save()
 plan=freeze_plan('candidate');run(['ninja','-C',build,'-f',plan,'-j2','btx-modeld'],'candidate-build',600)
 dest=w/'binaries/candidate';dest.mkdir(parents=True);shutil.copy2(build/'bin/btx-modeld',dest/'btx-modeld')
 native('candidate');r['complete']=True;r['status']='NATIVE_POSIX_GOVERNOR_BEFORE_AFTER_PASS'
except Exception as error:r['status']='INCOMPLETE';r['error']=repr(error);print('QUALIFICATION ERROR',repr(error),flush=True)
finally:
 if restored:
  try:r['checkpoint_sha256']=create(w,w/'resume-checkpoint',{'source':HEAD,'purpose':'governor permit native qualification','intended_helper_sha256':sha(P/'helper.cpp'),'actual_source_helper_sha256':sha(w/'product/src/modelnet/helper.cpp'),'qualification_state':r.get('status','INCOMPLETE')})['archive_sha256']
  except Exception as error:r['checkpoint_error']=repr(error)
 save()
raise SystemExit(0 if r['complete'] else 1)
