"""Native paired cloud/R2 fixture correction; exact cached maintained test target."""
from pathlib import Path
import base64,hashlib,json,os,re,shutil,stat,subprocess,sys
import checkpoint
import integration_support as s
from batch_results import classify
from job_tree import ProcessTree
P=Path(__file__).resolve().parent;I=json.loads((P/'cloud-inputs.json').read_text());s.STATE=s.E/'maintained.json';s.R=json.loads(s.STATE.read_text());R=s.R;sha=checkpoint.digest

def contained():
 tree=ProcessTree();globals()['process_tree']=tree;return tree

def baseline():
 tree=contained();assert R['status']=='RESTORED_VERIFIED' and not s.owned_processes();assert sha(s.BUILD/'bin/test_btx.exe')==I['binary_sha256']
 s.need('cloud-before-inventory',[str(s.BUILD/'bin/test_btx.exe'),'--list_content'],30);R['baseline_inventory_sha256']=sha(s.E/'cloud-before-inventory.log');before=I['reuse_baseline'];assert before['source']==I['integration_base'] and before['binary_sha256']==I['binary_sha256'] and before['inventory_sha256']==R['baseline_inventory_sha256']
 assert [x['selector'] for x in before['cases']]==I['cases'];assert all(x['result']['result'] in ['failed','aborted'] for x in before['cases']);assert before['explicit_permission_errors']==9 and before['cache_files_unchanged']==12837
 R['baseline_reused_from_run']=before['run'];R['baseline_verified']=True;R['status']='CLOUD_R2_BASELINE_REUSED';s.save()

def build():
 tree=contained();assert R['baseline_verified'] and not s.owned_processes();bundle=s.E/'cloud-candidate.bundle';bundle.write_bytes(base64.b64decode((P/'candidate.bundle.base64').read_text()));assert sha(bundle)==I['bundle_sha256'];s.need('cloud-bundle-verify',['git','bundle','verify',str(bundle)],30);s.need('cloud-bundle-fetch',['git','fetch',str(bundle),I['bundle_ref']],30)
 changed=subprocess.check_output(['git','diff','--name-only',I['integration_base'],I['integration']],cwd=s.SOURCE,text=True).splitlines();assert changed==I['changed_files'];s.need('cloud-candidate-checkout',['git','checkout','--detach',I['integration']],30);assert subprocess.check_output(['git','rev-parse','HEAD^{tree}'],cwd=s.SOURCE,text=True).strip()==I['tree']
 for name in changed:assert sha(s.SOURCE/name)==I['candidate_file_sha256'][name]
 candidate=s.catalog(I['integration'],'cloud-before');assert set(candidate['files'])==set(R['source_catalog']['files']);assert [k for k in candidate['files'] if candidate['files'][k]!=R['source_catalog']['files'][k]]==changed;R['candidate_catalog']=candidate;assert not subprocess.check_output(['git','diff','--name-only'],cwd=s.SOURCE,text=True).strip()
 manifest=s.E/'cloud-verified.ninja';shutil.copyfile(s.BUILD/'build.ninja',manifest);assert sha(manifest)==R['original_config']['build.ninja'];R['frozen_manifest_sha256']=sha(manifest);common=['ninja','-C',str(s.BUILD),'-f',str(manifest)]
 s.need('cloud-unit-plan',common+['-n','-d','explain','test_btx'],60);plan=(s.E/'cloud-unit-plan.log').read_text(errors='replace');steps=re.findall(r'^\[(\d+)/(\d+)\]',plan,re.M);R['cloud_planned_steps']=int(steps[-1][1]) if steps else 0;assert 0<R['cloud_planned_steps']<=60;assert 'command line changed for ' not in plan and 'Re-running CMake' not in plan
 objects=re.findall(r'Building CXX object ([^\r\n]+\.obj)',plan);R['cloud_planned_objects']=objects;allowed=['modelnet_cloud_tests.cpp.obj','modelnet_r2_storage_tests.cpp.obj','clientversion.cpp.obj','matmul_v4_rc_production_canary.cpp.obj','matmul_v4_rc_production_golden_manifest.cpp.obj'];assert all(any(x.endswith(z) for z in allowed) for x in objects),objects;assert all(any(x.endswith(z) for x in objects) for z in allowed[:2]);R['status']='CLOUD_R2_BUILDING';s.save()
 s.need('cloud-unit-build',common+['-j','4','-k','1','test_btx'],900)
 for name,value in R['original_config'].items():assert sha(s.BUILD/name)==value,name
 R['candidate_binary_sha256']=sha(s.BUILD/'bin/test_btx.exe');assert R['candidate_binary_sha256']!=I['binary_sha256'];header=(s.BUILD/'src/bitcoin-build-info.h').read_text();assert I['integration'][:7] in header and re.search(r'BUILD_GIT_DIRTY\s+0',header);R['build_info']=header
 s.need('cloud-after-inventory',[str(s.BUILD/'bin/test_btx.exe'),'--list_content'],30);before=(s.E/'cloud-before-inventory.log').read_bytes();after=(s.E/'cloud-after-inventory.log').read_bytes();names=[x.split('/',1)[1].encode() for x in I['new_controls']];lines=after.splitlines(keepends=True);removed=[x for x in lines if any(x.strip().startswith(n+b'*') for n in names)];assert len(removed)==2,removed;assert b''.join(x for x in lines if x not in removed)==before;R['inventory_delta_controls']=I['new_controls'];R['status']='CLOUD_R2_LINKED';s.save();assert tree.active()==1

