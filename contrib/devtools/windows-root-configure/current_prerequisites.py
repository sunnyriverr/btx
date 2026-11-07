"""Current accepted Windows configure/plan/three-object diagnosis, no repair/run/cache-save."""
from pathlib import Path
import json,os,re,subprocess,shutil,sys
import checkpoint
import integration_support as s
from job_tree import ProcessTree
P=Path(__file__).resolve().parent;I=json.loads((P/'current-inputs.json').read_text());s.STATE=s.E/'maintained.json';s.R=json.loads(s.STATE.read_text());R=s.R;sha=checkpoint.digest

def settings():
 vals={}
 for line in (s.BUILD/'CMakeCache.txt').read_text().splitlines():
  if line and not line.startswith(('#','//')) and '=' in line:
   k,v=line.split('=',1);vals[k]=v
 for k in ['WITH_MODELNET:BOOL','BUILD_TESTS:BOOL','ENABLE_WALLET:BOOL','WITH_ZMQ:BOOL']:assert vals.get(k)=='ON',(k,vals.get(k))
 assert vals['CMAKE_HOME_DIRECTORY:INTERNAL'].replace('\\','/')==str(s.SOURCE).replace('\\','/')
 return vals

def verify_dependencies():
    excluded = 'vcpkg-installed/vcpkg/compiler-file-hash-cache.json'
    before = {name.replace('\\','/'): item['sha256'] for name,item in R['dependencies_before'].items() if name.replace('\\','/') != excluded}
    after = {str(path.relative_to(s.ROOT)).replace('\\','/'): sha(path) for path in (s.ROOT/'vcpkg-installed').rglob('*') if path.is_file() and not path.is_symlink() and str(path.relative_to(s.ROOT)).replace('\\','/') != excluded}
    R['dependency_set_check'] = {'before_count': len(before), 'after_count': len(after), 'added': sorted(after.keys()-before.keys()), 'removed': sorted(before.keys()-after.keys()), 'changed': sorted(name for name in before.keys()&after.keys() if before[name]!=after[name]), 'excluded': excluded}
    s.save(); assert before == after, R['dependency_set_check']
    for name,h in R['actual_profile']['openssl_files'].items(): assert sha(s.ROOT/'openssl-3.5.4-static'/name)==h,name

