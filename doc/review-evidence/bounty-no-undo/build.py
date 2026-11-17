from pathlib import Path
import json,os,subprocess,tarfile,shutil,time,traceback,hashlib
from checkpoint import sha,restore_timestamps,verify_restored
w=Path(os.environ['GITHUB_WORKSPACE']);r=w/'bountyqual';out=w/'records';out.mkdir(exist_ok=True);src=w/'product';fresh=w/'accepted-source';b=w/'gui-pilot-runtime/qtbuild';state={'status':'INCOMPLETE','commands':[]}
def save():(out/'build-result.json').write_text(json.dumps(state,indent=2)+'\n')
def run(cmd,label,timeout=180,expected=0):
 start=time.monotonic()
 with (out/(label+'.log')).open('w') as f:p=subprocess.run(list(map(str,cmd)),stdout=f,stderr=subprocess.STDOUT,timeout=timeout)
 text=(out/(label+'.log')).read_text(errors='replace');state['commands'].append({'label':label,'command':list(map(str,cmd)),'exit':p.returncode,'seconds':time.monotonic()-start});save();print(label,p.returncode,text[-1500:],flush=True);assert p.returncode==expected,(label,p.returncode);return text
try:
 assert subprocess.check_output(['git','-c','safe.directory='+str(fresh),'rev-parse','HEAD'],cwd=fresh,text=True).strip()=='bd847e2b986722c1723b4cd60988d4f4908452d4'
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
 assert sha(r/'candidate-bounty.cpp')=='23ab54cd8c29efcdd8c8801ea014e792feb056af428d320644a90bc7424845d7'
 assert sha(r/'test.py')=='2414c332308005d067bde52708bf32eedd28986783f1f307c50f51773e6fa080'
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
 for phase in ['baseline','candidate']:
  if phase=='candidate':shutil.copyfile(r/'candidate-bounty.cpp',src/'src/modelnet/bounty.cpp')
  run(['cmake','-P',b/'CMakeFiles/VerifyGlobs.cmake'],phase+'-globs',60)
  graph=out/(phase+'.ninja');shutil.copyfile(b/'build.ninja',graph)
  plan=run(['ninja','-C',b,'-f',graph,'-n','btx-modeld'],phase+'-plan',90);actions=[x for x in plan.splitlines() if x.startswith('[')];state[phase+'_planned_actions']=len(actions);save();assert len(actions)<=250 and 'Re-running CMake' not in plan,'Build exceeds bounded incremental scope'
  run(['ninja','-C',b,'-f',graph,'-j2','btx-modeld'],phase+'-build',900)
  dest=w/'built'/phase;dest.mkdir(parents=True);shutil.copy2(b/'bin/btx-modeld',dest/'btx-modeld');state[phase+'_binary_sha256']=sha(dest/'btx-modeld');state[phase+'_bounty_sha256']=sha(src/'src/modelnet/bounty.cpp');save()
  run(['/opt/hostedtoolcache/Python/3.12.16/x64/bin/python3',r/'test.py',dest/'btx-modeld','/tmp/bounty-'+phase,out/phase],phase+'-test',150,7 if phase=='baseline' else 0)
  result=json.load(open(out/phase/'result.json'));assert result['status']==('EXPECTED_CONTRACT_FAILURE' if phase=='baseline' else 'PASS')
  if phase=='baseline':assert len(result['checks'])==4 and all(not x['pass'] for x in result['checks'])
  else:assert len(result['checks'])==4 and all(x['pass'] for x in result['checks'])
 state['status']='NORMAL_HELPER_MATCHED_PASS';save()
except Exception as e:state['error']=repr(e);state['traceback']=traceback.format_exc();save();print(state['traceback'],flush=True)
raise SystemExit(0 if state['status']=='NORMAL_HELPER_MATCHED_PASS' else 1)
