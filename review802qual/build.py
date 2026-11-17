from pathlib import Path
import json,os,shutil,signal,subprocess,tarfile,time,traceback
from checkpoint import sha,restore_timestamps,verify_restored,create
w=Path(os.environ['GITHUB_WORKSPACE']);recipe=w/'review802qual';out=w/'records';out.mkdir(exist_ok=True);source=w/'product';accepted=w/'accepted-source';base=w/'baseline-source';build=w/'gui-pilot-runtime/qtbuild';i=json.loads((recipe/'inputs.json').read_text())
r={'status':'INCOMPLETE','scope':'production-linked component, not Boost runner/daemon restart/concurrency/chain','candidate':i['candidate'],'baseline':i['baseline'],'commands':[],'old_object_reuse':False};groups=[];phase='unprepared'
def save():(out/'result.json').write_text(json.dumps(r,indent=2)+'\n')
def quiet(g):return not [l for l in subprocess.check_output(['ps','-eo','pgid=,stat='],text=True).splitlines() if l.split()[0]==str(g)]
def run(cmd,label,cap,expected=0):
 start=time.monotonic();timedout=False
 with (out/(label+'.log')).open('w') as f:
  p=subprocess.Popen(list(map(str,cmd)),stdout=f,stderr=subprocess.STDOUT,start_new_session=True);groups.append(p.pid)
  try:p.wait(cap)
  except subprocess.TimeoutExpired:
   timedout=True
   try:os.killpg(p.pid,signal.SIGTERM)
   except ProcessLookupError:pass
   try:p.wait(10)
   except subprocess.TimeoutExpired:
    try:os.killpg(p.pid,signal.SIGKILL)
    except ProcessLookupError:pass
    p.wait(10)
 if timedout and not quiet(p.pid):
  try:os.killpg(p.pid,signal.SIGKILL)
  except ProcessLookupError:pass
 for _ in range(50):
  if quiet(p.pid):break
  time.sleep(.2)
 assert quiet(p.pid),'Owned process group remains live'
 text=(out/(label+'.log')).read_text(errors='replace');r['commands'].append({'label':label,'command':list(map(str,cmd)),'exit':p.returncode,'seconds':round(time.monotonic()-start,3),'timeout':timedout,'group':p.pid,'quiescent':True});save();print(label,p.returncode,text[-3000:],flush=True)
 if timedout:raise TimeoutError(label)
 assert p.returncode==expected,(label,p.returncode)
 return text

def plan(label,limit):
 run(['cmake','-P',build/'CMakeFiles/VerifyGlobs.cmake'],label+'-globs',60);graph=out/(label+'.ninja');shutil.copyfile(build/'build.ninja',graph)
 text=run(['ninja','-C',build,'-f',graph,'-n','btx-modeld','review802'],label+'-plan',90);actions=[l for l in text.splitlines() if l.startswith('[')];r[label+'_actions']=len(actions);save();assert len(actions)<=limit and 'Re-running CMake' not in text
 return graph

def external_inputs():
 roots=[Path('/usr/include'),Path('/usr/lib/gcc'),Path('/usr/lib/x86_64-linux-gnu'),Path('/opt/hostedtoolcache/Python/3.12.16/x64')];paths=set()
 for root in roots:
  if root.exists():paths.update(p for p in root.rglob('*') if p.is_file() or p.is_symlink())
 for name in ['gcc','g++','ld','ar','ranlib','as','cmake','ninja']:
  if shutil.which(name):paths.update([Path(shutil.which(name)),Path(shutil.which(name)).resolve()])
 rows={str(p):({'link':os.readlink(p)} if p.is_symlink() else {'sha256':sha(p),'bytes':p.stat().st_size}) for p in sorted(paths)}
 f=out/'external-inputs.json';f.write_text(json.dumps({'roots':list(map(str,roots)),'rows':rows,'limits':'Future reuse must compare actual dependency/link inputs with these recorded roots; this is not universal portability.'},indent=2)+'\n');r['external_manifest_sha256']=sha(f);save()
 run(['bash','-c','g++ --version; cmake --version; ninja --version; dpkg-query -W'],'toolchain',60)

def checkpoint(name):
 assert all(quiet(g) for g in groups)
 m=create(w,w/name,{'candidate':i['candidate'],'baseline':i['baseline'],'phase':phase,'status':r['status'],'fixture_sha256':i['fixture_sha256'],'external_manifest_sha256':r['external_manifest_sha256']});shutil.copyfile(out/'external-inputs.json',w/name/'external-inputs.json');shutil.copyfile(recipe/'inputs.json',w/name/'inputs.json');r[name]={'sha256':m['archive_sha256'],'phase':phase};save()

def use_phase(name):
 global phase
 for path,v in i['files'][name].items():
  assert sha(recipe/name/path)==v['sha256'];shutil.copyfile(recipe/name/path,source/path);assert sha(source/path)==v['sha256']
 phase=name;r['phase']=name;r[name+'_source_inputs']=i['files'][name];save()
