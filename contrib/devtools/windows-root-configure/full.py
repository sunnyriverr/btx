# Normal maintained graph/target, exact preserved cache; no source changes.
from pathlib import Path
import json,os,sys,subprocess,hashlib,re,shutil,base64,stat
import checkpoint
import integration_support as s
P=Path(__file__).resolve().parent;I=json.loads((P/'maintained-inputs.json').read_text());ROOT,SOURCE,BUILD,E=s.ROOT,s.SOURCE,s.BUILD,s.E
s.STATE=E/'maintained.json';s.R=json.loads(s.STATE.read_text())if s.STATE.exists()else{'status':'SETUP','source':I['source'],'scope':I['scope'],'commands':[],'process_active':False,'unit_built':False,'unit_invoked':False};R=s.R;sha=checkpoint.digest

def diff(a,b,p=''):
 out={}
 for k in sorted(set(a)|set(b)):
  x,y=a.get(k),b.get(k)
  if isinstance(x,dict)and isinstance(y,dict):out.update(diff(x,y,p+k+'.'))
  elif x!=y:out[p+k]=[x,y]
 return out

def settings():
 vals={}
 for line in(BUILD/'CMakeCache.txt').read_text().splitlines():
  if line and not line.startswith(('#','//'))and '='in line:
   k,v=line.split('=',1);vals[k]=v
 for k in ['WITH_MODELNET:BOOL','BUILD_TESTS:BOOL','ENABLE_WALLET:BOOL','WITH_ZMQ:BOOL']:assert vals.get(k)=='ON',(k,vals.get(k))
 assert vals['CMAKE_HOME_DIRECTORY:INTERNAL'].replace('\\','/')==str(SOURCE).replace('\\','/')
 return vals

def prepare():
 setup=json.loads((E/'result.json').read_text());assert setup['stages']['profile']=='COMPLETE';marker=BUILD/'btx-checkpoint.json';assert sha(marker)==I['checkpoint_sha256'];cp=json.loads(marker.read_text());assert cp['profile']['source']==I['source']
 delta=diff(cp['profile']['actual_current_profile'],setup['profile']);allowed=json.loads((P/'profile-transition.json').read_text())['allowed_differences'];assert delta in [{},allowed,{k:list(reversed(v))for k,v in allowed.items()}],delta
 assert subprocess.check_output(['ninja','--version'],text=True).strip()=='1.13.2'
 s.need('source-parent-fetch',['git','fetch','--no-tags','--depth=3','https://github.com/sunnyriverr/btx.git',I['public_parent']],180)
 bundle=E/'maintained-source.bundle';bundle.write_bytes(base64.b64decode((P/'maintained-source.bundle.base64').read_text()));assert sha(bundle)==I['bundle_sha256']
 s.need('source-bundle-verify',['git','bundle','verify',str(bundle)],60);s.need('source-bundle-fetch',['git','fetch',str(bundle),I['bundle_ref']],60)
 s.need('source-checkout',['git','checkout','--detach',I['source']],60);assert subprocess.check_output(['git','rev-parse','HEAD^{tree}'],cwd=SOURCE,text=True).strip()==I['tree']
 cat=s.catalog(I['source'],'cached');assert cat==cp['source_catalog'];R['restore']=checkpoint.restore(ROOT,SOURCE,cp['profile'],cat);assert R['restore']['restored'];R['source_catalog']=cat;R['actual_profile']=setup['profile'];R['profile_transition']=delta
 R['original_config']={n:sha(BUILD/n)for n in ['build.ninja','CMakeFiles/rules.ninja','CMakeCache.txt','compile_commands.json']};assert R['original_config']==cp['profile']['configuration'];R['original_objects']={k:v for k,v in cp['files'].items()if k.endswith('.obj')};assert len(R['original_objects'])==I['objects'];R['settings_before']=settings();R['initial_resources']=s.resources();assert R['initial_resources']['disk_free']>8*1024**3 and R['initial_resources']['available_ram']>3*1024**3
 R['dependencies_before']={k:v for k,v in cp['files'].items()if k.replace('\\','/').startswith('vcpkg-installed/')};R['status']='RESTORED_VERIFIED';s.save()

