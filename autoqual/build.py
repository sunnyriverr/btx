from pathlib import Path
import json,os,subprocess,tarfile,shutil,time,traceback,hashlib
from checkpoint import sha,restore_timestamps,verify_restored
w=Path(os.environ['GITHUB_WORKSPACE']);r=w/'autoqual';out=w/'records';out.mkdir(exist_ok=True);src=w/'product';fresh=w/'accepted-source';b=w/'gui-pilot-runtime/qtbuild';mode=__import__('sys').argv[1];state=json.load(open(out/'build-result.json')) if (out/'build-result.json').exists() else {'status':'INCOMPLETE','commands':[]}
def save():(out/'build-result.json').write_text(json.dumps(state,indent=2)+'\n')
def run(cmd,label,timeout=180,expected=0):
 start=time.monotonic()
 with (out/(label+'.log')).open('w') as f:p=subprocess.run(list(map(str,cmd)),stdout=f,stderr=subprocess.STDOUT,timeout=timeout)
 text=(out/(label+'.log')).read_text(errors='replace');state['commands'].append({'label':label,'command':list(map(str,cmd)),'exit':p.returncode,'seconds':time.monotonic()-start});save();print(label,p.returncode,text[-1500:],flush=True);assert p.returncode==expected,(label,p.returncode);return text
