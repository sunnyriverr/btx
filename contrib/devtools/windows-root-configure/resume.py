"""Normal current maintained build, immutable progress checkpoint, bounded units."""
from pathlib import Path
from collections import defaultdict
import json,os,sys,subprocess,re,shutil,stat,hashlib
import checkpoint
import integration_support as s
from job_tree import ProcessTree
P=Path(__file__).resolve().parent;I=json.loads((P/'current-inputs.json').read_text());C=json.loads((P/'maintained-inputs.json').read_text());s.STATE=s.E/'maintained.json';s.R=json.loads(s.STATE.read_text());R=s.R;sha=checkpoint.digest
TARGETS=['btxd','btx-cli','btx-tx','btx-util','btx-open','btx-modeld','test_btx']

def dependencies():
 excluded='vcpkg-installed/vcpkg/compiler-file-hash-cache.json'
 old={n.replace('\\','/'):v['sha256']for n,v in R['dependencies_before'].items()if n.replace('\\','/')!=excluded}
 new={str(p.relative_to(s.ROOT)).replace('\\','/'):sha(p)for p in(s.ROOT/'vcpkg-installed').rglob('*')if p.is_file()and not p.is_symlink()and str(p.relative_to(s.ROOT)).replace('\\','/')!=excluded}
 assert old==new,'Installed dependency content/set changed'
 for n,h in R['actual_profile']['openssl_files'].items():assert sha(s.ROOT/'openssl-3.5.4-static'/n)==h
 R['dependencies_verified']=len(old)

def inventory(text):
 nodes=[];stack=[]
 for line in text.splitlines():
  if not line.strip():continue
  spaces=len(line)-len(line.lstrip());assert spaces%4==0;depth=spaces//4;assert depth<=len(stack);stack=stack[:depth];name=line.strip();enabled=name.endswith('*')and all(x['enabled']for x in stack);name=name.removesuffix('*');node={'name':name,'depth':depth,'enabled':enabled,'path':'/'.join([x['name']for x in stack]+[name])};nodes.append(node);stack.append(node)
 leaves=[x for i,x in enumerate(nodes)if(i+1==len(nodes)or nodes[i+1]['depth']<=x['depth'])and x['depth']>0];enabled=[x['path']for x in leaves if x['enabled']];assert len(enabled)==len(set(enabled))and enabled;groups=defaultdict(list)
 for x in enabled:groups[x.split('/')[0]].append(x)
 jobs=[]
 for suite,paths in groups.items():
  lane='modelnet'if suite.startswith('modelnet')else'proof'if suite.startswith(('matmul','smile','shielded'))else'other';chunk=[]
  for path in paths:
   assert len(path)<24000
   if chunk and(len(chunk)>=200 or len(':'.join(chunk+[path]))>=24000):jobs.append({'suite':suite,'lane':lane,'selectors':chunk,'expected_cases':len(chunk),'timeout_seconds':300 if lane=='proof'else 120});chunk=[]
   chunk.append(path)
  if chunk:jobs.append({'suite':suite,'lane':lane,'selectors':chunk,'expected_cases':len(chunk),'timeout_seconds':300 if lane=='proof'else 120})
 selected=json.loads((P/'selected-cases.json').read_text())['selectors'];assert len(selected)==len(set(selected))==31;assert set(selected)<=set(enabled),(set(selected)-set(enabled));R['registered_enabled_cases']=len(enabled);R['explicit_selected_cases']=len(selected)
 jobs=[{'suite':path.split('/')[0],'lane':'selected','selectors':[path],'expected_cases':1,'timeout_seconds':60}for path in selected]
 return {'source':I['target'],'binary_sha256':R['unit_binary_sha256'],'inventory_sha256':sha(s.E/'unit-inventory.log'),'jobs':jobs,'all_enabled_cases':selected,'registered_enabled_cases':len(enabled),'disabled_cases':[x['path']for x in leaves if not x['enabled']],'campaign_test_budget_seconds':C['unit_budget_seconds'],'batch_budget_seconds':600,'require_first_pass_control':False,'scope':'Explicit31affected/controlcases, not all-enabled or full unit acceptance.'}