def configure():
 assert R['status']=='RESTORED_VERIFIED';args=R['actual_profile']['args'];assert args[0]=='cmake'and '--preset'in args and '-DWITH_MODELNET=ON'in args and '-DBUILD_TESTS=ON'in args
 old={x['output']:x for x in json.loads((BUILD/'compile_commands.json').read_text())};os.environ.update(VCPKG_ROOT=str(ROOT/'vcpkg'),VCPKG_DISABLE_METRICS='1',VCPKG_MAX_CONCURRENCY='2',VCPKG_BINARY_SOURCES='clear;files,'+str(ROOT/'binary-cache')+',readwrite')
 book=ROOT/'vcpkg-installed/vcpkg/compiler-file-hash-cache.json';shutil.copyfile(book,E/'compiler-file-hash-cache-before.json');R['status']='NORMAL_CONFIGURING';s.save();s.need('normal-cmake-regenerate',args,900);R['settings_after']=settings();R['settings_delta']=diff(R['settings_before'],R['settings_after']);R['configuration']={n:sha(BUILD/n)for n in R['original_config']};shutil.copyfile(book,E/'compiler-file-hash-cache-after.json')
 new={x['output']:x for x in json.loads((BUILD/'compile_commands.json').read_text())};sdk=[x for x in new.values()if x['file'].replace('\\','/').endswith('/src/test/util/sdk_process.cpp')and '/test_btx.dir/'in x['output'].replace('\\','/')];assert len(sdk)==1;R['sdk_helper_registration']=sdk
 added=sorted(new.keys()-old.keys());removed=sorted(old.keys()-new.keys());changed=[k for k in old.keys()&new.keys()if old[k]!=new[k]];assert not removed;assert all(new[k]['file'].replace('\\','/').endswith('/src/test/util/sdk_process.cpp')for k in added)
 def normal(cmd):return re.sub(r'(?<!\S)(-I|-imsvc|/I)(\s*)("[^"\r\n]*"|[^\s]+)',lambda m:m.group(1)+m.group(2)+m.group(3).replace('\\','/'),cmd)
 unexpected=[{'before':old[k],'after':new[k]}for k in changed if {**old[k],'command':normal(old[k]['command'])}!={**new[k],'command':normal(new[k]['command'])}]
 (E/'unexpected-command-delta.json').write_text(json.dumps({'count':len(unexpected),'first20':unexpected[:20]},indent=2)+'\n');R['unexpected_command_delta_count']=len(unexpected);s.save();assert not unexpected,'Unexpected configure command delta; diagnostic retained'
 R['command_delta']={'before':len(old),'after':len(new),'added':len(added),'removed':len(removed),'changed':len(changed),'all_old_changes_include_separators_only':True}
 for k,v in R['original_objects'].items():assert sha(ROOT/k)==v['sha256'],k
 for k,v in R['dependencies_before'].items():
  if k.replace('\\','/').endswith('/compiler-file-hash-cache.json'):continue
  assert sha(ROOT/k)==v['sha256'],k
 R['dependencies_after']={str(x.relative_to(ROOT)):sha(x)for x in(ROOT/'vcpkg-installed').rglob('*')if x.is_file()and not x.is_symlink()};assert set(R['dependencies_after'])==set(R['dependencies_before'])
 for n,h in R['actual_profile']['openssl_files'].items():assert sha(ROOT/'openssl-3.5.4-static'/n)==h
 assert s.catalog(I['source'],'configured')==R['source_catalog'];R['profile']={'source':I['source'],'actual_current_profile':R['actual_profile'],'input_checkpoint_sha256':I['checkpoint_sha256'],'input_cache_key':I['key'],'configuration':R['configuration'],'normal_cmake_regeneration':True,'full_maintained_target':True,'scope':I['scope'],'controller_sha256':sha(P/'full.py')};R['configuration_validated']=True;R['status']='NORMAL_CONFIGURED';s.save()