def configure():
 tree=ProcessTree();assert R['status']=='RESTORED_VERIFIED' and not s.owned_processes();assert sha(s.BUILD/'bin/test_btx.exe')==I['cached_binary_sha256'];R['node_binaries_before']={n:sha(s.BUILD/'bin'/(n+'.exe')) for n in I['binaries']};R['cached_commands']=json.loads((s.BUILD/'compile_commands.json').read_text());shutil.copyfile(s.BUILD/'compile_commands.json',s.E/'cached-compile-commands.json')
 s.need('current-fetch',['git','fetch','--no-tags','--depth=2','https://github.com/btxchain/btx.git',I['target']],180);s.need('current-checkout',['git','checkout','--detach',I['target']],60);cat=s.catalog(I['target'],'current-before');old=R['source_catalog'];R['current_source_catalog']=cat;added=sorted(cat['files'].keys()-old['files'].keys());removed=sorted(old['files'].keys()-cat['files'].keys());assert added==I['added_files'] and removed==I['removed_files'],(added,removed);delta=sorted(k for k in cat['files'].keys()|old['files'].keys() if cat['files'].get(k)!=old['files'].get(k));assert delta==I['source_delta'];R['current_source_delta']=delta;R['current_added_files']=added;R['current_removed_files']=removed
 for name in ['vcpkg.json','CMakeLists.txt']:assert cat['files'][name]==old['files'][name],name
 R['settings_before']=settings();args=R['actual_profile']['args'];assert args[0]=='cmake' and '-DWITH_MODELNET=ON' in args and '-DBUILD_TESTS=ON' in args
 os.environ.update(VCPKG_ROOT=str(s.ROOT/'vcpkg'),VCPKG_DISABLE_METRICS='1',VCPKG_MAX_CONCURRENCY='2',VCPKG_BINARY_SOURCES='clear;files,'+str(s.ROOT/'binary-cache')+',read')
 R['current_configure_command']=args;R['status']='CURRENT_CONFIGURING';s.save();code=s.run('current-normal-configure',args,900);R['current_configure_exit']=code
 R['configure_diagnostics']={}
 for name in ['CMakeCache.txt','CMakeFiles/CMakeConfigureLog.yaml','CMakeFiles/CMakeError.log','vcpkg-manifest-install.log']:
  path=s.BUILD/name
  if path.is_file():
   dest=s.E/('current-configure-'+Path(name).name);shutil.copyfile(path,dest);R['configure_diagnostics'][name]={'archive_file':dest.name,'sha256':sha(dest)}
 s.save()
 if code:
  R['status']='CURRENT_CONFIGURE_BLOCKER_CAPTURED';s.save();return
 R['current_configuration']={n:sha(s.BUILD/n) for n in R['original_config']};R['settings_after']=settings();new=json.loads((s.BUILD/'compile_commands.json').read_text());shutil.copyfile(s.BUILD/'compile_commands.json',s.E/'current-compile-commands.json');oldcmd={x['output']:x for x in R['cached_commands']};newcmd={x['output']:x for x in new};changed=[k for k in sorted(oldcmd.keys()&newcmd.keys()) if oldcmd[k]!=newcmd[k]]
 R['command_delta']={'before':len(oldcmd),'after':len(newcmd),'added':sorted(newcmd.keys()-oldcmd.keys()),'removed':sorted(oldcmd.keys()-newcmd.keys()),'changed_count':len(changed),'changed_unit_count':sum('/test_btx.dir/' in k.replace('\\','/') for k in changed)};examples=[{'output':k,'before':oldcmd[k],'after':newcmd[k]} for k in changed];(s.E/'compile-command-deltas.json').write_text(json.dumps(examples,indent=2)+'\n');R['selected_commands']={}
 for suffix in I['selected_sources']:
  match=[v for v in new if v['file'].replace('\\','/').endswith('/'+suffix) and '/test_btx.dir/' in v['output'].replace('\\','/')];assert len(match)==1,(suffix,len(match));v=match[0];output=Path(v['output']);output=output if output.is_absolute() else s.BUILD/output;rel=str(output.relative_to(s.BUILD)).replace('\\','/');R['selected_commands'][suffix]={'entry':v,'target':rel,'object_exists_before':output.is_file(),'object_mtime_ns_before':output.stat().st_mtime_ns if output.exists() else None,'object_sha256_before':sha(output) if output.is_file() else None}
 for name,item in R['original_objects'].items():assert sha(s.ROOT/name)==item['sha256'],name
 verify_dependencies()
 assert s.catalog(I['target'],'current-configured')==cat;R['status']='CURRENT_NORMAL_CONFIGURED';s.save();assert tree.active()==1

def plans():
 tree=ProcessTree()
 if R['status']=='CURRENT_CONFIGURE_BLOCKER_CAPTURED':return
 assert R['status']=='CURRENT_NORMAL_CONFIGURED';s.need('current-verify-globs',['cmake','-P',str(s.BUILD/'CMakeFiles/VerifyGlobs.cmake')],120,cwd=s.BUILD);assert 'GLOB mismatch!' not in (s.E/'current-verify-globs.log').read_text()
 R['current_plans']={}
 for label,targets in [('node',['btxd']),('full',['btxd','btx-cli','btx-tx','btx-util','btx-open','btx-modeld','test_btx']),('selected',[x['target'] for x in R['selected_commands'].values()])]:
  code=s.run('current-'+label+'-plan',['ninja','-C',str(s.BUILD),'-n','-d','explain']+targets,120);text=(s.E/('current-'+label+'-plan.log')).read_text(errors='replace');actions=re.findall(r'^\[\d+/\d+\] (.*)',text,re.M);objects=[a.removeprefix('Building CXX object ').replace('\\','/') for a in actions if a.startswith('Building CXX object ')];R['current_plans'][label]={'exit':code,'actions':actions,'steps':len(actions),'objects':objects,'command_invalidations':text.count('ninja explain: command line changed for ')};s.save();assert code==0,'Actual current graph planning failed'
  if label=='selected':
   allowed={'Generating bitcoin-build-info.h','Re-checking globbed directories...'};bad=[a for a in actions if not a.startswith('Building CXX object ') and a not in allowed];assert not bad,('Non-object actions would expand diagnostic',bad);assert 0<len(actions)<=I['max_selected_steps'] and len(objects)<=I['max_selected_objects'];assert set(objects)==set(targets),(objects,targets)
 R['status']='CURRENT_PLANS_CAPTURED';s.save();assert tree.active()==1

