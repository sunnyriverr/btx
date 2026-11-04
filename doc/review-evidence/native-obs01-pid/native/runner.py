from pathlib import Path
import os,sys,json,subprocess,hashlib,datetime,time,urllib.request,shutil,re
P=Path(__file__).resolve().parent
BASE='ecd9310a8b35dbf1260d1a64e0ff39bb50e7a629'
VCPKG_COMMIT='afa249f12f52ed8a3b919f195495ba8b330288d1'
OPENSSL_SHA='967311f84955316969bdb1d8d4b983718ef42338639c621ec4c34fddef355e99'
ROOT=Path(os.environ['BTX_NATIVE_ROOT']);SOURCE=Path(os.environ['GITHUB_WORKSPACE'])/'btx'
E=ROOT/'evidence';E.mkdir(parents=True,exist_ok=True);STATE=E/'result.json'
result=json.loads(STATE.read_text())if STATE.exists()else{'base':BASE,'scope':'Same actual native Windows generated obs01.cpp object before/after scoped PID portability repair','status':'IN_PROGRESS','commands':[],'stages':{},'product_fixes':[],'whole_node_build_run':False,'unit_test_execution':False,'PR397_in_upstream':True,'compiler_env':{k:os.environ.get(k)for k in ['VCToolsVersion','WindowsSDKVersion','ImageVersion','PROCESSOR_ARCHITECTURE']}}
EXPECTED_WORKING_BLOBS={}
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save():
 result['updated_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat();STATE.write_text(json.dumps(result,indent=2)+'\n')
def run(label,command,cwd=ROOT,timeout=1800):
 log=E/(label+'.log');start=time.monotonic();timed_out=False;result['active_command']=label;save()
 with log.open('wb')as out:
  proc=subprocess.Popen(command,cwd=cwd,stdout=out,stderr=subprocess.STDOUT)
  while proc.poll()is None:
   if time.monotonic()-start>timeout:
    cleanup=subprocess.run(['taskkill','/PID',str(proc.pid),'/T','/F'],capture_output=True)
    (E/(label+'-timeout-cleanup.log')).write_bytes(cleanup.stdout+cleanup.stderr)
    proc.wait(timeout=30);timed_out=True;break
   if label=='native-daemon-build':
    resources=host_resources();elapsed=int(time.monotonic()-start)
    if resources['disk_free_bytes']<2*1024**3:
     cleanup=subprocess.run(['taskkill','/PID',str(proc.pid),'/T','/F'],capture_output=True);(E/(label+'-disk-stop.log')).write_bytes(cleanup.stdout+cleanup.stderr);proc.wait(timeout=30);result['resource_stop']='Hosted disk below2GiB';break
    if elapsed//30>result.get('last_progress_bucket',-1):
     result['last_progress_bucket']=elapsed//30;result.setdefault('build_resource_samples',[]).append({'seconds':elapsed,**resources});save();print('Daemon build elapsed',elapsed,'seconds; free disk',resources['disk_free_bytes'],'available RAM',resources['available_ram_bytes'],flush=True)
   time.sleep(2)
 result['commands'].append({'label':label,'command':command,'cwd':str(cwd),'exit':proc.returncode,'process_pid':proc.pid,'seconds':round(time.monotonic()-start,2),'timed_out':timed_out,'log_sha256':sha(log)});save();print(label,proc.returncode,log.read_text(errors='replace')[-6500:],flush=True)
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
  if raw!=EXPECTED_WORKING_BLOBS.get(name,oid):raise RuntimeError('working bytes differ: '+name)
  entries[name]={'git_mode':mode,'git_blob':oid,'expected_working_blob':EXPECTED_WORKING_BLOBS.get(name,oid),'working_sha256':hashlib.sha256(data).hexdigest()}
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
def configure():
 tool=ROOT/'vcpkg';prefix=ROOT/'openssl-3.5.4-static';build=ROOT/'project-build'
 os.environ.update(VCPKG_ROOT=str(tool),VCPKG_DISABLE_METRICS='1',VCPKG_MAX_CONCURRENCY='2',VCPKG_BINARY_SOURCES='clear;files,'+str(ROOT/'binary-cache')+',readwrite');(ROOT/'binary-cache').mkdir(exist_ok=True)
 args=['cmake','--debug-find-pkg=OpenSSL','--preset','windows-clangcl-static','-S',str(SOURCE),'-B',str(build),'-DBUILD_TESTS=ON','-DVCPKG_MANIFEST_NO_DEFAULT_FEATURES=ON','-DVCPKG_MANIFEST_FEATURES=wallet;tests;zeromq','-DVCPKG_INSTALLED_DIR='+str(ROOT/'vcpkg-installed'),'-DOPENSSL_ROOT_DIR='+str(prefix),'-DOPENSSL_USE_STATIC_LIBS=ON','-DOPENSSL_MSVC_STATIC_RT=ON','-DOPENSSL_INCLUDE_DIR='+str(prefix/'include'),'-DOPENSSL_SSL_LIBRARY='+str(prefix/'lib/libssl.lib'),'-DOPENSSL_CRYPTO_LIBRARY='+str(prefix/'lib/libcrypto.lib'),'-DCMAKE_EXPORT_COMPILE_COMMANDS=ON']
 code=run('root-configure',args,SOURCE,1800)
 for f in ['CMakeCache.txt','CMakeFiles/CMakeConfigureLog.yaml','vcpkg-manifest-install.log','compile_commands.json']:
  if(build/f).exists():shutil.copyfile(build/f,E/Path(f).name)
 result['configure_exit']=code
 if code:result.update(status='BLOCKED_CONFIGURE',first_failed_stage='actual_root_configure');return
 need('generated-targets',['ninja','-C',str(build),'-t','targets','all']);targets=(E/'generated-targets.log').read_text(errors='replace');target='src/modelnet/CMakeFiles/bitcoin_modelnet.dir/obs01/obs01.cpp.obj'
 if target+':' not in targets:raise RuntimeError('real generated obs01 object absent')
 entries=json.loads((build/'compile_commands.json').read_text());selected=[x for x in entries if x['file'].replace('\\','/').endswith('/src/modelnet/obs01/obs01.cpp')]
 if len(selected)!=1:raise RuntimeError('ambiguous generated obs01 compile command')
 (E/'obs01-compile-command.json').write_text(json.dumps(selected[0],indent=2)+'\n')
 manifest=json.loads((P/'source-manifest.json').read_text());file=manifest['file'];baseline=(SOURCE/file).read_bytes();candidate=(P/'candidate.cpp').read_bytes()
 if manifest['base']!=BASE or sha(SOURCE/file)!=manifest['baseline_sha256'] or hashlib.sha256(candidate).hexdigest()!=manifest['candidate_sha256']:raise RuntimeError('source input mismatch')
 for row in json.loads((P/'fixture-manifest.json').read_text()).values():
  if isinstance(row,dict)and'fixture'in row:
   if sha(P/row['fixture'])!=row['sha256']:raise RuntimeError('fixture input hash mismatch')
 command=['cmake','--build',str(build),'--target',target,'--verbose','--','-j','1'];result['target']=target;result['before_object_resources']=host_resources();save()
 if result['before_object_resources']['disk_free_bytes']<6*1024**3 or result['before_object_resources']['available_ram_bytes']<4*1024**3:raise RuntimeError('Hosted resource prerequisites unavailable')
 code=run('baseline-obs01-object',command,SOURCE,240);log=(E/'baseline-obs01-object.log').read_text(errors='replace')
 if code==0 or "obs01.cpp(120,90): error: no member named 'getpid'"not in log:raise RuntimeError('baseline did not reproduce exact native getpid failure')
 if(build/target).exists():raise RuntimeError('baseline unexpectedly produced object')
 source_identity('baseline-after')
 def fixture_build(compiler,variant,expect_missing=False):
  label=variant+'-'+compiler;exe=ROOT/(label+'.exe');fixture=P/(variant+'-pid-check.cpp');cmd=[compiler,'/nologo','/std:c++20','/EHsc','/O2','/MT','/utf-8','/D_CRT_SECURE_NO_WARNINGS','/DNOMINMAX','/I'+str(SOURCE/'src/compat/msvc'),'/I'+str(SOURCE/'src/compat/mingw'),'/I'+str(build/'src'),'/I'+str(SOURCE/'src'),'/FI'+str(SOURCE/'src/compat/mingw/posix_extra.h'),str(fixture),'/Fe'+str(exe),'/Fo'+str(ROOT/(label+'.obj')),'/link','ws2_32.lib']
  rc=run(label+'-build',cmd,ROOT,90)
  if expect_missing:
   text=(E/(label+'-build.log')).read_text(errors='replace')
   if rc==0 or 'getpid'not in text or not re.search(r'(?i)error(?:\s+C\d+)?\s*:',text):raise RuntimeError('baseline fixture not blocked by missing PID declaration: '+label)
   return None
  if rc:raise RuntimeError('fixture build failed: '+label)
  shutil.copyfile(exe,E/(label+'.exe'));result.setdefault('compiled_fixtures',{})[label]=sha(exe);return exe
 def fixture_run(exe,label,mutant=False):
  scratch=ROOT/(label+'-files');scratch.mkdir();keys=['TMP','TEMP','TMPDIR'];old={k:os.environ.get(k)for k in keys}
  try:
   for key in keys:os.environ[key]=str(scratch)
   rc=run(label+'-run',[str(exe),str(scratch)],ROOT,60);text=(E/(label+'-run.log')).read_text(errors='replace')
   observed=re.search(r'PID oracle=(\d+)',text)
   if not observed or int(observed.group(1))!=result['commands'][-1]['process_pid']:raise RuntimeError('launcher/oracle PID mismatch: '+label)
   if mutant:
    if rc!=1 or 'FAIL PID-derived exact prefix/suffix'not in text:raise RuntimeError('wrong PID workaround not rejected')
   elif rc or 'RESULT checks=37 failures=0'not in text:raise RuntimeError('legitimate PID/path/cleanup control failed: '+label)
   if list(scratch.iterdir()):raise RuntimeError('owned fixture parent not empty')
   scratch.rmdir()
  finally:
   for key,value in old.items():
    if value is None:os.environ.pop(key,None)
    else:os.environ[key]=value
   if scratch.exists():shutil.rmtree(scratch)
 for compiler in ['cl','clang-cl']:fixture_build(compiler,'baseline',True)
 try:
  EXPECTED_WORKING_BLOBS[file]=manifest['candidate_blob'];(SOURCE/file).write_bytes(candidate);result['product_fixes']=[file];source_identity('candidate-before')
  code=run('candidate-obs01-object',command,SOURCE,240)
  if code:result.update(status='BLOCKED_CANDIDATE_OBJECT',failed_target=target);return
  if not(build/target).exists():raise RuntimeError('candidate command passed without object')
  shutil.copyfile(build/target,E/'candidate-obs01.obj');result['obs01_object_sha256']=sha(build/target)
  if sha(build/'compile_commands.json')!=sha(E/'compile_commands.json'):raise RuntimeError('compile database changed')
  for compiler in ['cl','clang-cl']:
   exe=fixture_build(compiler,'candidate');fixture_run(exe,'candidate-'+compiler)
  exe=fixture_build('clang-cl','wrong');fixture_run(exe,'wrong-clang-cl',True)
  source_identity('candidate-after');result.update(status='PAIRED_OBS01_PID_AND_CLEANUP_PASS',same_generated_target_command=command,compile_database_unchanged=True,full_daemon_build=False,qualification_gates_executed=False,fixture_executed=True,owned_filesystem_fixture_cleaned=True,wrong_pid_mutant_rejected=True,POSIX_control_external='mac/results.json')
 finally:
  (SOURCE/file).write_bytes(baseline);EXPECTED_WORKING_BLOBS.pop(file,None);source_identity('restored');result['source_restored']=sha(SOURCE/file)==manifest['baseline_sha256']

def host_resources():
 import ctypes
 class MemoryStatus(ctypes.Structure):
  _fields_=[('length',ctypes.c_uint32),('load',ctypes.c_uint32)]+[(x,ctypes.c_uint64) for x in ['total_phys','avail_phys','total_page','avail_page','total_virtual','avail_virtual','avail_extended']]
 memory=MemoryStatus();memory.length=ctypes.sizeof(memory);ok=ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(memory))
 return {'disk_free_bytes':shutil.disk_usage(ROOT).free,'cpus':os.cpu_count(),'total_ram_bytes':memory.total_phys if ok else None,'available_ram_bytes':memory.avail_phys if ok else None}

