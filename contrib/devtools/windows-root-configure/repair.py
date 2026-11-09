"""Bounded native Windows before/after repair qualification; no upstream publication."""
from pathlib import Path
import os,sys,json,subprocess,shutil,re,datetime,hashlib
import restore_support as h
import checkpoint
s=h.s;R=h.R;E=h.E;B=h.B;ROOT=h.ROOT;SOURCE=h.SOURCE;P=Path(__file__).resolve().parent
BASE=h.TARGET;RESULT=E/'repair.json'
def write(v):RESULT.write_text(json.dumps(v,indent=2)+'\n')
def cmd(label,args,limit=120,cwd=SOURCE):return s.need(label,[str(x)for x in args],limit,cwd=cwd)
def check(label,args,expected,contains=None):
 code=s.run(label,[str(x)for x in args],90);text=(E/(label+'.log')).read_text(errors='replace')
 assert code==expected,(label,code,text[-3000:])
 if contains:assert contains in text,(label,text[-3000:])
 return {'exit':code,'log_sha256':checkpoint.digest(E/(label+'.log')),'expected_text':contains}
def run():
 assert R['status']=='RESTORED_VERIFIED' and not h.processes()
 result={'source':BASE,'status':'BASELINE_CONTROLS','baseline_cache':10223164157,'baseline_binaries':h.I['binaries'],'cases':{},'product_compilation_invoked':False,'upstream_post':False};write(result)
 original=json.loads((B/'btx-checkpoint.json').read_text());target=None
 try:
  # Use the maintained component CMake project and test, with only our new
  # regression inserted. The source under test stays the exact accepted base.
  driver=ROOT/'guard-regression-driver';driver.mkdir();component=ROOT/'guard-component-build'
  shutil.copyfile(SOURCE/'test/util/model_security/CMakeLists.txt',driver/'CMakeLists.txt')
  test=(SOURCE/'test/util/model_security/native_ipc_tests.cpp').read_bytes()
  temp=ROOT/'regression-edit';temp.mkdir();(temp/'test/util/model_security').mkdir(parents=True);(temp/'test/util/model_security/native_ipc_tests.cpp').write_bytes(test)
  cmd('prepare-regression-test',['git','apply','--unsafe-paths',str(P/'regression.patch')],60,cwd=temp)
  # Copy all maintained test files: CMake declares their targets even when only
  # the IPC target is selected. No unrelated test bodies will be executed.
  for f in(SOURCE/'test/util/model_security').iterdir():
   if f.is_file() and f.suffix in ['.cpp','.c'] :shutil.copyfile(f,driver/f.name)
  shutil.copyfile(temp/'test/util/model_security/native_ipc_tests.cpp',driver/'native_ipc_tests.cpp')
  result['regression_sha256']=checkpoint.digest(driver/'native_ipc_tests.cpp');result['maintained_cmake_sha256']=checkpoint.digest(driver/'CMakeLists.txt');write(result)
  triplet=ROOT/'vcpkg-installed/x64-windows-static';sqlite=triplet/'lib/sqlite3.lib';assert sqlite.exists() and(triplet/'include/sqlite3.h').exists()
  args=['cmake','-S',str(driver),'-B',str(component),'-G','Ninja','-DCMAKE_C_COMPILER=clang-cl','-DCMAKE_CXX_COMPILER=clang-cl','-DCMAKE_BUILD_TYPE=Release','-DCMAKE_MSVC_RUNTIME_LIBRARY=MultiThreaded','-DBTX_SOURCE_ROOT='+str(SOURCE),'-DBTX_INTEGRATED_SOURCE='+str(SOURCE),'-DSQLite3_INCLUDE_DIR='+str(triplet/'include'),'-DSQLite3_LIBRARY='+str(sqlite)]
  cmd('component-configure',args,180)
  baseline=json.loads((P/'baseline-evidence.json').read_text())
  assert baseline['source']==BASE and baseline['binary_hashes']==h.I['binaries']
  assert baseline['regression_sha256']==result['regression_sha256'] and baseline['maintained_cmake_sha256']==result['maintained_cmake_sha256']
  assert baseline['restore_support_sha256']==checkpoint.digest(P/'restore_support.py')
  assert baseline['cleanup'] and baseline['node_status']=='NODE_LIFECYCLE_PASS_GUARD_BLOCKED' and len(baseline['cases'])==6
  result['baseline_reuse']=baseline;result['cases']=dict(baseline['cases']);result['baseline_node_status']=baseline['node_status'];write(result)
  # Two independent product repairs; existing reader validation is untouched.
  identity=['-c','user.name=Sunny River','-c','user.email=254738454+sunnyriverr@users.noreply.github.com']
  # Use the fork controller's existing verified public noreply identity.
  author=json.loads((P/'contract.json').read_text())['author'];identity=['-c','user.name='+author['name'],'-c','user.email='+author['email']]
  result['commits']=[]
  for patch,message in [('framing.patch','modelnet: accept terminal CRLF in private guard replies'),('private-owner.patch','modelnet: assign Windows private objects to the current user'),('regression.patch','test: cover native guard framing and private-store ownership')]:
   cmd('apply-'+patch,['git','apply','--check',P/patch],60);cmd('patch-'+patch,['git','apply',P/patch],60)
   cmd('stage-'+patch,['git','add','--update'],60);cmd('commit-'+patch,['git',*identity,'commit','-m',message],60)
   result['commits'].append(subprocess.check_output(['git','rev-parse','HEAD'],cwd=SOURCE,text=True).strip())
  target=result['commits'][-1];cmd('preserve-candidate-bundle',['git','bundle','create',E/'guard-repair.bundle',BASE+'..HEAD'],90);result['target']=target;result['source_catalog']=s.catalog(target,'candidate-before');write(result)
  # Plan from the restored real project before compiling. Retain all objects.
  glob=B/'CMakeFiles/VerifyGlobs.cmake'
  if glob.exists():cmd('candidate-verify-globs',['cmake','-P',glob],120,cwd=B)
  cmd('candidate-ninja-plan',['ninja','-C',B,'-n','-d','explain','btxd','btx-cli','btx-tx','btx-util','btx-open','btx-modeld','btx-guardd','btx-security','test_btx'],180,cwd=B)
  plan=(E/'candidate-ninja-plan.log').read_text(errors='replace');actions=re.findall(r'^\[\d+/\d+\].*',plan,re.M);result['planned_actions']=actions;write(result)
  assert len(actions)<=40 and 'stored deps info out of date'not in plan,'Unexpected broad invalidation; stop before build'
  result['product_compilation_invoked']=True;write(result)
  cmd('candidate-unit-build',['cmake','--build',B,'--target','btxd','btx-cli','btx-tx','btx-util','btx-open','btx-modeld','btx-guardd','btx-security','test_btx','--parallel','4','--','-k','1'],1200,cwd=B)
  result['candidate_binaries']={n:checkpoint.digest(B/'bin'/(n+'.exe'))for n in h.I['binaries']};write(result)
  cmd('component-candidate-build',['cmake','--build',component,'--target','security-native-ipc','--parallel','4'],600)
  for i in range(3):
   result['cases']['candidate-ipc-'+str(i)]=check('candidate-ipc-'+str(i),[component/'security-native-ipc.exe',B/'bin/btx-guardd.exe'],0,'"failed":0')
   root=ROOT/('guard-candidate-store-'+str(i));assert not root.exists()
   result['cases']['candidate-owner-'+str(i)]=check('candidate-owner-'+str(i),[B/'bin/btx-security.exe','inspect','--root',root],0)
   status=json.loads((E/('candidate-owner-'+str(i)+'.log')).read_text());assert status['journal_valid']and status['automatic_spend_atoms']=='0'
   shutil.rmtree(root)
  R['status']='RESTORED_VERIFIED';R['boots']=[];R['forced_cleanup']=[];h.run()
  result['candidate_node_status']=R['status'];assert R['status']=='NODE_AND_GUARD_LIFECYCLE_PASS'
  assert len(R['boots'])==2 and all(b['guard_observed']and len(b['health'])==10 for b in R['boots'])
  assert R['boots'][0]['guard_pid']!=R['boots'][1]['guard_pid'];result['new_guard_pid_after_restart']=True
  result['status']='NATIVE_BEFORE_AFTER_AND_NODE_RESTART_PASS';write(result)
 except BaseException as e:result.update(status='QUALIFICATION_BLOCKED',error=repr(e));write(result);raise
 finally:
  s.quiesce();result['process_cleanup_verified']=not h.processes();assert result['process_cleanup_verified']
  if target and result['product_compilation_invoked']:
   catalog=s.catalog(target,'retained-guard-repair');profile=dict(original['profile']);profile.update(source=target,baseline_cache=10223164157,scope='Focused Windows guard repair; native IPC and node-owned lifecycle only; full unit campaign incomplete')
   result['checkpoint']=checkpoint.capture(ROOT,SOURCE,profile,catalog,{'status':result['status'],'binaries':result.get('candidate_binaries'),'full_units':False})
   shutil.copyfile(B/'btx-checkpoint.json',E/'guard-repair-checkpoint.json');result['checkpoint_key']='btx356-guard-repair-v1-'+os.environ['GITHUB_RUN_ID']
   with open(os.environ['GITHUB_OUTPUT'],'a')as f:f.write('checkpoint_valid=true\ncheckpoint_key='+result['checkpoint_key']+'\n')
  else:
   # Component-only preparation must leave every retained project file unchanged.
   for k,v in original['files'].items():assert checkpoint.digest(ROOT/k)==v['sha256'],k
   result['original_cache_unchanged']=True
  result['preserved_original_cache_id']=10223164157;write(result);s.save()

try:
 if sys.argv[1]=='prepare':h.prepare()
 elif sys.argv[1]=='run':run()
 else:raise ValueError(sys.argv[1])
except BaseException as e:R.setdefault('errors',[]).append({'stage':sys.argv[1],'error':repr(e)});raise
finally:s.save()
