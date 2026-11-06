"""Unchanged native cloud/R2 prerequisite observation using exact saved binary."""
from pathlib import Path
import hashlib,json,os,shutil,stat,sys
import checkpoint
import integration_support as s
from batch_results import classify
from job_tree import ProcessTree
P=Path(__file__).resolve().parent;I=json.loads((P/'cloud-inputs.json').read_text())
s.STATE=s.E/'maintained.json';s.R=json.loads(s.STATE.read_text());R=s.R;sha=checkpoint.digest

def run():
 tree=ProcessTree();assert R['status']=='RESTORED_VERIFIED' and not s.owned_processes()
 assert sha(s.BUILD/'bin/test_btx.exe')==I['binary_sha256']
 s.need('cloud-inventory',[str(s.BUILD/'bin/test_btx.exe'),'--list_content'],30)
 R['inventory_sha256']=sha(s.E/'cloud-inventory.log');R['unit_data']='D:/cr'+os.environ['GITHUB_RUN_ID'];root=Path(R['unit_data']);assert not root.exists() and not Path('S:/').exists();root.mkdir();(root/'tmp').mkdir()
 s.need('map-cloud',['subst','S:',str(root)],15);os.environ['TMP']=os.environ['TEMP']='S:/tmp'
 try:
  R['cloud_cases']={};s.save()
  for n,selector in enumerate(I['cases']):
   label='before-%02d'%n;report=s.E/(label+'.xml');cmd=[str(s.BUILD/'bin/test_btx.exe'),'--run_test='+selector,'--log_level=message','--report_level=detailed','--report_format=XML','--report_sink='+str(report),'--catch_system_errors=yes','--','-testdatadir=S:/f']
   rc=s.run(label,cmd,I['per_case_budget_seconds']);log=(s.E/(label+'.log')).read_text(errors='replace');value=classify([selector],log,report.read_text() if report.exists() else '',rc)
   R['cloud_cases'][selector]={'label':label,'result':value,'permission_error_explicit':'credential file must be mode 0600' in log};s.save();assert value['state']=='failed' and value['cases'][selector]['result'] in ['failed','aborted'],(selector,value)
   assert tree.active()==1,'Unexpected descendant after selected case'
  assert R['cloud_cases'][I['actual_error_case']]['permission_error_explicit'];R['actual_error_confirmed']=True;R['status']='CLOUD_R2_BASELINE_CONFIRMED';s.save()
 finally:
  s.need('unmap-cloud',['subst','S:','/D'],15);R['short_drive_removed']=not Path('S:/').exists();s.save();assert R['short_drive_removed']

def retain():
 assert not R['process_active'];R['owned_processes_before_cleanup']=s.owned_processes();s.quiesce();assert not R['owned_processes_before_cleanup'];assert R.get('short_drive_removed',True)
 if R.get('unit_data'):
  root=Path(R['unit_data']);assert root==Path('D:/cr'+os.environ['GITHUB_RUN_ID'])
  def readonly(fn,name,exc):
   f=Path(name);assert f.resolve().is_relative_to(root.resolve())
   if not isinstance(exc[1],PermissionError) or f.stat().st_mode&stat.S_IWRITE:raise exc[1]
   os.chmod(f,stat.S_IREAD|stat.S_IWRITE);fn(name)
  if root.exists():shutil.rmtree(root,onerror=readonly)
  R['runtime_data_removed']=not root.exists()
 assert R['status']=='CLOUD_R2_BASELINE_CONFIRMED' and R['runtime_data_removed']
 assert s.catalog(I['source'],'cloud-after')==R['source_catalog']
 cp=json.loads((s.BUILD/'btx-checkpoint.json').read_text());assert sha(s.BUILD/'btx-checkpoint.json')==I['checkpoint_sha256'];R['unchanged_cache_verification']=checkpoint.restore(s.ROOT,s.SOURCE,cp['profile'],R['source_catalog']);assert sha(s.BUILD/'bin/test_btx.exe')==I['binary_sha256'];R['retention_verified']=True;s.save()
try:{'run':run,'retain':retain}[sys.argv[1]]()
except BaseException as e:R.setdefault('cloud_failures',[]).append({'stage':sys.argv[1],'type':type(e).__name__,'error':str(e)});s.save();raise
finally:s.save()