stage=sys.argv[1]
try:
 if result['status'].startswith('BLOCKED')or result['status']=='SETUP_ERROR':print('Prior failure retained; skipping',stage)
 else:
  result['stages'][stage]='RUNNING';save();{'openssl':openssl,'vcpkg':vcpkg,'configure':configure}[stage]();result['stages'][stage]='COMPLETE'
except Exception as ex:
 label=result.get('active_command') or result.get('last_completed_command') or stage
 status=('BUILD_TIMEOUT' if label=='native-daemon-build' else 'COMMAND_TIMEOUT') if isinstance(ex,TimeoutError) else ('POST_LINK_INSPECTION_ERROR' if result.get('daemon_executable_sha256') else 'SETUP_ERROR')
 result.update(status=status,first_failed_stage=label,error=type(ex).__name__+': '+str(ex));result['stages'][stage]='ERROR';print(result['error'],flush=True)
finally:
 try:
  manifest=json.loads((P/'source-manifest.json').read_text())
  if sha(SOURCE/manifest['file'])==manifest['candidate_sha256']:EXPECTED_WORKING_BLOBS[manifest['file']]=manifest['candidate_blob']
  source_identity('after');before=json.loads((E/'before-source.json').read_text());after=json.loads((E/'after-source.json').read_text());changed=[f for f in before['files'] if before['files'][f]!=after['files'][f]];result['tracked_source_changed_files']=changed
  if changed not in ([],[manifest['file']]):raise RuntimeError('unexpected tracked source change')
 except Exception as ex:result['source_verification_error']=str(ex);result['status']='SETUP_ERROR'
 save();print('Recorded diagnostic status:',result['status'],flush=True)
raise SystemExit(result['status']=='SETUP_ERROR')