def run():
 tree=contained();assert R['status']=='CLOUD_R2_LINKED' and not s.owned_processes();assert sha(s.BUILD/'bin/test_btx.exe')==R['candidate_binary_sha256'];R['unit_data']='D:/cr'+os.environ['GITHUB_RUN_ID'];root=Path(R['unit_data']);assert not root.exists() and not Path('S:/').exists();root.mkdir();(root/'tmp').mkdir();s.need('map-cloud',['subst','S:',str(root)],15);os.environ['TMP']=os.environ['TEMP']='S:/tmp'
 try:
  R['cloud_cases']={};s.save()
  for n,selector in enumerate(I['cases']+I['new_controls']):
   label='after-%02d'%n;report=s.E/(label+'.xml');cmd=[str(s.BUILD/'bin/test_btx.exe'),'--run_test='+selector,'--log_level=message','--report_level=detailed','--report_format=XML','--report_sink='+str(report),'--catch_system_errors=yes','--','-testdatadir=S:/f'];rc=s.run(label,cmd,I['per_case_budget_seconds']);log=(s.E/(label+'.log')).read_text(errors='replace');value=classify([selector],log,report.read_text() if report.exists() else '',rc);R['cloud_cases'][selector]={'label':label,'result':value};s.save();assert value['state'] in ['passed','failed'],(selector,value);assert tree.active()==1,'Unexpected descendant after case'
  R['all_cases_passed']=all(x['result']['state']=='passed' for x in R['cloud_cases'].values());R['status']='CLOUD_R2_PASS' if R['all_cases_passed'] else 'CLOUD_R2_REMAINING_BEHAVIOR_FAILURE';s.save()
 finally:s.need('unmap-cloud',['subst','S:','/D'],15);R['short_drive_removed']=not Path('S:/').exists();s.save();assert R['short_drive_removed']
 assert R['all_cases_passed'],'Newly reached behavior failed; do not weaken assertions'

def retain():
 assert not R['process_active'];survivors=s.owned_processes();R['owned_processes_before_cleanup']=survivors;s.quiesce();assert not survivors and R.get('short_drive_removed',True)
 if R.get('unit_data'):
  root=Path(R['unit_data']);assert root==Path('D:/cr'+os.environ['GITHUB_RUN_ID'])
  def readonly(fn,name,exc):
   f=Path(name);assert f.resolve().is_relative_to(root.resolve())
   if not isinstance(exc[1],PermissionError) or f.stat().st_mode&stat.S_IWRITE:raise exc[1]
   os.chmod(f,stat.S_IREAD|stat.S_IWRITE);fn(name)
  if root.exists():shutil.rmtree(root,onerror=readonly)
  R['runtime_data_removed']=not root.exists()
 assert R['status'] in ['CLOUD_R2_PASS','CLOUD_R2_REMAINING_BEHAVIOR_FAILURE'] and R['runtime_data_removed'];assert s.catalog(I['integration'],'cloud-after')==R['candidate_catalog']
 for name,value in R['original_config'].items():assert sha(s.BUILD/name)==value,name
 changes=[]
 for name,item in R['original_objects'].items():
  assert (s.ROOT/name).is_file(),name
  if sha(s.ROOT/name)!=item['sha256']:changes.append(name)
 planned={'project-build/'+x.replace('\\','/') for x in R['cloud_planned_objects']};assert all(x.replace('\\','/') in planned for x in changes),changes;R['changed_objects']=changes;R['original_objects_retained']=len(R['original_objects'])
 for name,item in R['dependencies_before'].items():assert sha(s.ROOT/name)==item['sha256'],name
 R['binaries']={name:sha(s.BUILD/'bin'/(name+'.exe')) for name in ['btxd','btx-cli','btx-tx','btx-util','btx-open','btx-modeld','test_btx']};cp=json.loads((s.BUILD/'btx-checkpoint.json').read_text());R['node_binaries_unchanged']=all(R['binaries'][name]==next(item['sha256'] for file,item in cp['files'].items() if file.replace('\\','/').endswith('/bin/'+name+'.exe')) for name in R['binaries'] if name!='test_btx');assert R['node_binaries_unchanged'];assert R['binaries']['test_btx']==R['candidate_binary_sha256']
 profile={'source':I['integration'],'actual_current_profile':R['actual_profile'],'configuration':R['original_config'],'scope':'Cached unit-only cloud/R2 fixture correction; node binaries remain4609; test outcome explicitly retained'};R['checkpoint_capture']=checkpoint.capture(s.ROOT,s.SOURCE,profile,R['candidate_catalog'],{'status':R['status'],'candidate_binary_sha256':R['candidate_binary_sha256'],'all_cases_passed':R['all_cases_passed']});shutil.copyfile(s.BUILD/'btx-checkpoint.json',s.E/'cloud-checkpoint.json');R['checkpoint_sha256']=sha(s.BUILD/'btx-checkpoint.json');R['checkpoint_key']=hashlib.sha256(json.dumps(profile,sort_keys=True).encode()).hexdigest();R['retention_verified']=True;s.save()
 with open(os.environ['GITHUB_OUTPUT'],'a') as f:f.write('checkpoint_valid=true\ncheckpoint_key='+R['checkpoint_key']+'\n')
try:{'baseline':baseline,'build':build,'run':run,'retain':retain}[sys.argv[1]]()
except BaseException as e:R.setdefault('cloud_failures',[]).append({'stage':sys.argv[1],'type':type(e).__name__,'error':str(e)});s.save();raise
finally:s.save()
