from pathlib import Path
import os,sys,json,subprocess,tarfile,shutil,time,selectors,signal,hashlib
from checkpoint import sha,restore_timestamps,verify_restored,create
HEAD='61f13b8870ed98c7b10db2e32c04fb647023f4ef';OLD='f40eb37a6fb8b665340fe92a2f248ff3f23ec7f6';ARCHIVE='f273aa4bdabef3aff92dde54b55aabd8b36f54cd5243529c794effe7d6b47852'
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
 for entry in json.loads((w/'source-delta.json').read_text())['files']:
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
 r['changed_source_files']=changed;r['source_verified']=True
 if (source/'.git').exists():shutil.rmtree(source/'.git')
 shutil.copytree(accepted/'.git',source/'.git')
 assert 'OpenSSL 3.5.9' in run([w/'gui-pilot-runtime/openssl/bin/openssl','version'],'openssl')
 assert run(['g++','-dumpfullversion'],'gcc').strip()=='11.4.0'
 assert '3.31.6' in run(['cmake','--version'],'cmake')
 extra='''\n# Local qualification executable; not part of the proposed product patch.\nadd_executable(relay-expiry-check "${CMAKE_SOURCE_DIR}/../expiry_test.cpp")\ntarget_link_libraries(relay-expiry-check core_interface)\ntarget_link_btx_linux_archive_group(relay-expiry-check bitcoin_modelnet ${BTX_BASE_ARCHIVES})\nif(RELAY_CANDIDATE)\n target_compile_definitions(relay-expiry-check PRIVATE CANDIDATE)\nendif()\n'''
 with (source/'src/modelnet/CMakeLists.txt').open('a') as f:f.write(extra)
 for variant in ['baseline','candidate']:
  if variant=='candidate':
   run(['git','apply','--check',w/'candidate.patch'],'patch-check',cwd=source)
   run(['git','apply',w/'candidate.patch'],'patch-apply',cwd=source)
  run(['cmake','-S',source,'-B',build,'-DRELAY_CANDIDATE='+('ON' if variant=='candidate' else 'OFF')],variant+'-configure',180)
  dry=run(['ninja','-C',build,'-n','btx-modeld','relay-expiry-check'],variant+'-dry',120)
  steps=[x for x in dry.splitlines() if x.startswith('[')];assert 0<len(steps)<=160,(variant,len(steps));r[variant+'_planned_steps']=len(steps);save()
  run(['cmake','--build',build,'--parallel','2','--target','btx-modeld','relay-expiry-check'],variant+'-build',1000)
  dest=w/'binaries'/variant;dest.mkdir(parents=True)
  for name in ['btx-modeld','relay-expiry-check']:shutil.copy2(build/'bin'/name,dest/name)
  r[variant+'_sha256']={f.name:sha(f) for f in dest.iterdir()};save()
  expiry=run([dest/'relay-expiry-check'],variant+'-expiry',30,expected=1 if variant=='baseline' else 0)
  if variant=='baseline':assert 'expired_active_after_cleanup=1' in expiry and 'FAIL expired connection cleanup must release active count' in expiry
  else:assert 'pending_expiry_cleanup=PASS forwarded=7 active=0' in expiry and 'PASS expiry cleanup' in expiry
 r['complete']=True
except Exception as e:r['error']=repr(e);print('BUILD ERROR',repr(e),flush=True)
finally:
 if restored:
  try:r['checkpoint_sha256']=create(w,w/'resume-checkpoint',{'source':HEAD,'candidate_patch_sha256':sha(w/'candidate.patch'),'purpose':'relay full-helper qualification'})['archive_sha256']
  except Exception as e:r['retention_error']=repr(e)
 save()
raise SystemExit(0 if r['complete'] and not r.get('error') and not r.get('retention_error') else 1)
