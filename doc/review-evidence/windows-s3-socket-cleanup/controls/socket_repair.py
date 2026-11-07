"""Bounded native S3 cleanup before/after; never rerun the19 passed cases."""
from pathlib import Path
import base64,hashlib,json,os,re,shutil,stat,subprocess,sys
import checkpoint
import integration_support as s
from batch_results import classify
from job_tree import ProcessTree
P=Path(__file__).resolve().parent;I=json.loads((P/'cloud-inputs.json').read_text());s.STATE=s.E/'maintained.json';s.R=json.loads(s.STATE.read_text());R=s.R;sha=checkpoint.digest

def contained():
 tree=ProcessTree();globals()['process_tree']=tree;return tree

def mapped():
 R['unit_data']='D:/sr'+os.environ['GITHUB_RUN_ID'];root=Path(R['unit_data']);assert not Path('S:/').exists();root.mkdir(exist_ok=True);(root/'tmp').mkdir(exist_ok=True);s.need('map-'+sys.argv[1],['subst','S:',str(root)],15);os.environ['TMP']=os.environ['TEMP']='S:/tmp';s.save()

def unmap():
 s.need('unmap-'+sys.argv[1],['subst','S:','/D'],15);R['short_drive_removed']=not Path('S:/').exists();s.save();assert R['short_drive_removed']

def observe(label,selector,expected):
 report=s.E/(label+'.xml');cmd=[str(s.BUILD/'bin/test_btx.exe'),'--run_test='+selector,'--log_level=message','--report_level=detailed','--report_format=XML','--report_sink='+str(report),'--catch_system_errors=yes','--','-testdatadir=S:/f'];rc=s.run(label,cmd,60)
 log=(s.E/(label+'.log')).read_text(errors='replace');v=classify([selector],log,report.read_text() if report.exists() else '',rc);R.setdefault('socket_cases',{})[label]={'selector':selector,'expected':expected,'result':v,'binary_sha256':sha(s.BUILD/'bin/test_btx.exe')};s.save();assert globals()['process_tree'].active()==1
 if expected=='aborted':assert v['state']=='failed' and v['cases'][selector]['result']=='aborted' and 'Invalid parameter detected by C runtime library' in log
 else:assert v['state']=='passed' and rc==0,(selector,v)

def build_stage(label,target,changed,required):
 assert not s.owned_processes();s.need(label+'-checkout',['git','checkout','--detach',target],30)
 catalog=s.catalog(target,label);prior=R.get('current_catalog',R['source_catalog']);assert set(catalog['files'])==set(prior['files']);delta=[k for k in catalog['files'] if catalog['files'][k]!=prior['files'][k]];assert delta==changed,delta
 assert not subprocess.check_output(['git','diff','--name-only'],cwd=s.SOURCE,text=True).strip();manifest=s.E/(label+'-verified.ninja');shutil.copyfile(s.BUILD/'build.ninja',manifest);assert sha(manifest)==R['original_config']['build.ninja'];common=['ninja','-C',str(s.BUILD),'-f',str(manifest)]
 s.need(label+'-plan',common+['-n','-d','explain','test_btx'],60);plan=(s.E/(label+'-plan.log')).read_text(errors='replace');steps=re.findall(r'^\[(\d+)/(\d+)\]',plan,re.M);n=int(steps[-1][1]) if steps else 0;assert 0<n<=60;assert 'command line changed for ' not in plan and 'Re-running CMake' not in plan
 objects=re.findall(r'Building CXX object ([^\r\n]+\.obj)',plan);allowed=required+['clientversion.cpp.obj','matmul_v4_rc_production_canary.cpp.obj','matmul_v4_rc_production_golden_manifest.cpp.obj'];assert all(any(x.endswith(a) for a in allowed) for x in objects),objects;assert all(any(x.endswith(a) for x in objects) for a in required)
 links=re.findall(r'Linking CXX executable bin[\\/]([^\r\n]+)\.exe',plan);assert set(links)<=set(['test_btx','btxd','btx-open','btx-modeld']);R.setdefault('socket_builds',{})[label]={'target':target,'planned_steps':n,'planned_objects':objects,'planned_links':links};s.save()
 s.need(label+'-build',common+['-j','4','-k','1','test_btx'],900)
 for name,value in R['original_config'].items():assert sha(s.BUILD/name)==value,name
 header=(s.BUILD/'src/bitcoin-build-info.h').read_text();assert target[:7] in header and re.search(r'BUILD_GIT_DIRTY\s+0',header)
 s.need(label+'-inventory',[str(s.BUILD/'bin/test_btx.exe'),'--list_content'],30);inventory=(s.E/(label+'-inventory.log')).read_bytes();original=(s.E/'original-inventory.log').read_bytes();names=[x.split('/',1)[1].encode() for x in I['new_controls']];lines=inventory.splitlines(keepends=True);new=[x for x in lines if any(x.strip().startswith(k+b'*') for k in names)];assert len(new)==2 and b''.join(x for x in lines if x not in new)==original
 R['socket_builds'][label].update(binary_sha256=sha(s.BUILD/'bin/test_btx.exe'),build_info=header);R['current_catalog']=catalog;s.save()

