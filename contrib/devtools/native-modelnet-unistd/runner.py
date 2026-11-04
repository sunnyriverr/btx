from pathlib import Path
import os,json,subprocess,base64,hashlib,platform,shutil
P=Path(__file__).resolve().parent
D=json.loads((P/'payload.json').read_text())
ROOT=Path(os.environ['RUNNER_TEMP'])/'native-modelnet-unistd';ROOT.mkdir()
E=ROOT/'evidence';E.mkdir()
result={'base':D['base'],'platform':platform.platform(),'sdk':os.environ.get('WindowsSDKVersion'),'toolset':os.environ.get('VCToolsVersion'),'scope':'Component CMake objects/direct-header runtime; not stock root/full node/unit qualification','commands':[],'variants':{},'errors':[]}
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def run(label,command,cwd):
 p=subprocess.run(command,cwd=cwd,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=100)
 log=E/(label+'.log');log.write_bytes(p.stdout)
 result['commands'].append({'label':label,'command':command,'exit':p.returncode,'log_sha256':sha(log)})
 print(label,p.returncode,p.stdout.decode(errors='replace')[-4500:],flush=True);return p
template='''cmake_minimum_required(VERSION 3.22)
project(native_modelnet_unistd_component LANGUAGES CXX)
set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_MSVC_RUNTIME_LIBRARY MultiThreaded)
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)
add_library(bitcoin_modelnet OBJECT src/modelnet/package_execute.cpp src/modelnet/capability_control.cpp)
target_include_directories(bitcoin_modelnet PUBLIC ${PROJECT_SOURCE_DIR}/src ${PROJECT_SOURCE_DIR}/src/univalue/include)
target_compile_definitions(bitcoin_modelnet PUBLIC _WIN32_WINNT=0x0A00 _WIN32_IE=0x0A00 WIN32_LEAN_AND_MEAN NOMINMAX _CRT_SECURE_NO_WARNINGS)
@WINDOWS_BLOCK@
add_executable(direct_header test/util/windows_modelnet_unistd_tests.cpp)
target_include_directories(direct_header PRIVATE $<TARGET_PROPERTY:bitcoin_modelnet,INCLUDE_DIRECTORIES>)
target_compile_options(direct_header PRIVATE $<TARGET_PROPERTY:bitcoin_modelnet,COMPILE_OPTIONS>)
target_compile_definitions(direct_header PRIVATE $<TARGET_PROPERTY:bitcoin_modelnet,COMPILE_DEFINITIONS>)
target_link_libraries(direct_header PRIVATE ws2_32 iphlpapi bcrypt userenv advapi32 ole32)
'''
try:
 for cc in ['cl','clang-cl']:
  run(cc+'-version',[cc,'/Bv'] if cc=='cl' else[cc,'--version'],ROOT)
  for variant in ['baseline','candidate']:
   name=cc+'-'+variant;source=ROOT/name;source.mkdir();files=dict(D['files'])
   files['test/util/windows_modelnet_unistd_tests.cpp']=D['product']['test/util/windows_modelnet_unistd_tests.cpp']
   if variant=='candidate':files['src/compat/msvc/unistd.h']=D['product']['src/compat/msvc/unistd.h']
   for f,b in files.items():
    q=source/f;q.parent.mkdir(parents=True,exist_ok=True);q.write_bytes(base64.b64decode(b))
   (source/'CMakeLists.txt').write_text(template.replace('@WINDOWS_BLOCK@',D['blocks'][variant]))
   build=source/'build';v={'files':{f:sha(source/f)for f in files},'cmake_fixture_sha256':sha(source/'CMakeLists.txt')};result['variants'][name]=v
   cfg=run(name+'-configure',['cmake','-S',str(source),'-B',str(build),'-G','Ninja','-DCMAKE_CXX_COMPILER='+cc,'-DCMAKE_BUILD_TYPE=Release'],source)
   if cfg.returncode:result['errors'].append(name+' configure failed');continue
   shutil.copyfile(source/'CMakeLists.txt',E/(name+'-CMakeLists.txt'));shutil.copyfile(build/'compile_commands.json',E/(name+'-compile_commands.json'));v['compile_commands_sha256']=sha(E/(name+'-compile_commands.json'))
   prod=run(name+'-objects',['cmake','--build',str(build),'--target','bitcoin_modelnet','--verbose','--','-k','0','-j','1'],source)
   ctrl=run(name+'-header-build',['cmake','--build',str(build),'--target','direct_header','--verbose','--','-j','1'],source)
   if variant=='baseline':
    if prod.returncode==0 or ctrl.returncode==0 or b'unistd.h'not in prod.stdout or b'unistd.h'not in ctrl.stdout:result['errors'].append(name+' missing expected direct-header failure')
   else:
    if prod.returncode or ctrl.returncode:result['errors'].append(name+' candidate compile failed');continue
    exe=build/'direct_header.exe';v['executable_sha256']=sha(exe);shutil.copyfile(exe,E/(name+'-direct_header.exe'));v['object_sha256']={str(x.relative_to(build)):sha(x)for x in build.rglob('*.obj')}
    deps=run(name+'-dependencies',['ninja','-C',str(build),'-t','deps'],source)
    normalized_deps=deps.stdout.decode(errors='replace').replace('\\','/').lower()
    if deps.returncode or '/src/compat/msvc/unistd.h' not in normalized_deps:result['errors'].append(name+' exact native include trace absent')
    if not all(any(seed in obj for obj in v['object_sha256'])for seed in ['package_execute.cpp','capability_control.cpp']):result['errors'].append(name+' production object hashes incomplete')
    runtime=run(name+'-runtime',[str(exe)],source)
    if runtime.returncode or b'PASS 10 direct-header checks'not in runtime.stdout:result['errors'].append(name+' runtime failed')
except Exception as ex:result['errors'].append(type(ex).__name__+': '+str(ex))
finally:
 (E/'result.json').write_text(json.dumps(result,indent=2)+'\n');print('Errors:',result['errors'],flush=True)
raise SystemExit(bool(result['errors']))
