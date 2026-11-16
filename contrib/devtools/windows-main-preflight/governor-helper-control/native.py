from pathlib import Path
import os,sys,json,subprocess,time,hashlib,shutil,re,stat
from batch_results import classify
P=Path(__file__).resolve().parent;M=json.loads((P/'manifest.json').read_text());R=Path('D:/btx-native-035');B=R/'project-build';S=Path(os.environ['GITHUB_WORKSPACE'])/'btx';E=R/'unit-governor-helper-evidence';X=R/'unit-governor-binary';E.mkdir(parents=True,exist_ok=True);STATE=E/'result.json';data=Path('D:/ut'+os.environ['GITHUB_RUN_ID'])
r=json.loads(STATE.read_text()) if STATE.exists() else {'source':M['source'],'patch':M['patch'],'test_btx_sha256':M['binary_sha256'],'compilation':False,'upstream_post':False}
def save():STATE.write_text(json.dumps(r,indent=2)+'\n')
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for v in iter(lambda:f.read(1048576),b''):h.update(v)
 return h.hexdigest()
def cached_verify():
 assert sha(B/'btx-successor.json')==M['checkpoint_sha256'];cp=json.loads((B/'btx-successor.json').read_text());assert cp['source']==M['source'] and cp['build_result']['status']=='UNIT_LINK_PASS'
 for n,a in cp['files'].items():assert sha(R/n)==a['sha256'],n
 assert sha(B/'bin/test_btx.exe')==M['binary_sha256'];return cp

def prepare():
 assert shutil.disk_usage(R).free>8*1024**3
 assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=S,text=True).strip()==M['source']
 shutil.copyfile(P.parent/'modelnet_jit_ensure_tests.fixed.cpp',S/'src/test/modelnet_jit_ensure_tests.cpp')
 cp=cached_verify()
 for n,a in cp['source_files'].items():assert sha(S/n)==a['sha256'],n
 r['restored_files_verified']=len(cp['files']);r['restored_objects_verified']=sum(n.endswith('.obj') for n in cp['files']);r['source_hashes_verified']=len(cp['source_files']);r['status']='RESTORED_VERIFIED';r['runtime_os']=sys.getwindowsversion().platform_version;save()
 r['binary_artifact_reused']=14188085237;save()

def run():
 global tree
 r["baseline_test_btx_sha256"]=M["binary_sha256"];M["binary_sha256"]=r["diagnostic_binary_sha256"];r["test_btx_sha256"]=M["binary_sha256"]
 from job_tree import ProcessTree
 tree=ProcessTree();r['job_active_initial']=tree.active();assert tree.active()==1;r['process_tree_control_reused_from']=43779246167
 assert r['status']=='RESTORED_VERIFIED' and not data.exists() and not Path('S:/').exists();data.mkdir();(data/'tmp').mkdir();r['runtime_root']=str(data);save()
 cp=subprocess.run(['subst','S:',str(data)],capture_output=True,timeout=15);assert cp.returncode==0;r['mapped_short_root']=True;save()
 for key in ['TEMP','TMP','TMPDIR']:os.environ[key]='S:/tmp'
 exe=B/'bin/test_btx.exe'
 def scratch_bytes():
  total=0
  for path in data.rglob('*'):
   try:
    if path.is_file():total+=path.stat().st_size
   except FileNotFoundError:pass # The native tests may atomically remove transient files.
  return total
 def invoke(label,args,cap):
  path=E/(label+'.log');start=time.monotonic();stop=None
  with path.open('wb') as f:
   p=subprocess.Popen([str(exe)]+args,cwd=B,stdout=f,stderr=subprocess.STDOUT)
   try:
    while p.poll() is None:
     time.sleep(1)
     if time.monotonic()-start>cap:stop='TIME_BUDGET'
     elif shutil.disk_usage(R).free<1342177280 or scratch_bytes()>512*1024**2:stop='RESOURCE_RESERVE'
     if stop:subprocess.run(['taskkill','/PID',str(p.pid),'/T','/F'],capture_output=True,timeout=20);p.wait(timeout=20);break
   finally:
    if p.poll() is None:subprocess.run(['taskkill','/PID',str(p.pid),'/T','/F'],capture_output=True,timeout=20);p.wait(timeout=20)
  row={'label':label,'exit':p.returncode,'seconds':round(time.monotonic()-start,3),'budget_stop':stop,'command':[str(exe)]+args,'log_sha256':sha(path),'job_active_after':tree.active()};r.setdefault('commands',[]).append(row);save();assert sha(exe)==M['binary_sha256'];assert tree.active()==1,'Unexpected owned child remains';return row,path.read_text(errors='replace')
 r['no_match_control_reused_from']=43779246167;save()
 report=E/'batch.xml';args=['--run_test='+M['selector_expression'],'--log_level=test_suite','--report_level=detailed','--report_format=XML','--report_sink='+str(report),'--catch_system_errors=yes','--','-testdatadir=S:/n']
 row,log=invoke('governor-helper-3',args,M['batch_budget_seconds']);out=classify(M['selectors'],log,report.read_text(errors='replace') if report.exists() else '',row['exit'],row['budget_stop']);out['report_sha256']=sha(report) if report.exists() else None
 # Preserve the selected cases; unselected skip nodes are not selected-case passes.
 cases=out.pop('cases');out['unselected_report_nodes']=len(set(cases)-set(M['selectors']));out['cases']={n:cases[n] for n in M['selectors'] if n in cases};out['selected_assertions_present']=len(out['cases'])==M['expected_cases'] and all(int(v.get('assertions_passed','0'))>0 for v in out['cases'].values());r['batch']=out;r['hardware_not_run_messages']=[x for x in log.splitlines() if 'NOT_RUN' in x];r['status']='BATCH_PASSED' if out['state']=='passed' and out['selected_assertions_present'] else 'BATCH_NOT_PASSED';save();print(json.dumps(r['batch'],indent=2),flush=True)
 assert out['announced']==1 and out['selected_assertions_present'];r['status']='DIAGNOSTIC_OBSERVED';save()

def cleanup():
 # Previous test controller has exited; its Job Object closes all descendants even on error.
 mapping=subprocess.run(['subst'],capture_output=True,text=True,timeout=15).stdout
 if Path('S:/').exists():
  assert str(data).lower().replace('/','\\') in mapping.lower().replace('/','\\'),mapping
  p=subprocess.run(['subst','S:','/D'],capture_output=True,timeout=15);assert p.returncode==0
 assert not Path('S:/').exists();r['short_drive_removed']=True
 def readonly(fn,name,info):
  path=Path(name);assert path.resolve().is_relative_to(data.resolve())
  if not isinstance(info[1],PermissionError) or path.stat().st_mode&stat.S_IWRITE:raise info[1]
  os.chmod(path,stat.S_IREAD|stat.S_IWRITE);fn(name)
 if data.exists():shutil.rmtree(data,onerror=readonly)
 r['runtime_data_removed']=not data.exists();cp=cached_verify();r['cached_files_unchanged']=len(cp['files']);r['cached_objects_unchanged']=sum(n.endswith('.obj') for n in cp['files']);r['cache_unchanged_verified']=True;save()

try:{'prepare':prepare,'run':run,'cleanup':cleanup}[sys.argv[1]]()
except BaseException as e:r.setdefault('errors',[]).append({'stage':sys.argv[1],'error':repr(e)});save();raise
finally:save()
