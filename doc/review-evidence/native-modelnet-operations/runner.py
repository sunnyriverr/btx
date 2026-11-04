from pathlib import Path
import os,sys,json,subprocess,hashlib,datetime,time,urllib.request,shutil,re
P=Path(__file__).resolve().parent
BASE='1b404ed8e52eae249ac73036007ba5a382b0d3ba'
VCPKG_COMMIT='afa249f12f52ed8a3b919f195495ba8b330288d1'
OPENSSL_SHA='967311f84955316969bdb1d8d4b983718ef42338639c621ec4c34fddef355e99'
ROOT=Path(os.environ['BTX_NATIVE_ROOT']);SOURCE=Path(os.environ['GITHUB_WORKSPACE'])/'btx'
E=ROOT/'evidence';E.mkdir(parents=True,exist_ok=True);STATE=E/'result.json'
result=json.loads(STATE.read_text())if STATE.exists()else{'base':BASE,'scope':'Same three native generated Modelnet targets, exact403 prerequisite, guarded Windows operations','status':'IN_PROGRESS','commands':[],'stages':{},'product_fixes':[],'whole_node_build_run':False,'unit_test_execution':False,'PR397_in_upstream':True,'compiler_env':{k:os.environ.get(k)for k in ['VCToolsVersion','WindowsSDKVersion','ImageVersion','PROCESSOR_ARCHITECTURE']}}
MANIFEST=json.loads((P/'source-manifest.json').read_text())
result.setdefault('job_started_epoch',time.time())
EXPECTED_WORKING_BLOBS={f:r['baseline']['git_blob'] for f,r in MANIFEST['files'].items()}
for f,row in MANIFEST['files'].items():
 data=(P/row['baseline']['input']).read_bytes()
 if hashlib.sha256(data).hexdigest()!=row['baseline']['sha256']:raise RuntimeError('baseline input mismatch')
 (SOURCE/f).write_bytes(data)

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save():
 result['updated_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat();STATE.write_text(json.dumps(result,indent=2)+'\n')
def run(label,command,cwd=ROOT,timeout=1800):
 remaining=65*60-(time.time()-result['job_started_epoch'])
 if remaining<30:raise TimeoutError('shared job budget exhausted before '+label)
 timeout=min(timeout,int(remaining))
 log=E/(label+'.log');start=time.monotonic();timed_out=False;result['active_command']=label;save()
 with log.open('wb')as out:
  proc=subprocess.Popen(command,cwd=cwd,stdout=out,stderr=subprocess.STDOUT)
  while proc.poll()is None:
   if time.monotonic()-start>timeout:
    cleanup=subprocess.run(['taskkill','/PID',str(proc.pid),'/T','/F'],capture_output=True)
    (E/(label+'-timeout-cleanup.log')).write_bytes(cleanup.stdout+cleanup.stderr)
    proc.wait(timeout=30);timed_out=True;break
   if label.endswith('-object') or label in ['modelnet-build','daemon-build','default-all-build','unit-run']:
    resources=host_resources();elapsed=int(time.monotonic()-start)
    if resources['disk_free_bytes']<2*1024**3:
     cleanup=subprocess.run(['taskkill','/PID',str(proc.pid),'/T','/F'],capture_output=True);(E/(label+'-disk-stop.log')).write_bytes(cleanup.stdout+cleanup.stderr);proc.wait(timeout=30);result['resource_stop']='Hosted disk below2GiB';break
    if elapsed//30>result.get('last_progress_bucket',-1):
     result['last_progress_bucket']=elapsed//30;result.setdefault('build_resource_samples',[]).append({'seconds':elapsed,**resources});save();print('Build elapsed',elapsed,'seconds; free disk',resources['disk_free_bytes'],'available RAM',resources['available_ram_bytes'],flush=True)
   time.sleep(2)
 result['commands'].append({'label':label,'command':command,'cwd':str(cwd),'exit':proc.returncode,'process_pid':proc.pid,'seconds':round(time.monotonic()-start,2),'timed_out':timed_out,'log_sha256':sha(log)});save();print(label,proc.returncode,log.read_text(errors='replace')[-6500:],flush=True)
 if result.get('resource_stop'):raise RuntimeError('terminal resource stop: '+result['resource_stop'])
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
def host_resources():
 import ctypes
 class MemoryStatus(ctypes.Structure):
  _fields_=[('length',ctypes.c_uint32),('load',ctypes.c_uint32)]+[(x,ctypes.c_uint64) for x in ['total_phys','avail_phys','total_page','avail_page','total_virtual','avail_virtual','avail_extended']]
 memory=MemoryStatus();memory.length=ctypes.sizeof(memory);ok=ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(memory))
 return {'disk_free_bytes':shutil.disk_usage(ROOT).free,'cpus':os.cpu_count(),'total_ram_bytes':memory.total_phys if ok else None,'available_ram_bytes':memory.avail_phys if ok else None}

