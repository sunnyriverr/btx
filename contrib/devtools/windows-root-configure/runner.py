from pathlib import Path
import os,sys,json,subprocess,hashlib,datetime,time,urllib.request,shutil
import checkpoint
P=Path(__file__).resolve().parent
BASE='666673a3153225ba264c7870e0e82e354df86765'
VCPKG_COMMIT='afa249f12f52ed8a3b919f195495ba8b330288d1'
OPENSSL_SHA='967311f84955316969bdb1d8d4b983718ef42338639c621ec4c34fddef355e99'
ROOT=Path(os.environ['BTX_NATIVE_ROOT']);SOURCE=Path(os.environ['GITHUB_WORKSPACE'])/'btx'
E=ROOT/'evidence';E.mkdir(parents=True,exist_ok=True);STATE=E/'result.json'
result=json.loads(STATE.read_text())if STATE.exists()else{'base':BASE,'scope':'Actual stock native Windows btxd build/link; no test-source patch','status':'IN_PROGRESS','commands':[],'stages':{},'product_fixes':[],'whole_node_build_run':False,'unit_test_execution':False,'PR397_in_upstream':True,'compiler_env':{k:os.environ.get(k)for k in ['VCToolsVersion','WindowsSDKVersion','ImageVersion','PROCESSOR_ARCHITECTURE']}}
result.setdefault('job_started_epoch',time.time())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save():
 result['updated_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat();STATE.write_text(json.dumps(result,indent=2)+'\n')
def run(label,command,cwd=ROOT,timeout=1800):
 remaining=180*60-(time.time()-result['job_started_epoch'])
 if remaining<30:raise TimeoutError('Total job budget exhausted before '+label)
 timeout=min(timeout,int(remaining))
 log=E/(label+'.log');start=time.monotonic();timed_out=False;result['active_command']=label;save()
 with log.open('wb')as out:
  proc=subprocess.Popen(command,cwd=cwd,stdout=out,stderr=subprocess.STDOUT);result['process_active']=True;save()
  while proc.poll()is None:
   if time.monotonic()-start>timeout:
    cleanup=subprocess.run(['taskkill','/PID',str(proc.pid),'/T','/F'],capture_output=True)
    (E/(label+'-timeout-cleanup.log')).write_bytes(cleanup.stdout+cleanup.stderr);result['cleanup_confirmed']=cleanup.returncode==0
    proc.wait(timeout=30);timed_out=True;break
   if label in ['native-daemon-build','native-unit-build','native-unit-run']:
    resources=host_resources();elapsed=int(time.monotonic()-start)
    if resources['disk_free_bytes']<2*1024**3 or resources['available_ram_bytes']<1024**3:
     cleanup=subprocess.run(['taskkill','/PID',str(proc.pid),'/T','/F'],capture_output=True);(E/(label+'-disk-stop.log')).write_bytes(cleanup.stdout+cleanup.stderr);result['cleanup_confirmed']=cleanup.returncode==0;proc.wait(timeout=30);result['resource_stop']='Hosted disk below2GiB or available RAM below1GiB';break
    if elapsed//30>result.get('last_progress_bucket',-1):
     result['last_progress_bucket']=elapsed//30;result.setdefault('build_resource_samples',[]).append({'seconds':elapsed,**resources});save();print('Daemon build elapsed',elapsed,'seconds; free disk',resources['disk_free_bytes'],'available RAM',resources['available_ram_bytes'],flush=True)
   time.sleep(2)
 result['process_active']=False;result['active_command']=None
 result['commands'].append({'label':label,'command':command,'cwd':str(cwd),'exit':proc.returncode,'seconds':round(time.monotonic()-start,2),'timed_out':timed_out,'log_sha256':sha(log)});save();print(label,proc.returncode,log.read_text(errors='replace')[-6500:],flush=True)
 if result.get('resource_stop'):raise RuntimeError('Terminal disk stop')
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
 return ['cmake','--debug-find-pkg=OpenSSL','--preset','windows-clangcl-static','-S',str(SOURCE),'-B',str(ROOT/'project-build'),'-DBUILD_TESTS=ON','-DWITH_MODELNET=ON','-DVCPKG_MANIFEST_NO_DEFAULT_FEATURES=ON','-DVCPKG_MANIFEST_FEATURES=wallet;tests;zeromq','-DVCPKG_INSTALLED_DIR='+str(ROOT/'vcpkg-installed'),'-DOPENSSL_ROOT_DIR='+str(prefix),'-DOPENSSL_USE_STATIC_LIBS=ON','-DOPENSSL_MSVC_STATIC_RT=ON','-DOPENSSL_INCLUDE_DIR='+str(prefix/'include'),'-DOPENSSL_SSL_LIBRARY='+str(prefix/'lib/libssl.lib'),'-DOPENSSL_CRYPTO_LIBRARY='+str(prefix/'lib/libcrypto.lib'),'-DCMAKE_EXPORT_COMPILE_COMMANDS=ON']
def identity():
 return {'source':BASE,'tools':{n:{'path':shutil.which(n),'sha256':sha(Path(shutil.which(n)))} for n in ['clang-cl','cl','cmake','ninja']},'args':configure_args(),'environment':{k:os.environ.get(k) for k in ['ImageVersion','VCToolsVersion','WindowsSDKVersion','INCLUDE','LIB','LIBPATH','CL','_CL_']},'controls':{f:sha(P/f) for f in ['runner.py','checkpoint.py','checkpoint-selftest.py','dependency-identity.json']},'openssl_files':json.loads((P/'dependency-identity.json').read_text())['openssl_files']}
def profile():
 need('checkpoint-selftest',[sys.executable,str(P/'checkpoint-selftest.py')],ROOT,60)
 result['profile']=identity();result['checkpoint_key']=hashlib.sha256(json.dumps(result['profile'],sort_keys=True).encode()).hexdigest()
 with open(os.environ['GITHUB_OUTPUT'],'a',encoding='utf-8') as f:f.write('key='+result['checkpoint_key']+'\n')
def configure():
 if identity()!=result['profile']:raise RuntimeError('Profile changed before restore/configure')
 catalog=json.loads((E/'before-source.json').read_text());result['checkpoint_restore']=checkpoint.restore(ROOT,SOURCE,result['profile'],catalog);save()
 os.environ.update(VCPKG_ROOT=str(ROOT/'vcpkg'),VCPKG_DISABLE_METRICS='1',VCPKG_MAX_CONCURRENCY='2',VCPKG_BINARY_SOURCES='clear;files,'+str(ROOT/'binary-cache')+',readwrite')
 code=run('root-configure',configure_args(),SOURCE,1800)
 for f in ['CMakeCache.txt','CMakeFiles/CMakeConfigureLog.yaml','vcpkg-manifest-install.log','compile_commands.json','build.ninja','CMakeFiles/rules.ninja']:
  if (ROOT/'project-build'/f).exists():shutil.copyfile(ROOT/'project-build'/f,E/Path(f).name)
 if code:raise RuntimeError('Root configure failed')
 cache=(ROOT/'project-build/CMakeCache.txt').read_text()
 for flag in ['WITH_MODELNET:BOOL=ON','BUILD_TESTS:BOOL=ON','ENABLE_WALLET:BOOL=ON']:
  if flag not in cache:raise RuntimeError('Required profile absent: '+flag)
 result['status']='CONFIGURE_PASS'
def node():
 build=ROOT/'project-build';result['whole_node_build_run']=True;save()
 code=run('native-daemon-build',['cmake','--build',str(build),'--target','btxd','--verbose','--','-j','4','-k','1'],SOURCE,3600);result['node_exit']=code
 if code:result['status']='NODE_BUILD_FAILURE';raise RuntimeError('Node build failed; original compiler log retained')
 exe=build/'bin/btxd.exe';result['node_binary_sha256']=sha(exe);need('node-imports',['dumpbin','/dependents',str(exe)],SOURCE,60);need('node-version',[str(exe),'-version'],SOURCE,30);result['status']='NODE_BUILD_PASS'
def unitbuild():
 build=ROOT/'project-build';result['unit_build_attempted']=True;save()
 code=run('native-unit-build',['cmake','--build',str(build),'--target','test_btx','--verbose','--','-j','4','-k','1'],SOURCE,3600);result['unit_build_exit']=code
 if code:result['status']='UNIT_BUILD_FAILURE';raise RuntimeError('Unit build failed; no workarounds applied')
 exe=build/'bin/test_btx.exe';result['unit_binary_sha256']=sha(exe);need('unit-inventory',[str(exe),'--list_content'],SOURCE,60);result['status']='UNIT_BUILD_PASS'
def units():
 exe=ROOT/'project-build/bin/test_btx.exe'
 if sha(exe)!=result['unit_binary_sha256']:raise RuntimeError('Unit binary changed')
 result['unit_invocation_attempted']=True;save()
 # CWD is the exact source root: maintained relative test vectors/scripts remain available.
 code=run('native-unit-run',[str(exe),'--log_level=test_suite','--report_level=detailed','--catch_system_errors=yes'],SOURCE,3600);result['unit_exit']=code
 import re
 text=(E/'native-unit-run.log').read_text(errors='replace');m=re.search(r'Running (\d+) test cases?',text);result['unit_test_execution']=bool(m and int(m.group(1))>0)
 result['status']='NODE_AND_UNITS_PASS' if code==0 and result['unit_test_execution'] else 'UNIT_RUN_FAILURE'
 if result['status']!='NODE_AND_UNITS_PASS':raise RuntimeError('Unit tests did not pass; retain detailed result')
def retain():
 if result.get('process_active') or not result.get('cleanup_confirmed',True):raise RuntimeError('Process quiescence unconfirmed; checkpoint refused')
 source_identity('retained');catalog=json.loads((E/'retained-source.json').read_text())
 if catalog!=json.loads((E/'before-source.json').read_text()):raise RuntimeError('Source changed before checkpoint')
 if not result.get('profile') or not (ROOT/'project-build/CMakeCache.txt').exists():raise RuntimeError('No configured profile to checkpoint')
 result['checkpoint_capture']=checkpoint.capture(ROOT,SOURCE,result['profile'],catalog,{'status':result['status'],'node_exit':result.get('node_exit'),'unit_build_exit':result.get('unit_build_exit')})
 marker=ROOT/'project-build/btx-checkpoint.json';shutil.copyfile(marker,E/'btx-checkpoint.json')
 j=json.loads(marker.read_text());result['objects_retained']=sum(x.endswith('.obj') for x in j['files']);save()
 with open(os.environ['GITHUB_OUTPUT'],'a',encoding='utf-8') as f:f.write('checkpoint_valid=true\n')
stage=sys.argv[1];failed=False
try:
 if stage!='retain' and 'ERROR' in result['stages'].values():raise RuntimeError('Prior stage failed; stopping continuation')
 result['stages'][stage]='RUNNING';save();{'openssl':openssl,'vcpkg':vcpkg,'profile':profile,'configure':configure,'node':node,'unitbuild':unitbuild,'units':units,'retain':retain}[stage]();result['stages'][stage]='COMPLETE'
except Exception as ex:
 failed=True;result['stages'][stage]='ERROR'
 if stage=='retain':result['retention_error']=str(ex)
 else:
  if isinstance(ex,TimeoutError):result['status']='TIMEOUT_'+stage.upper()
  elif result['status'] not in ['NODE_BUILD_FAILURE','UNIT_BUILD_FAILURE','UNIT_RUN_FAILURE']:result['status']='ERROR_'+stage.upper()
  result['first_failed_stage']=stage;result['error']=type(ex).__name__+': '+str(ex)
 print('Stage failed',stage,str(ex),flush=True)
finally:
 try:
  source_identity('after');result['tracked_source_unchanged']=json.loads((E/'before-source.json').read_text())==json.loads((E/'after-source.json').read_text())
  if not result['tracked_source_unchanged']:raise RuntimeError('Tracked source changed')
 except Exception as ex:failed=True;result['source_verification_error']=str(ex)
 save();print('Result',stage,result['status'],flush=True)
raise SystemExit(1 if failed else 0)