def compile_selected():
 tree=ProcessTree()
 if R['status']=='CURRENT_CONFIGURE_BLOCKER_CAPTURED':return
 assert R['status']=='CURRENT_PLANS_CAPTURED';targets=[x['target'] for x in R['selected_commands'].values()];code=s.run('current-selected-compile',['ninja','-C',str(s.BUILD),'-j','2','-k','0']+targets,600);text=(s.E/'current-selected-compile.log').read_text(errors='replace');R['selected_compile_exit']=code;R['selected_object_results']={}
 for name,item in R['selected_commands'].items():
  obj=s.BUILD/item['target'];R['selected_object_results'][name]={'target':item['target'],'exists_after':obj.is_file(),'sha256_after':sha(obj) if obj.is_file() else None,'mtime_ns_after':obj.stat().st_mtime_ns if obj.is_file() else None,'command':item['entry']['command']}
 failures=[line for line in text.splitlines() if line.startswith('FAILED:')];R['compiler_error_lines']=[line for line in text.splitlines() if re.search(r'\berror(?: [A-Z]+\d+)?:',line)];R['failed_action_lines']=failures
 expected={'src/test/modelnet_035_wan_endpoint_tests.cpp':['mkfifo'],'src/test/modelnet_ahp_comp_tests.cpp':['popen','pclose']}
 for name,words in expected.items():
  assert any(Path(name).name+'.obj' in line for line in failures),(name,failures)
  for word in words:assert any(Path(name).name in line and word in line and 'error' in line for line in text.splitlines()),(name,word)
 positive=I['positive_source'];item=R['selected_object_results'][positive];assert item['exists_after'] and item['mtime_ns_after']!=R['selected_commands'][positive]['object_mtime_ns_before'];assert not any(Path(positive).name+'.obj' in line for line in failures);assert code!=0
 R['status']='CURRENT_UNIT_COMPILER_BLOCKERS_CONFIRMED';s.save();assert tree.active()==1

def finish():
 assert not R['process_active'];R['owned_processes_before_cleanup']=s.owned_processes();s.quiesce();assert not R['owned_processes_before_cleanup'];assert s.catalog(I['target'],'current-after')==R['current_source_catalog'];assert not subprocess.check_output(['git','diff','--name-only'],cwd=s.SOURCE,text=True).strip()
 missing=[];changed=[]
 for name,item in R['original_objects'].items():
  obj=s.ROOT/name
  if not obj.is_file():missing.append(name)
  elif sha(obj)!=item['sha256']:changed.append(name)
 R['cache_object_observation']={'input_count':len(R['original_objects']),'present':len(R['original_objects'])-len(missing),'missing_after_selected_failed_compile':missing,'changed_payloads':changed};allowed={v['target'].replace('\\','/') for v in R.get('selected_commands',{}).values()};assert all(x.replace('\\','/').removeprefix('project-build/') in allowed for x in missing+changed)
 for name,h in R['node_binaries_before'].items():assert sha(s.BUILD/'bin'/(name+'.exe'))==h,name
 verify_dependencies()
 R['node_binaries_unchanged']=True;R['dependencies_unchanged_except_compiler_hash_cache']=True;R['current_source_unchanged']=True;R['unit_invoked']=False;R['node_invoked']=False;R['project_cache_saved']=False;R['cleanup_verified']=True;R['diagnostic_complete']=R['status'] in ['CURRENT_CONFIGURE_BLOCKER_CAPTURED','CURRENT_UNIT_COMPILER_BLOCKERS_CONFIRMED'];s.save();assert R['diagnostic_complete'],R['status']
try:{'configure':configure,'plans':plans,'compile':compile_selected,'finish':finish}[sys.argv[1]]()
except BaseException as e:R.setdefault('prerequisite_failures',[]).append({'stage':sys.argv[1],'type':type(e).__name__,'error':str(e)});s.save();raise
finally:s.save()