def build():
 assert R['status']=='NORMAL_CONFIGURED' and R.get('configuration_validated');os.environ.update(VCPKG_ROOT=str(ROOT/'vcpkg'),VCPKG_DISABLE_METRICS='1',VCPKG_MAX_CONCURRENCY='2',VCPKG_BINARY_SOURCES='clear;files,'+str(ROOT/'binary-cache')+',readwrite');targets=['btxd','btx-cli','btx-tx','btx-util','btx-open','btx-modeld','test_btx'];R['maintained_targets']=targets
 s.need('normal-verify-globs',['cmake','-P',str(BUILD/'CMakeFiles/VerifyGlobs.cmake')],120,cwd=BUILD);assert 'GLOB mismatch!'not in(E/'normal-verify-globs.log').read_text();manifest=E/'observed-full-manifest.ninja';shutil.copyfile(BUILD/'build.ninja',manifest);assert sha(manifest)==R['configuration']['build.ninja'];s.need('full-unit-plan',['ninja','-C',str(BUILD),'-f',str(manifest),'-n','-d','explain']+targets,120)
 text=(E/'full-unit-plan.log').read_text(errors='replace');m=re.findall(r'^\[(\d+)/(\d+)\]',text,re.M);R['planned_steps']=int(m[-1][1])if m else 0;R['planned_command_invalidations']=text.count('ninja explain: command line changed for ');assert 0<R['planned_steps']<=I['max_build_steps'],R['planned_steps'];assert R['planned_command_invalidations']<=I['max_command_invalidations'],R['planned_command_invalidations'];assert 'stored deps info out of date'not in text;assert 'Re-running CMake'not in text and 'Re-checking globbed'not in text
 R['status']='MAINTAINED_BUILDING';R['compilation_invoked']=True;s.save();code=s.run('candidate-unit-build',['cmake','--build',str(BUILD),'--target']+targets+['--verbose','--parallel','4','--','-k','1'],I['build_budget_seconds']);R['unit_build_exit']=code
 if code:R['status']='MAINTAINED_BUILD_FAILURE';s.save();raise RuntimeError('Actual maintained compiler/link blocker; no unit runtime inferred')
 names=['btxd','btx-cli','btx-tx','btx-util','btx-open','btx-modeld','test_btx'];R['binaries']={n:sha(BUILD/'bin'/(n+'.exe'))for n in names};R['unit_binary_sha256']=R['binaries']['test_btx'];R['unit_built']=True;R['build_info']=(BUILD/'src/bitcoin-build-info.h').read_text();assert I['source'][:7]in R['build_info']and re.search(r'BUILD_GIT_DIRTY\s+0',R['build_info']);exe=BUILD/'bin/test_btx.exe';s.need('unit-imports',['dumpbin','/dependents',str(exe)],60);s.need('unit-inventory',[str(exe),'--list_content'],180);s.need('node-version',[str(BUILD/'bin/btxd.exe'),'-version'],30);R['status']='MAINTAINED_LINKED';s.save()

def run():
 assert R['status']=='MAINTAINED_LINKED';assert not s.owned_processes();exe=BUILD/'bin/test_btx.exe';assert sha(exe)==R['unit_binary_sha256'];data=Path('D:/bu'+os.environ['GITHUB_RUN_ID']);assert not data.exists();data.mkdir();R['unit_data']=str(data);temp=data/'tmp';temp.mkdir();R['prior_temp_environment']={k:os.environ.get(k) for k in ['TMP','TEMP']};R['unit_temp_environment']={'TMP':str(temp),'TEMP':str(temp)};os.environ.update(R['unit_temp_environment']);R['unit_invoked']=True;R['status']='MAINTAINED_UNIT_RUNNING';s.save()
 code=s.run('candidate-unit-run',[str(exe),'--log_level=test_suite','--report_level=detailed','--catch_system_errors=yes','--','-testdatadir='+str(data)],I['unit_budget_seconds']);R['unit_exit']=code;text=(E/'candidate-unit-run.log').read_text(errors='replace');m=re.search(r'Running (\d+) test cases?',text);R['unit_cases_announced']=int(m.group(1))if m else 0;R['unit_case_count_is_not_completion']=True;assert sha(exe)==R['unit_binary_sha256'];completion=re.search(r'Test module "Bitcoin Core Test Suite" has passed with:\s+(\d+) test cases? out of (\d+) passed',text);R['unit_cases_completed']=int(completion.group(1))if completion else 0;R['status']='MAINTAINED_UNIT_PASS'if code==0 and R['unit_cases_announced']>0 and R['unit_cases_completed']==R['unit_cases_announced'] else'MAINTAINED_UNIT_FAILURE';s.save()
 if R['status']!='MAINTAINED_UNIT_PASS':raise RuntimeError('Full unit invocation failed; preserve detailed evidence')

