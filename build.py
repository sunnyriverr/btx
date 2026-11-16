from pathlib import Path
import os,sys,json,subprocess,tarfile,shutil,time,selectors,signal,hashlib
from checkpoint import sha,restore_timestamps,verify_restored,create
HEAD='1e2f8b5f12295002334d3390c12cac0bb4ae2aff';OLD=HEAD;ARCHIVE='ba029ed497516ee984339eabbb3ab6728d30249feb2ab16d07f9153f820ede12'
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

 shutil.copy2(w/'maintained-feed-tests.cpp', source/'src/test/modelnet_feed_tests.cpp')
 run(['cmake','-S',source,'-B',build,'-DBUILD_TESTS=ON'],'integrated-configure',180)
 run(['cmake','-P',build/'CMakeFiles/VerifyGlobs.cmake'],'integrated-globs',120,cwd=build)
 observed=build/'feedstore-observed.ninja'; shutil.copy2(build/'build.ninja',observed)
 dry=run(['ninja','-C',build,'-f',observed,'-n','test_btx'],'integrated-plan',120)
 steps=[x for x in dry.splitlines() if x.startswith('[')]
 r['planned_steps']=len(steps)
 r['build_tests']= [x for x in (build/'CMakeCache.txt').read_text().splitlines() if x.startswith(('BUILD_TESTS:','WITH_MODELNET:','ENABLE_WALLET:'))]
 tests=run(['ctest','--test-dir',build,'-N','-R','^modelnet_feed(_restart)?_tests$'],'integrated-registration',120)
 assert 'modelnet_feed_tests' in tests and 'modelnet_feed_restart_tests' in tests

 assert 'Re-running CMake' not in dry
 r['resources']=run(['bash','-c','nproc; free -b; df -B1 .'],'resume-resources',30)
 available=int(next(x.split()[1] for x in Path('/proc/meminfo').read_text().splitlines() if x.startswith('MemAvailable:')))*1024
 workers=4 if os.cpu_count()>=4 and available>=8*1024**3 else 2
 r['workers']=workers; save()
 assert 0<len(steps)<=3000, 'Unexpected build size: '+str(len(steps))
 save()
 run(['ninja','-C',build,'-f',observed,'-j'+str(workers),'test_btx'],'baseline-build',1500)
 binary=build/'bin/test_btx'; assert binary.is_file()
 r['baseline_binary_sha256']=sha(binary); save()
 failing={'publisher_observation_matches_after_reopen','publisher_history_survives_expired_events_and_legacy_load','malformed_publisher_history_keeps_valid_new_publishers'}
 cases=['modelnet_feed_tests','modelnet_feed_restart_tests/complete_pages_continue_after_reopen','modelnet_feed_restart_tests/publisher_observation_matches_after_reopen','modelnet_feed_restart_tests/publisher_history_survives_expired_events_and_legacy_load','modelnet_feed_restart_tests/unlock_only_history_preserves_first_publisher_observation','modelnet_feed_restart_tests/malformed_publisher_history_keeps_valid_new_publishers','modelnet_feed_restart_tests/legacy_unlock_history_preserves_first_publisher_observation']
 for case in cases:
  run([binary,'--run_test='+case,'--log_level=test_suite'],'baseline-'+case.replace('/','-'),60,expected=201 if case.rsplit('/',1)[-1] in failing else 0)
 # Verify the new legacy control catches the intermediate restoration mistake.
 shutil.copy2(w/'prior-candidate-feed.cpp',source/'src/modelnet/feed.cpp')
 os.utime(source/'src/modelnet/feed.cpp',None)
 run(['ninja','-C',build,'-f',observed,'-j'+str(workers),'test_btx'],'prior-candidate-build',300)
 run([binary,'--run_test=modelnet_feed_restart_tests/legacy_unlock_history_preserves_first_publisher_observation','--log_level=test_suite'],'prior-candidate-legacy-control',60,expected=201)
 # Restore the baseline bytes before the final source identity assertion.
 shutil.copy2(w/'baseline-feed.cpp',source/'src/modelnet/feed.cpp')
 # The maintained cases are identical; change only the current feed implementation.
 assert sha(source/'src/modelnet/feed.cpp')==sha(w/'baseline-feed.cpp')
 shutil.copy2(w/'candidate-feed.cpp',source/'src/modelnet/feed.cpp')
 os.utime(source/'src/modelnet/feed.cpp',None)
 candidate_dry=run(['ninja','-C',build,'-f',observed,'-n','test_btx'],'candidate-plan',120)
 assert 'Re-running CMake' not in candidate_dry
 run(['ninja','-C',build,'-f',observed,'-j'+str(workers),'test_btx'],'candidate-build',300)
 r['candidate_binary_sha256']=sha(binary); save()
 for case in cases:
  run([binary,'--run_test='+case,'--log_level=test_suite'],'candidate-'+case.replace('/','-'),60)
 run(['ctest','--test-dir',build,'-R','^modelnet_feed(_restart)?_tests$','--output-on-failure'],'candidate-ctest',120)
 r['complete']=True
except Exception as e:r['error']=repr(e);print('PILOT ERROR',repr(e),flush=True)
finally:
 if restored:
  try:r['retained_checkpoint_sha256']=create(w,w/'resume-checkpoint',{'source':HEAD,'purpose':'Integrated FeedStore test_btx qualification','complete':r['complete']})['archive_sha256']
  except Exception as e:r['retention_error']=repr(e)
 save()
raise SystemExit(0 if r['complete'] and not r.get('error') else 1)
