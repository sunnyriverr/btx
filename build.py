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



 composition=json.loads((w/'composition-receipt.json').read_text());assert composition['base']==HEAD
 for name,expected_hash in composition['files'].items():assert sha(w/'composition'/name)==expected_hash
 # Identical candidate test source is compiled against base product bodies first.
 for name in composition['files']:
  if name.startswith('src/test/'):
   shutil.copy2(w/'composition'/name,source/name);os.utime(source/name,None)
 for name in ('src/modelnet/feed.cpp','src/modelnet/feed.h','src/test/modelnet_feed_tests.cpp'):
  assert sha(source/name)==sha(accepted/name),name
 r['base_feed_restored']=True;r['composition_verified']=True;r['composition']=composition
 run(['cmake','-S',source,'-B',build,'-DBUILD_TESTS=ON'],'settings-configure',180)
 run(['cmake','-P',build/'CMakeFiles/VerifyGlobs.cmake'],'settings-globs',120,cwd=build)
 observed=build/'settings-observed.ninja';shutil.copy2(build/'build.ninja',observed)
 dry=run(['ninja','-C',build,'-f',observed,'-n','test_btx','btx-modeld'],'baseline-plan',120)
 assert 'Re-running CMake'not in dry
 steps=[x for x in dry.splitlines()if x.startswith('[')];assert 0<len(steps)<=35
 r['planned_steps']=len(steps);r['workers']=2;save()
 r['resources']=run(['bash','-c','nproc; free -b; df -B1 .'],'build-resources',30)
 run(['ninja','-C',build,'-f',observed,'-j2','test_btx','btx-modeld'],'baseline-build',1500)
 retained=w/'qualified-binaries';(retained/'baseline').mkdir(parents=True)
 for name in ('test_btx','btx-modeld'):shutil.copy2(build/'bin'/name,retained/'baseline'/name)
 r['baseline_binaries']={n:sha(retained/'baseline'/n)for n in ('test_btx','btx-modeld')};save()
 cases=[
 ('modelnet_watch_tests/failed_watch_creation_preserves_live_state_actions_and_retry',201),
 ('modelnet_watch_tests/failed_watch_replacement_preserves_live_state_actions_and_retry',201),
 ('modelnet_watch_tests/rejected_channel_creation_allows_identical_retry',201),
 ('modelnet_watch_tests/rejected_channel_replacement_allows_identical_retry',201),
 ('modelnet_first_run_tests/rejected_policy_save_keeps_live_settings_and_allows_retry',201),
 ('modelnet_first_run_tests/saved_policy_quota_matches_catalog_normalization',0)]
 r['cases']=cases;save()
 for case,expected in cases:
  run([retained/'baseline/test_btx','--run_test='+case,'--log_level=test_suite','--report_level=detailed'],'baseline-'+case.replace('/','-'),90,expected=expected)
 for name,expected_hash in composition['files'].items():
  if not name.startswith('src/test/'):
   shutil.copy2(w/'composition'/name,source/name);os.utime(source/name,None)
  assert sha(source/name)==expected_hash
 candidate_dry=run(['ninja','-C',build,'-f',observed,'-n','test_btx','btx-modeld'],'candidate-plan',120)
 assert 'Re-running CMake'not in candidate_dry
 run(['ninja','-C',build,'-f',observed,'-j2','test_btx','btx-modeld'],'candidate-build',900)
 (retained/'candidate').mkdir(exist_ok=True)
 for name in ('test_btx','btx-modeld'):shutil.copy2(build/'bin'/name,retained/'candidate'/name)
 r['candidate_binaries']={n:sha(retained/'candidate'/n)for n in ('test_btx','btx-modeld')};save()
 for case,_ in cases:
  run([retained/'candidate/test_btx','--run_test='+case,'--log_level=test_suite','--report_level=detailed'],'candidate-'+case.replace('/','-'),90)
 run(['ninja','-C',build,'-f',observed,'-t','commands','btx-modeld'],'modeld-build-commands',60)
 run(['ninja','-C',build,'-f',observed,'-t','commands','test_btx'],'test-build-commands',60)
 r['paired_cases_complete']=True;r['complete']=True;save()
except Exception as e:
 r['error']=repr(e);print('BUILD ERROR',repr(e),flush=True)
finally:
 # Keep usable binaries separate from checkpoint/log retention, even on later failure.
 retained=w/'qualified-binaries'
 if retained.exists():
  try:
   bundle=w/'binary-retention';bundle.mkdir(exist_ok=True)
   with tarfile.open(bundle/'settings-binaries.tar.gz','w:gz',compresslevel=1)as t:t.add(retained,arcname='qualified-binaries')
   r['binary_archive_sha256']=sha(bundle/'settings-binaries.tar.gz')
  except Exception as e:r['binary_retention_error']=repr(e)
 if restored:
  try:r['retained_checkpoint_sha256']=create(w,w/'resume-checkpoint',{'source':HEAD,'purpose':'778-780 integrated settings paired qualification','complete':r['complete'],'composition':r.get('composition'),'scope':'No776cap or migration work'})['archive_sha256']
  except Exception as e:r['retention_error']=repr(e)
 save()
raise SystemExit(0 if r['complete'] and not r.get('error') and not r.get('retention_error') and not r.get('binary_retention_error') else 1)