def build():
 tree=ProcessTree();assert R['status']=='CURRENT_PLANS_CAPTURED';assert s.catalog(I['target'],'full-build-before')==R['current_source_catalog'];assert not s.owned_processes();plan=R['current_plans']['full'];assert plan['steps']<=C['max_build_steps']and plan['command_invalidations']<=C['max_command_invalidations'];R.update(status='CURRENT_FULL_BUILDING',full_build_invoked=True,unit_built=False,unit_invoked=False,maintained_targets=TARGETS);s.save()
 # Use the ordinary maintained root build, not the copied observation manifest.
 cmd=['cmake','--build',str(s.BUILD),'--target']+TARGETS+['--parallel','4','--','-k','0'];R['full_build_command']=cmd
 try:code=s.run('candidate-unit-build',cmd,C['build_budget_seconds'])
 except BaseException:
  R['status']='CURRENT_FULL_BUILD_INTERRUPTED';s.save();raise
 R['unit_build_exit']=code;R['current_configuration_after_build']={n:sha(s.BUILD/n)for n in R['current_configuration']};assert R['current_configuration_after_build']==R['current_configuration'],'Normal bootstrap changed the verified generated graph';assert s.catalog(I['target'],'full-build-after')==R['current_source_catalog'];dependencies()
 if code:
  text=(s.E/'candidate-unit-build.log').read_text(errors='replace');R['build_error_lines']=[x for x in text.splitlines()if re.search(r'\berror(?: [A-Z]+\d+)?:|undefined symbol|unresolved external',x)];R['status']='CURRENT_FULL_BUILD_FAILURE';s.save();raise RuntimeError('Actual current generated compiler/link blocker; retain progress before further work')
 R['binaries']={n:sha(s.BUILD/'bin'/(n+'.exe'))for n in TARGETS};R['unit_binary_sha256']=R['binaries']['test_btx'];R['unit_built']=True;R['build_info']=(s.BUILD/'src/bitcoin-build-info.h').read_text();assert I['target'][:7]in R['build_info']and re.search(r'BUILD_GIT_DIRTY\s+0',R['build_info']);s.need('unit-imports',['dumpbin','/dependents',str(s.BUILD/'bin/test_btx.exe')],60);s.need('unit-inventory',[str(s.BUILD/'bin/test_btx.exe'),'--list_content'],180);s.need('node-version',[str(s.BUILD/'bin/btxd.exe'),'-version'],30);manifest=inventory((s.E/'unit-inventory.log').read_text());(P/'completion-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n');(s.E/'completion-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n');R['enabled_case_count']=len(manifest['all_enabled_cases']);R['planned_unit_jobs']=len(manifest['jobs']);R['status']='CURRENT_FULL_LINKED';s.save();assert tree.active()==1

def retain():
 assert not R['process_active'];prior=s.owned_processes();R['owned_processes_before_retention']=prior;s.quiesce();assert not prior;assert s.catalog(I['target'],'full-retained')==R['current_source_catalog'];dependencies();config={n:sha(s.BUILD/n)for n in R['current_configuration']};assert config==R['current_configuration'];profile={'source':I['target'],'actual_current_profile':R['actual_profile'],'input_source':I['cached_source'],'input_cache_key':C['key'],'input_checkpoint_sha256':C['checkpoint_sha256'],'configuration':config,'normal_cmake_regeneration':True,'normal_root_build':bool(R.get('full_build_invoked')),'full_maintained_target':True,'unit_scope':'explicit31cases_only','scope':C['scope'],'controller_sha256':sha(P/'resume.py')};R['profile']=profile;R['checkpoint_capture']=checkpoint.capture(s.ROOT,s.SOURCE,profile,R['current_source_catalog'],{'status':R['status'],'unit_build_exit':R.get('unit_build_exit'),'unit_built':R.get('unit_built',False),'unit_invoked':False});shutil.copyfile(s.BUILD/'btx-checkpoint.json',s.E/'current-full-checkpoint.json');cp=json.loads((s.BUILD/'btx-checkpoint.json').read_text());R['objects_retained']=sum(n.endswith('.obj')for n in cp['files']);R['checkpoint_sha256']=sha(s.BUILD/'btx-checkpoint.json');R['checkpoint_key']=hashlib.sha256(json.dumps(profile,sort_keys=True).encode()).hexdigest();R['retention_verified']=True;s.save()
 with open(os.environ['GITHUB_OUTPUT'],'a')as f:f.write('checkpoint_valid=true\ncheckpoint_key='+R['checkpoint_key']+'\n')