try:
 assert sha(recipe/'component.cpp')==i['fixture_sha256']
 for directory,key in [(accepted,'candidate'),(base,'baseline')]:assert subprocess.check_output(['git','-c','safe.directory='+str(directory),'rev-parse','HEAD'],cwd=directory,text=True).strip()==i[key]
 for name,directory in [('baseline',base),('candidate',accepted)]:
  for path,v in i['files'][name].items():assert sha(directory/path)==v['sha256']
 m=json.loads((w/'saved-checkpoint/manifest.json').read_text());arc=w/'saved-checkpoint/build-state.tar.gz'
 assert m['workspace']==str(w) and m['archive_sha256']==sha(arc)=='ca4eb79d4f8dba2199770f57246c5c25a80b33b156ad1f957b8926ae5bf770b1' and shutil.disk_usage(w).free>10*1024**3
 with tarfile.open(arc) as t:t.extractall(w,filter='data')
 restore_timestamps(w,m);verify_restored(w,m);r['old_checkpoint_verified']=True
 invalid=[]
 for p in list(build.rglob('*')):
  if p.is_file() and (p.suffix in ('.o','.a','.so') or p.parent==build/'bin'):invalid.append(str(p.relative_to(w)));p.unlink()
 r['invalidated_outputs']=invalid
 # Exact archived base -> candidate comparison has no removed/renamed tracked files.
 assert json.loads((recipe/'source-comparison-summary.json').read_text())['removed_or_renamed']==[]
 tracked=subprocess.check_output(['git','ls-files'],cwd=accepted,text=True).splitlines()
 for name in tracked:
  a=accepted/name;b=source/name;same=(a.is_symlink() and b.is_symlink() and os.readlink(a)==os.readlink(b)) or (not a.is_symlink() and b.is_file() and not b.is_symlink() and sha(a)==sha(b))
  if not same:
   b.parent.mkdir(parents=True,exist_ok=True)
   if b.is_symlink():b.unlink()
   if a.is_symlink():b.symlink_to(os.readlink(a))
   else:shutil.copy2(a,b)
 for name in tracked:
  a=accepted/name;b=source/name;assert (a.is_symlink() and b.is_symlink() and os.readlink(a)==os.readlink(b)) or (a.is_file() and b.is_file() and sha(a)==sha(b)),name
 if (source/'.git').exists():shutil.rmtree(source/'.git')
 shutil.copytree(accepted/'.git',source/'.git');r['candidate_tracked_bytes_verified']=True;save()
 cm=source/'src/CMakeLists.txt';cm.write_text(cm.read_text()+f'\nadd_executable(review802 "{recipe}/component.cpp")\ntarget_link_libraries(review802 core_interface Boost::headers libevent::extra OpenSSL::SSL OpenSSL::Crypto)\ntarget_link_btx_linux_archive_group(review802 test_util bitcoin_cli bitcoin_modelnet ${{BTX_NODE_WALLET_ARCHIVES}})\n')
 run(['cmake','-S',source,'-B',build,'-DBUILD_TESTS=OFF'],'configure',180);cache=(build/'CMakeCache.txt').read_text();(out/'CMakeCache.txt').write_text(cache);assert 'WITH_MODELNET:BOOL=ON' in cache and 'ENABLE_WALLET:BOOL=ON' in cache
 external_inputs();use_phase('candidate');graph=plan('candidate',3800)
 run(['ninja','-C',build,'-f',graph,'-j2','btx-modeld','review802'],'candidate-build',1800)
 r['status']='CANDIDATE_BUILT_NOT_TESTED';save();dest=w/'built/candidate';dest.mkdir(parents=True)
 for name in ['btx-modeld','review802']:shutil.copy2(build/'bin'/name,dest/name)
 r['candidate_binaries']={name:sha(dest/name) for name in ['btx-modeld','review802']};save();checkpoint('candidate-checkpoint')
 text=run([dest/'review802'],'candidate-component',90);assert text.count('PASS stored_ciphertext_own_secret_exact_bytes_and_catalog_reload')==1;r['candidate_component']='PASS';save()
 use_phase('baseline');graph=plan('baseline',40)
 run(['ninja','-C',build,'-f',graph,'-j2','btx-modeld','review802'],'baseline-build',480)
 dest=w/'built/baseline';dest.mkdir(parents=True)
 for name in ['btx-modeld','review802']:shutil.copy2(build/'bin'/name,dest/name)
 r['baseline_binaries']={name:sha(dest/name) for name in ['btx-modeld','review802']};assert r['baseline_binaries']['review802']!=r['candidate_binaries']['review802'];save()
 text=run([dest/'review802'],'baseline-component',90,expected=1)
 signature='FAIL campaign["ciphertext_artifact_id"].get_str() != campaign["artifact_id"].get_str()';assert signature in text,'Baseline failure outside intended product condition'
 r['baseline_component']='EXPECTED_PRODUCT_FAILURE';r['same_fixture_sha256']=i['fixture_sha256'];r['status']='MATCHED_STORED_BYTE_COMPONENT_PASS';save()
except TimeoutError as e:r['status']='BUILD_BOUND_REACHED_NO_QUALIFICATION';r['error']=str(e);save()
except Exception as e:r['error']=repr(e);r['traceback']=traceback.format_exc();print(r['traceback'],flush=True);save()
finally:
 try:
  if r.get('external_manifest_sha256'):checkpoint('final-checkpoint')
 except Exception as e:r['final_checkpoint_error']=repr(e);save()
 r['owned_groups_quiescent']=all(quiet(g) for g in groups);save()
raise SystemExit(0 if r['status']=='MATCHED_STORED_BYTE_COMPONENT_PASS' else 1)