def baseline():
 tree=contained();assert R['status']=='RESTORED_VERIFIED' and not s.owned_processes();assert sha(s.BUILD/'bin/test_btx.exe')==I['binary_sha256'];s.need('original-inventory',[str(s.BUILD/'bin/test_btx.exe'),'--list_content'],30)
 assert I['reused_baseline']['baseline_source']==I['integration_base'] and I['reused_baseline']['baseline_binary_sha256']==I['binary_sha256'];R['reused_baseline']=I['reused_baseline'];R['baseline_inventory_sha256']=sha(s.E/'original-inventory.log')
 bundle=s.E/'socket-candidate.bundle';bundle.write_bytes(base64.b64decode((P/'candidate.bundle.base64').read_text()));assert sha(bundle)==I['bundle_sha256'];s.need('socket-bundle-verify',['git','bundle','verify',str(bundle)],30);s.need('socket-bundle-fetch',['git','fetch',str(bundle),I['bundle_ref']],30)
 build_stage('before',I['baseline'],['src/test/modelnet_cloud_tests.cpp'],['modelnet_cloud_tests.cpp.obj']);mapped()
 try:
  for n,selector in enumerate(I['new_controls']):observe('before-'+str(n),selector,'aborted')
  R['status']='SOCKET_BASELINE_CONFIRMED';s.save()
 finally:unmap()

def build():
 tree=contained();assert R['status']=='SOCKET_BASELINE_CONFIRMED';build_stage('after',I['integration'],['src/modelnet/s3_client.cpp'],['s3_client.cpp.obj']);R['candidate_catalog']=R['current_catalog'];R['candidate_binary_sha256']=sha(s.BUILD/'bin/test_btx.exe');R['status']='SOCKET_REPAIR_LINKED';s.save();assert tree.active()==1

def run():
 tree=contained();assert R['status']=='SOCKET_REPAIR_LINKED';mapped()
 try:
  for n,selector in enumerate(I['cases']+I['new_controls']):observe('after-'+str(n),selector,'passed')
  R['status']='SOCKET_REPAIR_PASS';s.save()
 finally:unmap()

def retain():
 assert not R['process_active'];R['owned_processes_before_cleanup']=s.owned_processes();s.quiesce();assert not R['owned_processes_before_cleanup'] and R.get('short_drive_removed',True)
 if R.get('unit_data'):
  root=Path(R['unit_data']);assert root==Path('D:/sr'+os.environ['GITHUB_RUN_ID'])
  def readonly(fn,name,exc):
   f=Path(name);assert f.resolve().is_relative_to(root.resolve())
   if not isinstance(exc[1],PermissionError) or f.stat().st_mode&stat.S_IWRITE:raise exc[1]
   os.chmod(f,stat.S_IREAD|stat.S_IWRITE);fn(name)
  if root.exists():shutil.rmtree(root,onerror=readonly)
  R['runtime_data_removed']=not root.exists()
 assert R['status']=='SOCKET_REPAIR_PASS' and R['runtime_data_removed'];assert s.catalog(I['integration'],'socket-after')==R['candidate_catalog']
 for name,value in R['original_config'].items():assert sha(s.BUILD/name)==value,name
 changes=[]
 for name,item in R['original_objects'].items():
  assert (s.ROOT/name).is_file(),name
  if sha(s.ROOT/name)!=item['sha256']:changes.append(name)
 planned={'project-build/'+x.replace('\\','/') for b in R['socket_builds'].values() for x in b['planned_objects']};assert all(x.replace('\\','/') in planned for x in changes),changes;R['changed_objects']=changes;R['original_objects_retained']=len(R['original_objects'])
 for name,item in R['dependencies_before'].items():assert sha(s.ROOT/name)==item['sha256'],name
 R['binaries']={name:sha(s.BUILD/'bin'/(name+'.exe')) for name in ['btxd','btx-cli','btx-tx','btx-util','btx-open','btx-modeld','test_btx']};cp=json.loads((s.BUILD/'btx-checkpoint.json').read_text());links=set(x for b in R['socket_builds'].values() for x in b['planned_links']);R['unchanged_binaries']={name:R['binaries'][name]==next(x['sha256'] for file,x in cp['files'].items() if file.replace('\\','/').endswith('/bin/'+name+'.exe')) for name in R['binaries']};assert all(ok for name,ok in R['unchanged_binaries'].items() if name not in links);assert R['binaries']['test_btx']==R['candidate_binary_sha256']
 profile={'source':I['integration'],'actual_current_profile':R['actual_profile'],'configuration':R['original_config'],'scope':'Scoped S3 cleanup native cached integration; not whole d522/release build qualification; planned metadata app relinks'};R['checkpoint_capture']=checkpoint.capture(s.ROOT,s.SOURCE,profile,R['candidate_catalog'],{'status':R['status'],'candidate_binary_sha256':R['candidate_binary_sha256']});shutil.copyfile(s.BUILD/'btx-checkpoint.json',s.E/'socket-checkpoint.json');R['checkpoint_sha256']=sha(s.BUILD/'btx-checkpoint.json');R['checkpoint_key']=hashlib.sha256(json.dumps(profile,sort_keys=True).encode()).hexdigest();R['retention_verified']=True;s.save()
 with open(os.environ['GITHUB_OUTPUT'],'a') as f:f.write('checkpoint_valid=true\ncheckpoint_key='+R['checkpoint_key']+'\n')
try:{'baseline':baseline,'build':build,'run':run,'retain':retain}[sys.argv[1]]()
except BaseException as e:R.setdefault('socket_failures',[]).append({'stage':sys.argv[1],'type':type(e).__name__,'error':str(e)});s.save();raise
finally:s.save()