def readonly_cleanup(function,filename,exc_info):
 data=Path(R['unit_data']);path=Path(filename);assert path.resolve().is_relative_to(data.resolve())
 error=exc_info[1]
 if not isinstance(error,PermissionError)or path.stat().st_mode&stat.S_IWRITE:raise error
 R.setdefault('readonly_cleanup_paths',[]).append(str(path));os.chmod(path,stat.S_IREAD|stat.S_IWRITE);function(filename)

def retain():
 assert not R['process_active']and R.get('cleanup_confirmed',True);assert R.get('configuration_validated'),'Unvalidated/failed configure cannot create a compatible successor cache';prior=s.owned_processes();R['owned_processes_before_retention']=prior;s.quiesce();assert not s.owned_processes()
 if prior:R['status']='OWNED_PROCESS_CLEANUP_REQUIRED'
 cat=s.catalog(I['source'],'retained');assert cat==R['source_catalog'];config=R.get('configuration',R['original_config']);assert all(sha(BUILD/n)==h for n,h in config.items()),'Unexpected graph/profile mutation'
 for k,h in R.get('dependencies_after',{}).items():assert sha(ROOT/k)==h,k
 for n,h in R['actual_profile']['openssl_files'].items():assert sha(ROOT/'openssl-3.5.4-static'/n)==h
 if R.get('unit_data'):
  data=Path(R['unit_data']);assert data.parent==Path('D:/')and data.name=='bu'+os.environ['GITHUB_RUN_ID'];R['runtime_cleanup_error']=None
  try:
   if data.exists():shutil.rmtree(data,onerror=readonly_cleanup)
  except OSError as e:R['runtime_cleanup_error']=str(e)
  R['runtime_data_removed']=not data.exists()
  if not R['runtime_data_removed']:R['status_before_cleanup_failure']=R['status'];R['status']='RUNTIME_CLEANUP_FAILURE'
 profile=R.get('profile',{'source':I['source'],'actual_current_profile':R['actual_profile'],'configuration':config,'scope':I['scope'],'input_checkpoint_sha256':I['checkpoint_sha256']});R['checkpoint_capture']=checkpoint.capture(ROOT,SOURCE,profile,cat,{'status':R['status'],'unit_build_exit':R.get('unit_build_exit'),'unit_built':R['unit_built'],'unit_invoked':R['unit_invoked'],'unit_exit':R.get('unit_exit')});shutil.copyfile(BUILD/'btx-checkpoint.json',E/'maintained-checkpoint.json');cp=json.loads((BUILD/'btx-checkpoint.json').read_text());R['objects_retained']=sum(k.endswith('.obj')for k in cp['files']);R['checkpoint_sha256']=sha(BUILD/'btx-checkpoint.json');R['checkpoint_key']=hashlib.sha256(json.dumps(profile,sort_keys=True).encode()).hexdigest();R['retention_verified']=True;s.save()
 with open(os.environ['GITHUB_OUTPUT'],'a')as f:f.write('checkpoint_valid=true\ncheckpoint_key='+R['checkpoint_key']+'\n')

def verdict():
 assert R['status']=='MAINTAINED_UNIT_PASS' and R.get('runtime_data_removed') and not R.get('owned_processes_before_retention') and R.get('configuration_validated') and R.get('retention_verified'),R['status']

stage=sys.argv[1];failed=False
try:{'prepare':prepare,'configure':configure,'build':build,'run':run,'retain':retain,'verdict':verdict}[stage]()
except BaseException as ex:
 failed=True;R.setdefault('failures',[]).append({'stage':stage,'type':type(ex).__name__,'error':str(ex)})
 if R['status']in ['MAINTAINED_BUILDING','MAINTAINED_UNIT_RUNNING']:R['status']+='_' + ('BUDGET_STOP'if 'stopped:'in str(ex)else'ERROR')
 print(type(ex).__name__,str(ex),flush=True)
finally:
 if stage=='run':
  for key,value in R.get('prior_temp_environment',{}).items():
   if value is None:os.environ.pop(key,None)
   else:os.environ[key]=value
 s.save();print(json.dumps({k:R.get(k)for k in ['status','planned_steps','unit_built','unit_invoked','unit_build_exit','unit_exit','failures']},indent=2),flush=True)
raise SystemExit(1 if failed else 0)
