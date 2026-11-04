from pathlib import Path
import os,sys,json,subprocess,hashlib,datetime,time,urllib.request,shutil
P=Path(__file__).resolve().parent
BASE='46caec762b0f130d497313d8ca9fa6894ac19ccd'
VCPKG_COMMIT='afa249f12f52ed8a3b919f195495ba8b330288d1'
OPENSSL_SHA='967311f84955316969bdb1d8d4b983718ef42338639c621ec4c34fddef355e99'
ROOT=Path(os.environ['BTX_NATIVE_ROOT']);SOURCE=Path(os.environ['GITHUB_WORKSPACE'])/'btx'
E=ROOT/'evidence';E.mkdir(parents=True,exist_ok=True);STATE=E/'result.json'
result=json.loads(STATE.read_text())if STATE.exists()else{'base':BASE,'scope':'Exact root-generated unit portability before/after plus actual-helper runtime controls','status':'IN_PROGRESS','commands':[],'stages':{},'product_fixes':[],'planned_test_source_fix':'src/test/matmul_backend_capabilities_tests.cpp','whole_node_build_run':False,'unit_test_execution':False,'PR397_in_upstream':True,'compiler_env':{k:os.environ.get(k)for k in ['VCToolsVersion','WindowsSDKVersion','ImageVersion','PROCESSOR_ARCHITECTURE']}}
EXPECTED_WORKING_BLOBS={}
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save():
 result['updated_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat();STATE.write_text(json.dumps(result,indent=2)+'\n')
def run(label,command,cwd=ROOT,timeout=1800):
 log=E/(label+'.log');start=time.monotonic();timed_out=False
 with log.open('wb')as out:
  proc=subprocess.Popen(command,cwd=cwd,stdout=out,stderr=subprocess.STDOUT)
  while proc.poll()is None:
   if time.monotonic()-start>timeout:
    cleanup=subprocess.run(['taskkill','/PID',str(proc.pid),'/T','/F'],capture_output=True)
    (E/(label+'-timeout-cleanup.log')).write_bytes(cleanup.stdout+cleanup.stderr)
    proc.wait(timeout=30);timed_out=True;break
   time.sleep(2)
 result['commands'].append({'label':label,'command':command,'cwd':str(cwd),'exit':proc.returncode,'seconds':round(time.monotonic()-start,2),'timed_out':timed_out,'log_sha256':sha(log)});save();print(label,proc.returncode,log.read_text(errors='replace')[-6500:],flush=True)
 if timed_out:raise TimeoutError(label+' timed out; owned process tree terminated and log retained')
 return proc.returncode
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
 prefix=ROOT/'openssl-3.5.4-static';metadata();archive=ROOT/'openssl-3.5.4.tar.gz';cached=(prefix/'lib/libcrypto.lib').exists()
 if cached:
  receipt=prefix/'btx-build-provenance.json'
  if not receipt.exists():raise RuntimeError('incomplete OpenSSL cache; no provenance')
  prior=json.loads(receipt.read_text())
  if prior['source_sha256']!=OPENSSL_SHA or prior['toolset']!=os.environ.get('VCToolsVersion'):raise RuntimeError('cached OpenSSL source/toolset mismatch')
  for f,h in prior['files'].items():
   if sha(prefix/f)!=h:raise RuntimeError('cached OpenSSL library/header mismatch')
  if sha(prefix/'btx-Makefile.txt')!=prior['makefile_sha256']:raise RuntimeError('cached OpenSSL Makefile mismatch')
  shutil.copyfile(prefix/'btx-Makefile.txt',E/'openssl-Makefile.txt')
 result['openssl_cache_reused']=cached
 if not archive.exists():urllib.request.urlretrieve('https://github.com/openssl/openssl/releases/download/openssl-3.5.4/openssl-3.5.4.tar.gz',archive)
 if sha(archive)!=OPENSSL_SHA:raise RuntimeError('OpenSSL official source digest mismatch')
 result['openssl_source_sha256']=sha(archive)
 if not(prefix/'lib/libcrypto.lib').exists():
  unpack=ROOT/'openssl-source';unpack.mkdir(exist_ok=True);need('openssl-extract',['tar','-xzf',str(archive),'-C',str(unpack)]);source=unpack/'openssl-3.5.4'
  need('openssl-configure',['perl','Configure','VC-WIN64A','no-shared','no-tests','--prefix='+prefix.as_posix(),'--openssldir='+(prefix/'ssl').as_posix(),'--libdir=lib'],source)
  need('openssl-build',['nmake','/S','build_sw'],source,1200);need('openssl-install',['nmake','/S','install_sw'],source,180);shutil.copyfile(source/'Makefile',E/'openssl-Makefile.txt');need('openssl-configdata',['perl','configdata.pm','--dump'],source)
 need('openssl-version',[str(prefix/'bin/openssl.exe'),'version','-a'])
 probe=E/'openssl_probe.c';probe.write_text((P/'openssl_probe.c').read_text());exe=E/'openssl_probe.exe'
 need('openssl-probe-build',['cl','/nologo','/MT','/O2','/I'+str(prefix/'include'),str(probe),'/Fe'+str(exe),'/Fo'+str(E/'openssl_probe.obj'),'/link','/LIBPATH:'+str(prefix/'lib'),'libssl.lib','libcrypto.lib','ws2_32.lib','gdi32.lib','advapi32.lib','crypt32.lib','user32.lib'])
 need('openssl-probe-run',[str(exe)]);need('openssl-probe-dependents',['dumpbin','/dependents',str(exe)]);deps=(E/'openssl-probe-dependents.log').read_text(errors='replace').lower()
 if any(x in deps for x in ['libcrypto-','libssl-','vcruntime']):raise RuntimeError('unexpected dynamic dependency in static OpenSSL smoke')
 result['openssl_prefix']=str(prefix);result['openssl_files']={f:sha(prefix/f)for f in ['include/openssl/opensslv.h','lib/libssl.lib','lib/libcrypto.lib','bin/openssl.exe']};result['openssl_probe_executable_sha256']=sha(exe)
 if not cached:
  shutil.copyfile(E/'openssl-Makefile.txt',prefix/'btx-Makefile.txt')
  (prefix/'btx-build-provenance.json').write_text(json.dumps({'source_sha256':OPENSSL_SHA,'toolset':os.environ.get('VCToolsVersion'),'files':result['openssl_files'],'configuration':'VC-WIN64A no-shared no-tests, libdir=lib; staticCRT per pinned OpenSSL config','makefile_sha256':sha(E/'openssl-Makefile.txt')},indent=2)+'\n')
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
 need('generated-targets',['ninja','-C',str(build),'-t','targets','all']);targets=(E/'generated-targets.log').read_text(errors='replace')
 target='src/test/CMakeFiles/test_btx.dir/matmul_backend_capabilities_tests.cpp.obj'
 if target+':' not in targets:raise RuntimeError('expected generated target missing')
 command=['cmake','--build',str(build),'--target',target,'--verbose','--','-j','1']
 result['generated_compile_database_sha256']=sha(build/'compile_commands.json')
 original_code=run('baseline-unit-object',command,SOURCE,180)
 baseline_log=(E/'baseline-unit-object.log').read_text(errors='replace')
 if original_code==0 or "(24,10): fatal error: 'unistd.h' file not found" not in baseline_log:raise RuntimeError('baseline did not reproduce exact unit portability blocker')
 source_identity('baseline-after')
 if json.loads((E/'before-source.json').read_text())!=json.loads((E/'baseline-after-source.json').read_text()):raise RuntimeError('baseline source changed')
 file='src/test/matmul_backend_capabilities_tests.cpp'
 manifest=json.loads((P/'source-manifest.json').read_text());candidate=(P/'candidate.cpp').read_bytes()
 if manifest['base']!=BASE or sha(SOURCE/file)!=manifest['baseline_sha256'] or hashlib.sha256(candidate).hexdigest()!=manifest['candidate_sha256']:raise RuntimeError('candidate input identity differs')
 EXPECTED_WORKING_BLOBS[file]=hashlib.sha1(b'blob '+str(len(candidate)).encode()+b'\0'+candidate).hexdigest()
 (SOURCE/file).write_bytes(candidate);result['product_fixes']=[file]
 source_identity('candidate-before')
 candidate_code=run('candidate-unit-object',command,SOURCE,180)
 if candidate_code:result.update(status='BLOCKED_CANDIDATE_OBJECT',failed_target=target);return
 if sha(build/'compile_commands.json')!=result['generated_compile_database_sha256']:raise RuntimeError('generated compilation database changed')
 result['unit_object_sha256']=sha(build/target);shutil.copyfile(build/target,E/'candidate-unit.obj')
 result['candidate_source_sha256']=sha(SOURCE/file)
 component_controls(SOURCE/file)
 result['status']='PAIRED_GENERATED_UNIT_AND_COMPONENT_CONTROLS_PASS'

def component_controls(source):
 text=source.read_text();start=text.index('class ScopedEnvVar\n');end=text.index('\n};',start)+len('\n};');helper=text[start:end]
 tests_start=text.index('BOOST_AUTO_TEST_CASE(scoped_environment_restores_values)');tests_end=text.index('BOOST_AUTO_TEST_CASE(cpu_backend_always_available)',tests_start);cases=text[tests_start:tests_end]
 if cases!=(P/'in-tree-cases.inc').read_text():raise RuntimeError('extracted cases differ')
 includes=ROOT/'vcpkg-installed/x64-windows-static/include';header='#define BOOST_TEST_MODULE BackendScopedEnvironment\n#include <boost/test/included/unit_test.hpp>\n#include <cstdlib>\n#include <string>\n#include <cstdio>\n'
 fixture=(P/'component_fixture.inc').read_text();component=header+helper+'\n'+fixture+'\n'+cases
 cpp=E/'component.cpp';cpp.write_text(component);result['component_source_sha256']=sha(cpp)
 probe=includes/'boost/version.hpp';result['boost_version_header_sha256']=sha(probe)
 for compiler in ['clang-cl','cl']:
  exe=E/(compiler+'-component.exe');obj=E/(compiler+'-component.obj')
  need(compiler+'-component-build',[compiler,'/nologo','/std:c++20','/MT','/EHsc','/I'+str(includes),str(cpp),'/Fe'+str(exe),'/Fo'+str(obj)],timeout=180)
  for name,value in [('absent',None),('preexisting','before-test')]:
   if value is None:os.environ.pop('BTX_TEST_BACKEND_SCOPED_ENV',None)
   else:os.environ['BTX_TEST_BACKEND_SCOPED_ENV']=value
   need(compiler+'-component-'+name,[str(exe),'--log_level=test_suite'],timeout=60)
  result[compiler+'_component_sha256']=sha(exe);result[compiler+'_component_object_sha256']=sha(obj);obj.unlink()
 dt_start=helper.index('    ~ScopedEnvVar()');dt_end=helper.index('\nprivate:',dt_start)
 mutant=helper[:dt_start]+'    ~ScopedEnvVar() {}\n'+helper[dt_end:]
 mcpp=E/'component-no-restore.cpp';mcpp.write_text(header+mutant+'\n'+fixture+'\n'+cases)
 mexe=E/'component-no-restore.exe'
 need('mutant-component-build',['clang-cl','/nologo','/std:c++20','/MT','/EHsc','/I'+str(includes),str(mcpp),'/Fe'+str(mexe),'/Fo'+str(E/'component-no-restore.obj')],timeout=180)
 os.environ['BTX_TEST_BACKEND_SCOPED_ENV']='before-test'
 mutant_exit=run('mutant-component-expected-failure',[str(mexe),'--log_level=test_suite'],timeout=60)
 mutant_log=(E/'mutant-component-expected-failure.log').read_text(errors='replace')
 if mutant_exit==0 or 'has failed' not in mutant_log or 'scoped_environment_restores_' not in mutant_log:raise RuntimeError('no-restore mutant did not fail the expected assertions')
 result['component_test_execution']=True
 os.environ.pop('BTX_TEST_BACKEND_SCOPED_ENV',None)

stage=sys.argv[1]
try:
 if result['status'].startswith('BLOCKED')or result['status']=='SETUP_ERROR':print('Prior failure retained; skipping',stage)
 else:
  result['stages'][stage]='RUNNING';save();{'openssl':openssl,'vcpkg':vcpkg,'configure':configure}[stage]();result['stages'][stage]='COMPLETE'
except Exception as ex:
 result.update(status='SETUP_ERROR',first_failed_stage=stage,error=type(ex).__name__+': '+str(ex));result['stages'][stage]='ERROR';print(result['error'],flush=True)
finally:
 try:
  source_identity('after');before=json.loads((E/'before-source.json').read_text());after=json.loads((E/'after-source.json').read_text());changed=[f for f in before['files'] if before['files'][f]!=after['files'][f]];result['tracked_source_changed_files']=changed
  if changed!=list(EXPECTED_WORKING_BLOBS):raise RuntimeError('unexpected tracked source identity delta')
 except Exception as ex:result['source_verification_error']=str(ex);result['status']='SETUP_ERROR'
 save();print('Recorded diagnostic status:',result['status'],flush=True)
raise SystemExit(result['status']=='SETUP_ERROR')
