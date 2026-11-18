"""Bounded exact-current-tree qualification using the retained Linux cache."""
import hashlib,json,os,selectors,shutil,signal,subprocess,sys,time
from pathlib import Path
w=Path(os.environ['GITHUB_WORKSPACE']);out=w/'records';source=w/'product';build=w/'gui-pilot-runtime/qtbuild';p=w/'proposal';ref=w/'current-reference';pin='ea79c62407d04b6b37e55d8121c463cb13aadb7c'
r={'source':pin,'complete':False,'commands':[]};deadline=time.monotonic()+42*60

def sha(x):
 h=hashlib.sha256()
 with x.open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
def save():(out/'qualification.json').write_text(json.dumps(r,indent=2)+'\n')
def run(cmd,label,limit,cwd=None,allowed=None):
 assert time.monotonic()<deadline
 start=time.monotonic();parts=[];log=(out/(label+'.log')).open('wb');proc=subprocess.Popen([str(x)for x in cmd],cwd=cwd or w,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,start_new_session=True)
 sel=selectors.DefaultSelector();sel.register(proc.stdout,selectors.EVENT_READ);timed_out=False
 try:
  while sel.get_map():
   for key,_ in sel.select(1):
    b=os.read(key.fileobj.fileno(),65536)
    if not b:sel.unregister(key.fileobj);continue
    parts.append(b);log.write(b);log.flush();sys.stdout.buffer.write(b);sys.stdout.buffer.flush()
   if proc.poll() is None and (time.monotonic()-start>limit or time.monotonic()>deadline or shutil.disk_usage(w).free<3*1024**3):
    timed_out=True;os.killpg(proc.pid,signal.SIGTERM)
    try:proc.wait(10)
    except subprocess.TimeoutExpired:os.killpg(proc.pid,signal.SIGKILL);proc.wait()
  proc.wait()
 finally:sel.close();log.close()
 r['commands'].append({'label':label,'exit':proc.returncode,'seconds':time.monotonic()-start,'timed_out_or_disk_gate':timed_out});save()
 assert not timed_out,label+' exceeded bound or disk gate'
 if allowed is not None:assert proc.returncode in allowed,(label,proc.returncode)
 return proc.returncode,b''.join(parts).decode(errors='replace')