def configure():
 tool=ROOT/'vcpkg';prefix=ROOT/'openssl-3.5.4-static';build=ROOT/'project-build'
 os.environ.update(VCPKG_ROOT=str(tool),VCPKG_DISABLE_METRICS='1',VCPKG_MAX_CONCURRENCY='2',VCPKG_BINARY_SOURCES='clear;files,'+str(ROOT/'binary-cache')+',readwrite');(ROOT/'binary-cache').mkdir(exist_ok=True)
 args=['cmake','--debug-find-pkg=OpenSSL','--preset','windows-clangcl-static','-S',str(SOURCE),'-B',str(build),'-DBUILD_TESTS=ON','-DVCPKG_MANIFEST_NO_DEFAULT_FEATURES=ON','-DVCPKG_MANIFEST_FEATURES=wallet;tests;zeromq','-DVCPKG_INSTALLED_DIR='+str(ROOT/'vcpkg-installed'),'-DOPENSSL_ROOT_DIR='+str(prefix),'-DOPENSSL_USE_STATIC_LIBS=ON','-DOPENSSL_MSVC_STATIC_RT=ON','-DOPENSSL_INCLUDE_DIR='+str(prefix/'include'),'-DOPENSSL_SSL_LIBRARY='+str(prefix/'lib/libssl.lib'),'-DOPENSSL_CRYPTO_LIBRARY='+str(prefix/'lib/libcrypto.lib'),'-DCMAKE_EXPORT_COMPILE_COMMANDS=ON']
 code=run('root-configure',args,SOURCE,1800)
 for f in ['CMakeCache.txt','CMakeFiles/CMakeConfigureLog.yaml','vcpkg-manifest-install.log','compile_commands.json']:
  if(build/f).exists():shutil.copyfile(build/f,E/Path(f).name)
 result['configure_exit']=code
 if code:result.update(status='BLOCKED_CONFIGURE',first_failed_stage='actual_root_configure');return
 targets={name:'src/modelnet/CMakeFiles/bitcoin_modelnet.dir/'+name+'.cpp.obj' for name in ['generate','pq1_runtime','helper']}
 need('generated-targets',['ninja','-C',str(build),'-t','targets','all'])
 listing=(E/'generated-targets.log').read_text(errors='replace')
 database=sha(build/'compile_commands.json');entries=json.loads((build/'compile_commands.json').read_text());selected={}
 for name,target in targets.items():
  if target+':' not in listing:raise RuntimeError('actual generated target absent: '+target)
  found=[x for x in entries if x['file'].replace('\\','/').endswith('/src/modelnet/'+name+'.cpp')]
  if len(found)!=1:raise RuntimeError('ambiguous compile command: '+name)
  selected[name]=found[0]
 (E/'selected-compile-commands.json').write_text(json.dumps(selected,indent=2)+'\n')
 resources=host_resources();result['before_object_resources']=resources;save()
 if resources['disk_free_bytes']<6*1024**3 or resources['available_ram_bytes']<4*1024**3:raise RuntimeError('hosted resources unavailable')
 baseline={f:(SOURCE/f).read_bytes() for f in MANIFEST['files']}
 try:
  for name,target in targets.items():
   cmd=['cmake','--build',str(build),'--target',target,'--verbose','--','-j','1']
   rc=run('baseline-'+name+'-object',cmd,SOURCE,300)
   text=(E/('baseline-'+name+'-object.log')).read_text(errors='replace')
   expected={'generate':['X_OK'],'pq1_runtime':['popen','pclose'],'helper':['S_IWOTH','pid_t']}[name]
   if rc==0 or not all(x in text for x in expected) or not re.search(r'error(?:\s+C\d+)?\s*:',text):raise RuntimeError('expected baseline failure missing: '+name)
   if(build/target).exists():raise RuntimeError('baseline produced object: '+name)
   if sha(build/'compile_commands.json')!=database:raise RuntimeError('baseline compile database changed')
  source_identity('baseline-after')
  for f,row in MANIFEST['files'].items():
   data=(P/row['candidate']['input']).read_bytes()
   if hashlib.sha256(data).hexdigest()!=row['candidate']['sha256']:raise RuntimeError('candidate input hash mismatch')
   (SOURCE/f).write_bytes(data);EXPECTED_WORKING_BLOBS[f]=row['candidate']['git_blob']
  result['product_fixes']=list(MANIFEST['files']);source_identity('candidate-before')
  for name,target in targets.items():
   cmd=['cmake','--build',str(build),'--target',target,'--verbose','--','-j','1']
   rc=run('candidate-'+name+'-object',cmd,SOURCE,600)
   if rc or not(build/target).exists():result.update(status='BLOCKED_CANDIDATE_OBJECT',failed_target=target);return
   shutil.copyfile(build/target,E/('candidate-'+name+'.obj'))
   if sha(build/'compile_commands.json')!=database:raise RuntimeError('candidate compile database changed')
  result['same_generated_targets_pass']=True;result['compile_database_unchanged']=True;save()
  need('native-controls',[sys.executable,str(P/'fixtures/native.py'),str(SOURCE),str(ROOT),str(E)],timeout=780)
  source_identity('candidate-after')
  result['status']='PAIRED_THREE_TARGETS_AND_NATIVE_CONTROLS_PASS';save()
  # Candidate-only continuation. The full failing baseline already exists.
  deadline=time.monotonic()+2400
  for label,target in [('modelnet-build','bitcoin_modelnet'),('daemon-build','btxd'),('default-all-build',None)]:
   if deadline-time.monotonic()<30:result['status']='INTEGRATION_BUDGET_EXHAUSTED';return
   cmd=['cmake','--build',str(build),'--verbose']
   if target:cmd+=['--target',target]
   cmd+=['--','-j','4','-k','1']
   if label=='daemon-build':result['whole_node_build_run']=True
   rc=run(label,cmd,SOURCE,int(deadline-time.monotonic()))
   result.setdefault('integration_gates',{})[label]={'exit':rc};save()
   if rc:result['status']='BLOCKED_INTEGRATION';result['first_failed_stage']=label;return
  units=build/'bin/test_btx.exe'
  if not units.exists():result['status']='UNIT_BINARY_ABSENT';return
  rc=run('unit-run',[str(units),'--log_level=test_suite','--report_level=detailed'],build,600)
  text=(E/'unit-run.log').read_text(errors='replace');match=re.search(r'Running (\d+) test cases?',text)
  result['unit_cases_announced']=int(match.group(1))if match else None
  result['unit_test_execution']=bool(match and int(match.group(1))>0)
  result['status']='FULL_NATIVE_PASS'if rc==0 and result['unit_test_execution']else'UNIT_FAILURES'
 finally:
  for f,data in baseline.items():(SOURCE/f).write_bytes(data);EXPECTED_WORKING_BLOBS[f]=MANIFEST['files'][f]['baseline']['git_blob']
  source_identity('restored');result['source_restored']=all((SOURCE/f).read_bytes()==data for f,data in baseline.items())

stage=sys.argv[1]
try:
 if result['status'].startswith('BLOCKED') or result['status']=='SETUP_ERROR':print('Prior failure retained; skipping',stage)
 else:
  result['stages'][stage]='RUNNING';save();{'openssl':openssl,'vcpkg':vcpkg,'configure':configure}[stage]();result['stages'][stage]='COMPLETE'
except Exception as ex:
 result.update(status='COMMAND_TIMEOUT'if isinstance(ex,TimeoutError)else'SETUP_ERROR',error=type(ex).__name__+': '+str(ex));result['stages'][stage]='ERROR';print(result['error'],flush=True)
finally:
 try:source_identity('after')
 except Exception as ex:result['source_verification_error']=str(ex);result['status']='SETUP_ERROR'
 save();print('Recorded diagnostic status:',result['status'],flush=True)
raise SystemExit(0 if result['status']in['PAIRED_THREE_TARGETS_AND_NATIVE_CONTROLS_PASS','FULL_NATIVE_PASS'] or (stage!='configure'and result['status']=='IN_PROGRESS') else 1)