try:
 if mode=='prepare':
  assert subprocess.check_output(['git','-c','safe.directory='+str(fresh),'rev-parse','HEAD'],cwd=fresh,text=True).strip()=='ea64a31e9b4f83375746ce2e65917bcb3c2026e9'
  arc=w/'saved-checkpoint/build-state.tar.gz';m=json.load(open(w/'saved-checkpoint/manifest.json'));assert m['workspace']==str(w);assert sha(arc)==m['archive_sha256']=='7099e445368c278fefde438ed282238a55fdfffb2c3566a2354a1ca43aa121ba'
  with tarfile.open(arc) as t:t.extractall(w,filter='data')
  restore_timestamps(w,m);verify_restored(w,m);state['checkpoint_verified']=True;save()
  ext=json.load(open(w/'saved-checkpoint/external-inputs.json'));diff=[];checked=0
  for name,row in ext['rows'].items():
   p=Path(name)
   if '__pycache__' in name or name.endswith('.pyc'):continue
   checked+=1
   if 'link' in row:
    if not p.is_symlink() or os.readlink(p)!=row['link']:diff.append(name)
   elif not p.is_file() or sha(p)!=row['sha256']:diff.append(name)
  state['external_checked']=checked;state['external_differences']=diff;save();assert not diff,'External checkpoint inputs changed; do not reuse objects'
  tracked=subprocess.check_output(['git','ls-files'],cwd=fresh,text=True).splitlines();changed=[]
  old_tracked=subprocess.check_output(['git','-c','safe.directory='+str(w/'checkpoint-source'),'ls-files'],cwd=w/'checkpoint-source',text=True).splitlines()
  removed=sorted(set(old_tracked)-set(tracked));state['old_tracked_removed']=removed;save();assert not removed,'Checkpoint has retired tracked sources; reassess before reuse'
  identities=json.load(open(r/'input-identities.json'))
  for name,h in identities.items():assert sha(r/name)==h,name
  for name in tracked:
   a=fresh/name;p=src/name
   equal=(a.is_symlink() and p.is_symlink() and os.readlink(a)==os.readlink(p)) or (a.is_file() and p.is_file() and not a.is_symlink() and not p.is_symlink() and sha(a)==sha(p))
   if not equal:
    p.parent.mkdir(parents=True,exist_ok=True)
    if p.is_symlink():p.unlink()
    if a.is_symlink():p.symlink_to(os.readlink(a))
    else:shutil.copy2(a,p)
    changed.append(name)
  if (src/'.git').exists():shutil.rmtree(src/'.git')
  shutil.copytree(fresh/'.git',src/'.git');state['tracked_updates']=changed
  for name in tracked:
   a=fresh/name;p=src/name
   assert (a.is_symlink() and p.is_symlink() and os.readlink(a)==os.readlink(p)) or (not a.is_symlink() and p.is_file() and not p.is_symlink() and sha(a)==sha(p)),name
  state['tracked_bytes_verified']=True
  run(['cmake','-S',src,'-B',b,'-DBUILD_TESTS=OFF'],'configure');assert 'WITH_MODELNET:BOOL=ON' in (b/'CMakeCache.txt').read_text()
  import shutil as _shutil
  state['free_bytes_after_restore']=_shutil.disk_usage(w).free;save();assert state['free_bytes_after_restore']>3*1024**3
  run(['cmake','-P',b/'CMakeFiles/VerifyGlobs.cmake'],'globs',60)
  graph=out/'current.ninja';shutil.copyfile(b/'build.ninja',graph)
  plan=run(['ninja','-C',b,'-f',graph,'-n','btx-modeld'],'plan',90)
  actions=[x for x in plan.splitlines() if x.startswith('[')];state['planned_actions']=len(actions);save()
  assert len(actions)<=250 and 'Re-running CMake' not in plan,'Build exceeds guarded scope'
  state['source_head']='ea64a31e9b4f83375746ce2e65917bcb3c2026e9'
  state['test_sha256']=sha(r/'test.py')
  state['helper_source_sha256']=sha(src/'src/modelnet/helper.cpp')
  state['search_source_sha256']=sha(src/'src/modelnet/search.cpp')
  state['status']='PLAN_ACCEPTED';save()
 elif mode=='compile':
  assert state['status']=='PLAN_ACCEPTED'
  run(['ninja','-C',b,'-f',out/'current.ninja','-j2','btx-modeld'],'compile',900)
  dest=w/'built';dest.mkdir(exist_ok=True);shutil.copy2(b/'bin/btx-modeld',dest/'btx-modeld')
  state['binary_sha256']=sha(dest/'btx-modeld');state['status']='NORMAL_HELPER_BUILT';save()
 elif mode=='test':
  assert state['status']=='NORMAL_HELPER_BUILT'
  portable=Path('/tmp/auto-search-input');portable.mkdir(mode=0o755)
  shutil.copytree(w/'gui-pilot-runtime/openssl',portable/'openssl',symlinks=True)
  shutil.copy2(w/'built/btx-modeld',portable/'btx-modeld');(portable/'btx-modeld').chmod(0o755)
  shutil.copy2(r/'test.py',portable/'test.py');assert sha(portable/'test.py')==state['test_sha256']
  result_root=Path('/tmp/auto-search-results');result_root.mkdir(mode=0o755);os.chown(result_root,65534,65534)
  env=['env','PYTHONDONTWRITEBYTECODE=1','LD_LIBRARY_PATH='+str(portable/'openssl/lib64')+':'+str(portable/'openssl/lib')+':/opt/hostedtoolcache/Python/3.12.16/x64/lib','BTX_OPENSSL='+str(portable/'openssl/bin/openssl')]
  try:run(['runuser','-u','nobody','--',*env,'/opt/hostedtoolcache/Python/3.12.16/x64/bin/python3',portable/'test.py',portable/'btx-modeld','/tmp/auto-search-runtime',result_root/'native'],'test',180)
  finally:
   if (result_root/'native').exists():shutil.copytree(result_root/'native',out/'native',dirs_exist_ok=True)
  result=json.load(open(out/'native/result.json'))
  assert result['status']=='PASS' and result['binary_sha256']==state['binary_sha256'] and result['script_sha256']==state['test_sha256']
  assert result['uid']==result['gid']==65534 and result['live_owned_helpers']==0
  state['status']='AUTOMATIC_PROPAGATION_QUALIFIED';save()
 else:raise ValueError(mode)
except Exception as e:state['error']=repr(e);state['traceback']=traceback.format_exc();save();print(state['traceback'],flush=True)
raise SystemExit(0 if state['status'] in ['PLAN_ACCEPTED','NORMAL_HELPER_BUILT','AUTOMATIC_PROPAGATION_QUALIFIED'] and 'error' not in state else 1)
