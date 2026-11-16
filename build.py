from pathlib import Path
import os,sys,json,subprocess,tarfile,shutil,time,selectors,signal,hashlib
from checkpoint import sha,restore_timestamps,verify_restored,create
HEAD='1e2f8b5f12295002334d3390c12cac0bb4ae2aff';OLD=HEAD;ARCHIVE='214c4b13426bf50fbe17a8dd64d1a7f108a96eb8b8162fcfa2f147a35c98880e'
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
 restore_timestamps(w,m);verify_restored(w,m);restored=True;r['checkpoint_verified']=True;r['checkpoint_identity']=m['identity'];save()
 source=w/'product';accepted=w/'accepted-source';build=w/'gui-pilot-runtime/qtbuild'
 assert run(['git','rev-parse','HEAD'],'accepted-head',cwd=accepted).strip()==HEAD
 names=run(['git','ls-files'],'accepted-files',cwd=accepted).splitlines();current=set(names)
 # Preserve generated/untracked cache files; remove only audited deleted tracked files.
 for entry in []:
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
   os.utime(b,None) if not b.is_symlink() else None
  if not a.is_symlink():os.chmod(b,a.stat().st_mode & 0o777)
  assert (b.is_symlink() and a.is_symlink() and os.readlink(a)==os.readlink(b)) or (not a.is_symlink() and sha(a)==sha(b) and (a.stat().st_mode&0o777)==(b.stat().st_mode&0o777)),name
 r['changed_source_files']=changed;r['source_verified']=True
 if (source/'.git').exists():shutil.rmtree(source/'.git')
 shutil.copytree(accepted/'.git',source/'.git')
 assert 'OpenSSL 3.5.9' in run([w/'gui-pilot-runtime/openssl/bin/openssl','version'],'openssl')
 assert run(['g++','-dumpfullversion'],'gcc').strip()=='11.4.0'
 assert '3.31.6' in run(['cmake','--version'],'cmake')


 composition=json.loads((w/'composition-receipt.json').read_text())
 assert composition['base']==HEAD
 for name,expected_hash in composition['files'].items():
  a=w/'composition'/name
  assert sha(a)==expected_hash,name
  shutil.copy2(a,source/name);os.utime(source/name,None)
  assert sha(source/name)==expected_hash
 r['composition_verified']=True;r['composition']=composition;save()
 # Explicitly exclude the parked publisher-history work from this independent target.
 for name in ('src/modelnet/feed.cpp','src/modelnet/feed.h','src/test/modelnet_feed_tests.cpp'):
  assert sha(source/name)==sha(accepted/name),name
 r['base_feed_restored']=True
 run(['cmake','-S',source,'-B',build,'-DBUILD_TESTS=ON'],'settings-configure',180)
 run(['cmake','-P',build/'CMakeFiles/VerifyGlobs.cmake'],'settings-globs',120,cwd=build)
 observed=build/'settings-observed.ninja';shutil.copy2(build/'build.ninja',observed)
 dry=run(['ninja','-C',build,'-f',observed,'-n','test_btx','btx-modeld'],'settings-plan',120)
 assert 'Re-running CMake' not in dry
 steps=[x for x in dry.splitlines()if x.startswith('[')]
 assert 0<len(steps)<=3000,'Unexpected plan size: '+str(len(steps))
 r['planned_steps']=len(steps)
 r['build_flags']=[x for x in (build/'CMakeCache.txt').read_text().splitlines()if x.startswith(('BUILD_TESTS:','WITH_MODELNET:','ENABLE_WALLET:','CMAKE_BUILD_TYPE:','CMAKE_CXX_COMPILER:','OPENSSL_'))]
 registration=run(['ctest','--test-dir',build,'-N','-R','^modelnet_(watch|first_run)_tests$'],'settings-registration',60)
 assert 'modelnet_watch_tests' in registration and 'modelnet_first_run_tests' in registration
 # Ninja query is nonexecuting and proves both requested actual targets exist.
 run(['ninja','-C',build,'-f',observed,'-t','query','test_btx','btx-modeld'],'settings-targets',60)
 r['resources']=run(['bash','-c','nproc; free -b; df -B1 .'],'settings-resources',30)
 r['product_compile_executed']=False;r['product_tests_executed']=False
 r['complete']=True;save()
except Exception as e:
 r['error']=repr(e);print('PILOT ERROR',repr(e),flush=True)
finally:
 save()
raise SystemExit(0 if r['complete'] and not r.get('error') else 1)