def readonly(function,filename,exc_info):
 path=Path(filename);assert path.resolve().is_relative_to(Path(R['unit_data']).resolve());error=exc_info[1]
 if not isinstance(error,PermissionError)or path.stat().st_mode&stat.S_IWRITE:raise error
 os.chmod(path,stat.S_IREAD|stat.S_IWRITE);function(filename)

def finish():
 assert not R['process_active'];prior=s.owned_processes();R['owned_processes_before_cleanup']=prior;s.quiesce();assert not prior
 if R.get('unit_data'):
  data=Path(R['unit_data']);assert data.parent==Path('D:/')and data.name=='bc'+os.environ['GITHUB_RUN_ID']
  if data.exists():shutil.rmtree(data,onerror=readonly)
  assert not data.exists();R['runtime_data_removed']=True;assert not Path('S:/').exists()
 assert s.catalog(I['target'],'current-full-final')==R['current_source_catalog'];dependencies()
 if R.get('retention_verified'):
  marker=s.BUILD/'btx-checkpoint.json';assert sha(marker)==R['checkpoint_sha256'];cp=json.loads(marker.read_text());changed=[n for n,i in cp['files'].items()if not(s.ROOT/n).is_file()or sha(s.ROOT/n)!=i['sha256']];R['cache_files_changed_during_units']=changed;assert not changed
 R['cleanup_verified']=True;R['source_unchanged']=True
 if R.get('batch_results'):
  from collections import Counter
  M=json.loads((s.E/'completion-manifest.json').read_text());done={j['suite'] for j in R['batch_results']};attempted={x for j in R['batch_results']for x in j['cases']if j['cases'][x].get('result')!='skipped'};planned=[p for j in M['jobs']for p in j['selectors']];R['unit_summary']={'planned_enabled':len(planned),'jobs_attempted':len(R['batch_results']),'jobs_planned':len(M['jobs']),'job_outcomes':dict(Counter(j['state']for j in R['batch_results'])),'reported_attempted_cases':len(attempted),'unattempted_not_a_pass':len(set(planned)-attempted),'campaign_stop':R.get('campaign_stop'),'full_pass':R.get('campaign_stop')=='ALL_PENDING_JOBS_ATTEMPTED'and all(j['state']=='passed'for j in R['batch_results'])};assert attempted<=set(planned);R['all_units_passed']=R['unit_summary']['full_pass']
 s.save()

def verdict():
 R['selected_cases_all_passed']=bool(R.get('all_units_passed'));R['full_unit_acceptance']=False
 assert R.get('unit_built')and R.get('cleanup_verified')and R.get('retention_verified')and R['selected_cases_all_passed'], 'Selected current Windows prerequisite cases failed or incomplete; scoped logs/checkpoint retained'
try:{'build':build,'retain':retain,'finish':finish,'verdict':verdict}[sys.argv[1]]()
except BaseException as e:R.setdefault('full_resume_failures',[]).append({'stage':sys.argv[1],'type':type(e).__name__,'error':str(e)});s.save();raise
finally:s.save()
