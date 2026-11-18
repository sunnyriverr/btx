from pathlib import Path
import os,sys,json,hashlib,subprocess,time,signal,re,shutil,traceback
from checkpoint import create,sha
from test_offline import result_gate
w=Path(os.environ['GITHUB_WORKSPACE']);src=w/'product';build=w/'gui-pilot-runtime/qtbuild';out=w/'records';r={'complete':False,'build':False,'commands':[]};checkpoint=False
PIN='371013d61dc124a363521df5b94e97f64d2464f2';target='src/wallet/rpc/transactions.cpp';test='test/functional/wallet_modelnet_funding.py'
def save():(out/'qualification.json').write_text(json.dumps(r,indent=2)+'\n')
def run(argv,label,limit=60,allow=(0,),cwd=None):
 started=time.monotonic();p=subprocess.Popen([str(x)for x in argv],cwd=cwd,start_new_session=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
 try:data,_=p.communicate(timeout=limit)
 except subprocess.TimeoutExpired:
  os.killpg(p.pid,signal.SIGTERM)
  try:data,_=p.communicate(timeout=10)
  except subprocess.TimeoutExpired:os.killpg(p.pid,signal.SIGKILL);data,_=p.communicate()
  (out/(label+'.log')).write_bytes(data);raise AssertionError(label+' timed out')
 (out/(label+'.log')).write_bytes(data);r['commands'].append({'label':label,'argv':[str(x)for x in argv],'exit':p.returncode,'seconds':time.monotonic()-started});save();print(label,p.returncode,round(time.monotonic()-started,3),flush=True)
 assert p.returncode in allow,(label,p.returncode,data.decode(errors='replace')[-4000:])
 return data.decode(errors='replace')
try:
 assert sha(build/'bin/btxd')=='00636dbeac1c75f808b06ad254b129270e60ccb9551b908eaf64ec18cc870995'
 assert (src/target).read_bytes()==(w/'proposal/baseline-transactions.cpp').read_bytes()
 before_checker={p:sha(src/p)for p in ['src/rpc/util.cpp','src/rpc/util.h','src/rpc/modelnet.cpp']};r['unchanged_source']=before_checker
 # The source itself is frozen; only tracked wallet response declarations and
 # the maintained test are overlaid. Explicit configure then a real Ninja plan.
 (w/'baseline').mkdir();shutil.copy2(build/'bin/btxd',w/'baseline/btxd');(out/'baseline-node.sha256').write_text(sha(w/'baseline/btxd')+'\n')
 (src/test).write_bytes((w/'proposal/wallet_modelnet_funding.py').read_bytes());r['test_sha256']=sha(src/test)
 baseline=run([sys.executable,w/'proposal/run_test.py','baseline'],'baseline-functional',300,allow=(1,),cwd=w)
 log=(w/'runtime-baseline/test_framework.log').read_text();assert 'returned incorrect type'in log and 'modelnet'in log and 'key returned that was not in doc'in log and 'assert_funding_readers'in log,'baseline failed before intended reader'
 r['baseline_expected_failure']=True;save()
 run(['git','init',src],'source-git-init',30);run(['git','fetch','--depth=1','https://github.com/btxchain/btx.git',PIN],'source-git-fetch',90,cwd=src);run(['git','update-ref','HEAD',PIN],'source-head',20,cwd=src);run(['git','read-tree',PIN],'source-index',20,cwd=src)
 (src/target).write_bytes((w/'proposal/candidate-transactions.cpp').read_bytes());r['candidate_transactions_sha256']=sha(src/target)
 run(['cmake','-S',src,'-B',build,'-DCMAKE_SUPPRESS_REGENERATION=ON'],'configure',180)
 plan=run(['ninja','-n','btxd'],'candidate-plan',60,cwd=build);actions=[l for l in plan.splitlines()if re.match(r'\[\d+/\d+\]',l)];compiles=[l for l in actions if 'Building CXX'in l or 'Building C object'in l];r['planned_actions']=len(actions);r['planned_compiles']=len(compiles);assert len(actions)<=60 and len(compiles)<=8 and any('transactions.cpp' in l for l in compiles),'unexpected or missing rebuild'
 run(['ninja','-j2','btxd'],'candidate-build',600,cwd=build);r['build']=True;checkpoint=True
 assert all(sha(src/p)==h for p,h in before_checker.items());assert sha(src/test)==r['test_sha256'];r['validator_and_funding_source_unchanged']=True
 (w/'binaries').mkdir();shutil.copy2(build/'bin/btxd',w/'binaries/btxd');r['candidate_node_sha256']=sha(w/'binaries/btxd');save()
 run([sys.executable,w/'proposal/run_test.py','candidate'],'candidate-functional',300,cwd=w)
 log=(w/'runtime-candidate/test_framework.log').read_text();assert 'Test passed'in log and 'Test failed'not in log
 assert sha(src/test)==r['test_sha256'];assert result_gate(1,(w/'runtime-baseline/test_framework.log').read_text(),0,log,sha(src/test)==r['test_sha256'],all(sha(src/p)==h for p,h in before_checker.items()));r.update(complete=True,verdict='SAME_MAINTAINED_TEST_BASELINE_FAIL_CANDIDATE_FULL_PASS');save()
except Exception:r['error']=traceback.format_exc();r['verdict']='QUALIFICATION_FAILED_OR_INCOMPLETE';save();raise
finally:
 for phase in ['baseline','candidate']:
  p=w/('runtime-'+phase)/'test_framework.log'
  if p.exists():shutil.copy2(p,out/(phase+'-framework.log'))
 if checkpoint:
  try:
   m=create(w,w/'checkpoint-new',{'source':PIN,'funding_result_candidate':True,'qualification_complete':r['complete']},reserve=2*1024**3);r['checkpoint_sha256']=m['archive_sha256'];save()
  except Exception:r['checkpoint_error']=traceback.format_exc();save()
