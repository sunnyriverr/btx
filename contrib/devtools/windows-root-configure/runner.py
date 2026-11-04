from pathlib import Path
import os,sys,json,subprocess,hashlib,datetime,time,urllib.request,shutil
import checkpoint
import re
P=Path(__file__).resolve().parent
BASE='1b404ed8e52eae249ac73036007ba5a382b0d3ba'
VCPKG_COMMIT='afa249f12f52ed8a3b919f195495ba8b330288d1'
OPENSSL_SHA='967311f84955316969bdb1d8d4b983718ef42338639c621ec4c34fddef355e99'
ROOT=Path(os.environ['BTX_NATIVE_ROOT']);SOURCE=Path(os.environ['GITHUB_WORKSPACE'])/'btx'
E=ROOT/'evidence';E.mkdir(parents=True,exist_ok=True);STATE=E/'result.json'
result=json.loads(STATE.read_text())if STATE.exists()else{'base':BASE,'scope':'Native Windows project build/unit continuation on ecd plus the published Obs01 PID repair','status':'IN_PROGRESS','commands':[],'stages':{},'product_fixes':[404],'accepted_base':'ecd9310a8b35dbf1260d1a64e0ff39bb50e7a629','whole_node_build_run':False,'unit_test_execution':False,'PR397_in_upstream':True,'compiler_env':{k:os.environ.get(k)for k in ['VCToolsVersion','WindowsSDKVersion','ImageVersion','PROCESSOR_ARCHITECTURE']}}
def sha(p):return checkpoint.digest(p)
def save():
 result['updated_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat();STATE.write_text(json.dumps(result,indent=2)+'\n')
def run(label,command,cwd=ROOT,timeout=1800):
 log=E/(label+'.log');start=time.monotonic();timed_out=False;result['active_command']=label;save()
 with log.open('wb')as out:
  proc=subprocess.Popen(command,cwd=cwd,stdout=out,stderr=subprocess.STDOUT);result['build_process_active']=True;save()
  while proc.poll()is None:
   if time.monotonic()-start>timeout:
    cleanup=subprocess.run(['taskkill','/PID',str(proc.pid),'/T','/F'],capture_output=True);result['cleanup_confirmed']=cleanup.returncode==0
    (E/(label+'-timeout-cleanup.log')).write_bytes(cleanup.stdout+cleanup.stderr)
    proc.wait(timeout=30);timed_out=True;break
   if label in ['modelnet-build','daemon-build','default-all-build','unit-run']:
    resources=host_resources();elapsed=int(time.monotonic()-start)
    if resources['disk_free_bytes']<2*1024**3 or resources['available_ram_bytes']<1024**3:
     cleanup=subprocess.run(['taskkill','/PID',str(proc.pid),'/T','/F'],capture_output=True);result['cleanup_confirmed']=cleanup.returncode==0;(E/(label+'-disk-stop.log')).write_bytes(cleanup.stdout+cleanup.stderr);proc.wait(timeout=30);result['resource_stop']='Hosted disk below2GiB or available RAM below1GiB';break
    if elapsed//30>result.setdefault('last_progress_buckets',{}).get(label,-1):
     result['last_progress_buckets'][label]=elapsed//30;result.setdefault('build_resource_samples',[]).append({'stage':label,'seconds':elapsed,**resources});save();print(label+' elapsed',elapsed,'seconds; free disk',resources['disk_free_bytes'],'available RAM',resources['available_ram_bytes'],flush=True)
   time.sleep(2)
 result['commands'].append({'label':label,'command':command,'cwd':str(cwd),'exit':proc.returncode,'seconds':round(time.monotonic()-start,2),'timed_out':timed_out,'log_sha256':sha(log)});save();print(label,proc.returncode,log.read_text(errors='replace')[-6500:],flush=True)
 result['build_process_active']=False;save()
 if timed_out:raise TimeoutError(label+' timed out; owned process tree terminated and log retained')
 result['last_completed_command']=label;result['active_command']=None;save();return proc.returncode
def need(label,command,cwd=ROOT,timeout=1800):
 if run(label,command,cwd,timeout):raise RuntimeError(label+' failed; see original log')
def source_identity(label):
 head=subprocess.check_output(['git','-C',str(SOURCE),'rev-parse','HEAD']).decode().strip()
 if head!=BASE:raise RuntimeError('wrong source HEAD')
 tree=subprocess.check_output(['git','-C',str(SOURCE),'ls-tree','-rz','--full-tree',BASE]);entries={}
 for record in tree.split(b'\0'):
  if not record:continue
  meta,name=record.split(b'\t',1);mode,kind,oid=meta.decode().split()
  if kind!='blob':raise RuntimeError('unexpected gitlink')
  name=name.decode();path=SOURCE/name
  if mode=='120000':
   expected=subprocess.check_output(['git','-C',str(SOURCE),'cat-file','blob',oid])
   if path.is_symlink():
    data=os.readlink(path).replace('\\','/').encode()
    if data!=expected:raise RuntimeError('symlink target differs: '+name)
    entries[name]={'git_mode':mode,'git_blob':oid,'checkout_kind':'symlink','target':data.decode(),'resolved_sha256':sha(path)if path.is_file()else None}
   else:
    data=path.read_bytes()
    if data!=expected:raise RuntimeError('symlink placeholder differs: '+name)
    entries[name]={'git_mode':mode,'git_blob':oid,'checkout_kind':'link_placeholder','target':data.decode(),'working_sha256':sha(path)}
   continue
  if path.is_symlink():raise RuntimeError('unexpected symlink for regular Git blob: '+name)
  data=path.read_bytes();raw=hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()
  if raw!=oid:raise RuntimeError('working bytes differ: '+name)
  entries[name]={'git_mode':mode,'git_blob':oid,'working_sha256':hashlib.sha256(data).hexdigest()}
 target=E/(label+'-source.json');target.write_text(json.dumps({'head':head,'files':entries},indent=2)+'\n');result[label+'_source_sha256']=sha(target);result[label+'_tracked_files']=len(entries)
def metadata():
 source_identity('before')
 for label,cmd in [('cmake-version',['cmake','--version']),('ninja-version',['ninja','--version']),('clang-version',['clang-cl','--version'])]:need(label,cmd)
 run('cl-version',['cl','/Bv']);result['resolved_tools']={x:shutil.which(x)for x in ['cl','clang-cl','cmake','ninja','perl','nasm','nmake','dumpbin']}
 if any(not v for v in result['resolved_tools'].values()):raise RuntimeError('required native setup tool missing')
def openssl():
 metadata();prefix=ROOT/'openssl-3.5.4-static';receipt=prefix/'btx-build-provenance.json'
 if not receipt.exists():raise RuntimeError('Required verified OpenSSL cache missing; no speculative dependency rebuild')
 prior=json.loads(receipt.read_text());expected=json.loads((P/'dependency-identity.json').read_text())
 if prior['source_sha256']!=OPENSSL_SHA or prior['toolset']!=os.environ.get('VCToolsVersion'):raise RuntimeError('cached OpenSSL source/toolset mismatch')
 for f,h in expected['openssl_files'].items():
  if sha(prefix/f)!=h or prior['files'][f]!=h:raise RuntimeError('cached OpenSSL identity mismatch: '+f)
 if sha(prefix/'btx-Makefile.txt')!=prior['makefile_sha256']:raise RuntimeError('cached OpenSSL Makefile mismatch')
 shutil.copyfile(prefix/'btx-Makefile.txt',E/'openssl-Makefile.txt')
 need('openssl-version',[str(prefix/'bin/openssl.exe'),'version','-a'])
 result.update(openssl_cache_reused=True,openssl_files=expected['openssl_files'],openssl_source_sha256=OPENSSL_SHA,openssl_prefix=str(prefix),dependency_native_smoke_reused_from=expected['prior_native_run'],dependency_smoke_rerun=False)

def vcpkg():
 tool=ROOT/'vcpkg'
 if not(tool/'.git').exists():need('vcpkg-clone',['git','clone','--no-checkout','https://github.com/microsoft/vcpkg.git',str(tool)],timeout=240)
 need('vcpkg-checkout',['git','-C',str(tool),'checkout','--detach',VCPKG_COMMIT],timeout=120);head=subprocess.check_output(['git','-C',str(tool),'rev-parse','HEAD']).decode().strip()
 if head!=VCPKG_COMMIT:raise RuntimeError('vcpkg source pin mismatch')
 need('vcpkg-bootstrap',['cmd','/c',str(tool/'bootstrap-vcpkg.bat'),'-disableMetrics'],timeout=240);need('vcpkg-version',[str(tool/'vcpkg.exe'),'version']);result['vcpkg_commit']=head;result['vcpkg_executable_sha256']=sha(tool/'vcpkg.exe')
 promisor=subprocess.run(['git','-C',str(tool),'config','--get','remote.origin.promisor'],capture_output=True,text=True)
 result['vcpkg_promisor_remote']=promisor.stdout.strip()
 if promisor.stdout.strip().lower()=='true':raise RuntimeError('vcpkg still has partial-clone lazy fetching')
 for oid in ['8ed2f86ee404263f5aa1f72f8f4f13ee44262b81','937a2198387cb5c913e4feea170652651dd756ba']:
  need('vcpkg-historical-blob-'+oid[:8],['git','-C',str(tool),'cat-file','-e',oid],timeout=30)
def configure_args():
 prefix=ROOT/'openssl-3.5.4-static'
 return ['cmake','--debug-find-pkg=OpenSSL','--preset','windows-clangcl-static','-S',str(SOURCE),'-B',str(ROOT/'project-build'),'-DBUILD_TESTS=ON','-DVCPKG_MANIFEST_NO_DEFAULT_FEATURES=ON','-DVCPKG_MANIFEST_FEATURES=wallet;tests;zeromq','-DVCPKG_INSTALLED_DIR='+str(ROOT/'vcpkg-installed'),'-DOPENSSL_ROOT_DIR='+str(prefix),'-DOPENSSL_USE_STATIC_LIBS=ON','-DOPENSSL_MSVC_STATIC_RT=ON','-DOPENSSL_INCLUDE_DIR='+str(prefix/'include'),'-DOPENSSL_SSL_LIBRARY='+str(prefix/'lib/libssl.lib'),'-DOPENSSL_CRYPTO_LIBRARY='+str(prefix/'lib/libcrypto.lib'),'-DCMAKE_EXPORT_COMPILE_COMMANDS=ON']
def profile_identity():
 tools={name:{'path':shutil.which(name),'sha256':sha(Path(shutil.which(name)))}for name in ['clang-cl','cl','cmake','ninja']}
 return {'source':BASE,'tree':json.loads((P/'integration-source.json').read_text())['tree'],'tools':tools,'configure_args':configure_args(),'environment':{k:os.environ.get(k)for k in ['ImageVersion','VCToolsVersion','WindowsSDKVersion','INCLUDE','LIB','LIBPATH','CL','_CL_']},'controls':{f:sha(P/f)for f in ['runner.py','checkpoint.py','checkpoint-selftest.py','dependency-identity.json','integration-source.json','LICENSE.openssl.txt']},'openssl_files':json.loads((P/'dependency-identity.json').read_text())['openssl_files']}
def profile():
 need('checkpoint-selftest',[sys.executable,str(P/'checkpoint-selftest.py')],ROOT,60)
 identity=profile_identity();key=hashlib.sha256(json.dumps(identity,sort_keys=True).encode()).hexdigest();result['checkpoint_profile']=identity;result['checkpoint_key']=key;save()
 with open(os.environ['GITHUB_OUTPUT'],'a',encoding='utf-8')as out:out.write('key='+key+'\n')

def configure():
 build=ROOT/'project-build';os.environ.update(VCPKG_ROOT=str(ROOT/'vcpkg'),VCPKG_DISABLE_METRICS='1',VCPKG_MAX_CONCURRENCY='2',VCPKG_BINARY_SOURCES='clear;files,'+str(ROOT/'binary-cache')+',readwrite');(ROOT/'binary-cache').mkdir(exist_ok=True)
 identity=profile_identity()
 if identity!=result['checkpoint_profile']:raise RuntimeError('Native profile changed between cache key and build')
 before=json.loads((E/'before-source.json').read_text());result['checkpoint_restore']=checkpoint.restore(ROOT,SOURCE,identity,before);save()
 code=run('root-configure',configure_args(),SOURCE,1800)
 for f in ['CMakeCache.txt','CMakeFiles/CMakeConfigureLog.yaml','vcpkg-manifest-install.log','compile_commands.json']:
  if(build/f).exists():shutil.copyfile(build/f,E/Path(f).name)
 result['configure_exit']=code
 if code:result.update(status='BLOCKED_CONFIGURE',first_failed_stage='actual_root_configure');return
 need('generated-targets',['ninja','-C',str(build),'-t','targets','all']);targets=(E/'generated-targets.log').read_text(errors='replace')
 for expected in ['lib/bitcoin_modelnet.lib:','bin/btxd.exe:','bin/test_btx.exe:']:
  if expected not in targets:raise RuntimeError('Real generated target absent: '+expected)
 for name,target in [('modelnet','lib/bitcoin_modelnet.lib'),('daemon','bin/btxd.exe'),('unit','bin/test_btx.exe')]:need(name+'-dependencies',['ninja','-C',str(build),'-t','query',target])
 # Retain authoritative generated rules without guessing Windows path spelling.
 # Dependency queries above prove the real targets exist; metadata needs no parser.
 rule_files={}
 for relative in ['build.ninja','CMakeFiles/rules.ninja']:
  path=build/relative
  if not path.is_file():raise RuntimeError('Generated rule file absent: '+relative)
  name='generated-'+Path(relative).name
  shutil.copyfile(path,E/name);rule_files[relative]={'evidence':name,'sha256':sha(E/name)}
 (E/'generated-link-rules.json').write_text(json.dumps({'format':'raw-ninja-rules-v2','files':rule_files,'targets':{'modelnet':'lib/bitcoin_modelnet.lib','daemon':'bin/btxd.exe','unit':'bin/test_btx.exe'}},indent=2)+'\n')
 result['gates']={};budget_start=time.monotonic()
 for label,target in [('modelnet-build','bitcoin_modelnet'),('daemon-build','btxd'),('default-all-build','all')]:
  remaining=2400-(time.monotonic()-budget_start)
  if remaining<5:result.update(status='BUILD_BUDGET',first_failed_stage=label);return
  resources=host_resources();result.setdefault('before_targets',{})[label]=resources
  if resources['disk_free_bytes']<6*1024**3 or resources['available_ram_bytes']<4*1024**3:result.update(status='BLOCKED_RESOURCE',first_failed_stage=label);return
  if label=='daemon-build':result['whole_node_build_run']=True
  if label=='default-all-build':result['default_build_run']=True
  save();code=run(label,['cmake','--build',str(build),'--target',target,'--verbose','--','-j','4','-k','1'],SOURCE,remaining);result['gates'][label]={'exit':code,'target':target};save()
  if result.get('resource_stop'):result.update(status='BLOCKED_RESOURCE',first_failed_stage=label);return
  if code:result.update(status='BLOCKED_BUILD',first_failed_stage=label);return
  if label=='daemon-build':
   exe=build/'bin/btxd.exe'
   if not exe.exists():raise RuntimeError('Daemon target succeeded without executable')
   result['daemon_sha256']=sha(exe);need('daemon-binary-imports',['dumpbin','/dependents',str(exe)])
 exe=build/'bin/test_btx.exe'
 if not exe.exists():raise RuntimeError('Default build succeeded without test_btx')
 result['unit_sha256']=sha(exe);need('unit-binary-imports',['dumpbin','/dependents',str(exe)]);runtime=ROOT/'unit-runtime';runtime.mkdir(exist_ok=True);result['unit_invocation_attempted']=True;save()
 code=run('unit-run',[str(exe),'--log_level=test_suite','--report_level=detailed','--catch_system_error=no'],runtime,600);result['unit_exit']=code
 if result.get('resource_stop'):result.update(status='BLOCKED_RESOURCE',first_failed_stage='unit-run');return
 text=(E/'unit-run.log').read_text(errors='replace');match=re.search(r'Running (\d+) test cases?',text);result['unit_test_execution']=bool(match and int(match.group(1))>0);result['unit_cases_announced']=int(match.group(1))if match else None
 result['status']='INTEGRATED_BUILD_UNITS_PASS'if code==0 and result['unit_test_execution']and 'No errors detected'in text else'UNIT_FAILURE'if code and result['unit_test_execution']else'UNIT_START_FAILURE'if code else'UNIT_RESULT_UNCLEAR'
 if result['status']!='INTEGRATED_BUILD_UNITS_PASS':result['first_failed_stage']='unit-run'

def retain():
 source_identity('retained');catalog=json.loads((E/'retained-source.json').read_text());initial=json.loads((E/'before-source.json').read_text())
 if catalog!=initial:raise RuntimeError('Source changed before retention')
 if result.get('build_process_active')or not result.get('cleanup_confirmed',True):raise RuntimeError('Build process quiescence not confirmed; refusing checkpoint')
 build=ROOT/'project-build';bundle=ROOT/'library-bundle';bundle.mkdir(exist_ok=True);files=[]
 def copy(path,relative,kind):
  if not path.exists()or not path.is_file():return
  target=bundle/relative;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(path,target);files.append({'path':relative,'source_path':str(path),'kind':kind,'bytes':target.stat().st_size,'sha256':sha(target)})
 for folder in ['lib','src']:
  for path in(build/folder).rglob('*.lib'):copy(path,'project/'+path.relative_to(build).as_posix(),'project_library')
 for name in ['btxd.exe','test_btx.exe','btx-modeld.exe','btx-open.exe']:copy(build/'bin'/name,'binaries/'+name,'linked_binary_present')
 for folder in ['lib','bin']:
  for pattern in ['*.lib','*.dll']:
   for path in (ROOT/'vcpkg-installed/x64-windows-static'/folder).rglob(pattern):copy(path,'vcpkg/'+path.relative_to(ROOT/'vcpkg-installed/x64-windows-static').as_posix(),'thirdparty_library_or_runtime')
 for path in (ROOT/'openssl-3.5.4-static/lib').glob('*.lib'):copy(path,'openssl/lib/'+path.name,'openssl_static')
 # Matching SDK/compiler inputs are identities, not redistributed toolchain binaries.
 externals=[]
 def external(path,kind):
  if path.exists()and path.is_file():externals.append({'path':str(path),'kind':kind,'sha256':sha(path),'bytes':path.stat().st_size})
 llvm=Path(shutil.which('clang-cl')).parents[1]
 for path in(llvm/'lib').rglob('clang_rt.builtins-x86_64.lib'):external(path,'compiler_builtins')
 vc=Path(os.environ['VCToolsInstallDir']);external(vc/'lib/x64/libomp.lib','openmp_import')
 redist=os.environ.get('VCToolsRedistDir')
 if redist:
  for path in Path(redist).rglob('libomp*.dll'):
   if'x64'in str(path):external(path,'openmp_runtime_candidate')
 for path in(llvm/'bin').glob('libomp*.dll'):external(path,'openmp_runtime_candidate')
 copy(SOURCE/'COPYING','licenses/project-COPYING','license');copy(P/'LICENSE.openssl.txt','licenses/OpenSSL-LICENSE.txt','license')
 for path in(ROOT/'vcpkg-installed/x64-windows-static/share').rglob('copyright'):copy(path,'licenses/vcpkg/'+path.relative_to(ROOT/'vcpkg-installed/x64-windows-static/share').as_posix(),'license')
 for folder in ['src','include']:
  for suffix in ['*.h','*.hpp']:
   for path in(build/folder).rglob(suffix):copy(path,'generated/'+path.relative_to(build).as_posix(),'generated_header')
 for name in ['result.json','before-source.json','CMakeCache.txt','generated-link-rules.json','generated-build.ninja','generated-rules.ninja','modelnet-dependencies.log','daemon-dependencies.log','unit-dependencies.log']:
  if(E/name).exists():copy(E/name,'provenance/'+name,'provenance')
 gates=result.get('gates',{});modelnet=gates.get('modelnet-build',{}).get('exit')==0
 manifest={'source':BASE,'accepted_base':result['accepted_base'],'patches':json.loads((P/'integration-source.json').read_text())['patches'],'profile':result.get('checkpoint_profile'),'gates':gates,'status':result['status'],'modelnet_target_passed':modelnet,'has_modelnet_archive':any(x['path']=='project/lib/bitcoin_modelnet.lib'for x in files),'dependency_runtime_closure_independently_qualified':False,'consumer_must_verify_source_abi_and_transitive_compatibility':True,'external_toolchain_inputs':externals,'files':files}
 (bundle/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n');(E/'library-bundle-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n');result['library_files_retained']=len(files);result['modelnet_archive_retained']=manifest['has_modelnet_archive'];save()
 if result.get('checkpoint_profile')and(build/'CMakeCache.txt').exists():
  result['checkpoint_snapshot']=checkpoint.capture(ROOT,SOURCE,result['checkpoint_profile'],catalog,{'status':result['status'],'gates':gates});save()
  with open(os.environ['GITHUB_OUTPUT'],'a',encoding='utf-8')as out:out.write('checkpoint_valid=true\n')


def host_resources():
 import ctypes
 class MemoryStatus(ctypes.Structure):
  _fields_=[('length',ctypes.c_uint32),('load',ctypes.c_uint32)]+[(x,ctypes.c_uint64) for x in ['total_phys','avail_phys','total_page','avail_page','total_virtual','avail_virtual','avail_extended']]
 memory=MemoryStatus();memory.length=ctypes.sizeof(memory);ok=ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(memory))
 return {'disk_free_bytes':shutil.disk_usage(ROOT).free,'cpus':os.cpu_count(),'total_ram_bytes':memory.total_phys if ok else None,'available_ram_bytes':memory.avail_phys if ok else None}

stage=sys.argv[1]
try:
 if stage=='retain':
  result['stages'][stage]='RUNNING';save();retain();result['stages'][stage]='COMPLETE'
 elif result['status'].startswith('BLOCKED')or result['status']=='SETUP_ERROR':print('Prior failure retained; skipping',stage)
 else:
  result['stages'][stage]='RUNNING';save();{'openssl':openssl,'vcpkg':vcpkg,'profile':profile,'configure':configure}[stage]();result['stages'][stage]='COMPLETE'
except Exception as ex:
 label=result.get('active_command') or result.get('last_completed_command') or stage
 status=('UNIT_TIMEOUT'if label=='unit-run' else 'BUILD_TIMEOUT'if label in ['modelnet-build','daemon-build','default-all-build']else 'COMMAND_TIMEOUT') if isinstance(ex,TimeoutError) else ('POST_LINK_INSPECTION_ERROR' if label in ['daemon-binary-imports','unit-binary-imports'] and result.get('daemon_sha256') else 'SETUP_ERROR')
 if stage=='retain':result['retention_error']=type(ex).__name__+': '+str(ex)
 else:result.update(status=status,first_failed_stage=label,error=type(ex).__name__+': '+str(ex))
 result['stages'][stage]='ERROR';print('Stage error',stage,type(ex).__name__,str(ex),flush=True)
finally:
 try:
  source_identity('after');result['tracked_source_unchanged']=json.loads((E/'before-source.json').read_text())==json.loads((E/'after-source.json').read_text())
  if not result['tracked_source_unchanged']:raise RuntimeError('tracked source identity changed')
 except Exception as ex:result['source_verification_error']=str(ex);result['status']='SETUP_ERROR'
 if result.get('unit_invocation_attempted')and(E/'unit-run.log').exists():
  text=(E/'unit-run.log').read_text(errors='replace');match=re.search(r'Running (\d+) test cases?',text);result['unit_test_execution']=bool(match and int(match.group(1))>0);result['unit_cases_announced']=int(match.group(1))if match else None
 save();print('Recorded diagnostic status:',result['status'],flush=True)
raise SystemExit(result['status']=='SETUP_ERROR')