try:
 assert json.loads((out/'staging.json').read_text())['complete']
 assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=ref,text=True).strip()==pin
 # Restore exact prerequisite853 source; retained857 code is not our baseline.
 tracked=[n for n in subprocess.check_output(['git','ls-files','-z'],cwd=ref,text=True).split('\0')if n]
 changed=[]
 for name in tracked:
  a=ref/name;b=source/name
  same=(b.is_symlink() and os.readlink(b)==os.readlink(a)) if a.is_symlink() else (b.is_file() and not b.is_symlink() and sha(a)==sha(b) and (a.stat().st_mode&0o111)==(b.stat().st_mode&0o111))
  if same:continue
  b.parent.mkdir(parents=True,exist_ok=True)
  if b.is_symlink() or b.is_file():b.unlink()
  if a.is_symlink():b.symlink_to(os.readlink(a))
  else:shutil.copy2(a,b);os.utime(b,None)
  changed.append(name)
 r['overlay_changed']=changed
 for name in tracked:
  a=ref/name;b=source/name
  assert (b.is_symlink() and os.readlink(a)==os.readlink(b)) if a.is_symlink() else sha(a)==sha(b),name
 r['all_tracked_prerequisite_source_verified']=True
 for name in ('helper.cpp','modelnet_economy_tests.cpp'):
  path='src/modelnet/'+name if name=='helper.cpp' else 'src/test/'+name
  assert sha(source/path)==sha(p/('baseline-'+name)),path
 # Identical maintained test code in both phases.
 shutil.copy2(p/'candidate-modelnet_economy_tests.cpp',source/'src/test/modelnet_economy_tests.cpp');os.utime(source/'src/test/modelnet_economy_tests.cpp',None)
 cmake=source/'src/test/CMakeLists.txt';cmake.write_text(cmake.read_text()+(p/'target.cmake').read_text())
 os.environ['BTX_OPENSSL']=str(w/'gui-pilot-runtime/openssl/bin/openssl')
 run([os.environ['BTX_OPENSSL'],'version'],'openssl',30,allowed=(0,));run(['g++','-dumpfullversion'],'gcc',30,allowed=(0,))
 run(['/usr/local/bin/cmake','-S',source,'-B',build],'configure-focused-target',150,allowed=(0,))
 test=build/'bin/s2_visibility_tests';helper=build/'bin/btx-modeld';case='release_lists_respect_local_hide_without_changing_campaigns'
 def phase(name):
  _,dry=run(['ninja','-n','btx-modeld','s2_visibility_tests'],name+'-dry',90,build,(0,))
  actions=[x for x in dry.splitlines()if x.startswith('[')];r[name+'_planned_actions']=len(actions);save();assert 0<len(actions)<=160,'build exceeds160action gate'
  run(['ninja','-j2','btx-modeld','s2_visibility_tests'],name+'-build',1100,build,(0,))
  dest=w/'retained-binaries'/name;dest.mkdir(parents=True,exist_ok=True)
  for x in (helper,test):shutil.copy2(x,dest/x.name)
  r[name+'_binaries']={x.name:sha(x)for x in (helper,test)};r[name+'_helper_source']=sha(source/'src/modelnet/helper.cpp');r[name+'_test_source']=sha(source/'src/test/modelnet_economy_tests.cpp');save()
  code,text=run([test,'--run_test=modelnet_economy_tests/'+case,'--log_level=test_suite','--report_level=detailed'],name+'-maintained',120,allowed=(201,)if name=='baseline' else (0,))
  assert 'Entering test case "'+case+'"' in text and 'Leaving test case "'+case+'"'in text
  if name=='baseline':
   from unit_result import baseline_failures
   errors=baseline_failures(text,code)
   r['baseline_expected_assertions']=errors
  r[name+'_maintained_exit']=code;save()
  run([sys.executable,p/'observe.py','--helper',helper,'--sha256',sha(helper),'--out',out/(name+'-native')],name+'-native',540,allowed=(0,))
  native=json.loads((out/(name+'-native/result.json')).read_text())
  assert native['verdict']==('REPRODUCED_LISTING_INCONSISTENCY' if name=='baseline' else 'NOT_REPRODUCED')
  if name=='baseline':
   expected=[{'phase':ph,'view':v,'model':label} for ph in ('hidden','hidden_restart') for v,label in [('recent_local','open_target'),('recent_local','released_target'),('fundable','open_target'),('unlocked','released_target')]]
   assert native['violations']==expected,'baseline missed a measured leak'
  r[name+'_native']=native;save()
 phase('baseline')
 shutil.copy2(p/'candidate-helper.cpp',source/'src/modelnet/helper.cpp');os.utime(source/'src/modelnet/helper.cpp',None)
 phase('candidate')
 assert r['baseline_test_source']==r['candidate_test_source'],'tests differ'
 code,text=run([test,'--run_test=modelnet_economy_tests','--log_level=test_suite','--report_level=detailed'],'candidate-economy-suite',240,allowed=(0,))
 assert 'Entering test case "'+case+'"'in text and 'Entering test case "feed_leaves_out_hidden_models_and_muted_publishers"'in text
 assert 'Leaving test case "'+case+'"'in text and 'No errors detected'in text
 r['candidate_economy_cases_entered']=text.count('Entering test case "');r['candidate_economy_exit']=code;r['complete']=True;save()
except Exception as e:r['error']=repr(e);save();raise
finally:
 r['retained_binaries']={str(x.relative_to(w/'retained-binaries')):sha(x)for x in (w/'retained-binaries').rglob('*')if x.is_file()}if(w/'retained-binaries').exists()else{}
 if r.get('candidate_binaries'):
  try:
   from checkpoint import create
   m=create(w,w/'visibility-checkpoint',{'source':pin,'pr853_prerequisite':True,'visibility_candidate':True,'qualification_complete':r['complete'],'test_scope':'focused full economy TU with normal main/libs, not aggregate test_btx'},reserve=int(1.25*1024**3))
   r['updated_checkpoint']={'archive_sha256':m['archive_sha256'],'identity':m['identity']}
  except Exception as e:r['updated_checkpoint_error']=repr(e)
 save()
