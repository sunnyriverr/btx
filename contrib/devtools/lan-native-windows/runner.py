from pathlib import Path
import os,sys,json,subprocess,hashlib,time,platform
S=Path(os.environ['GITHUB_WORKSPACE'])/'source';P=Path(__file__).resolve().parent;E=Path(os.environ['RUNNER_TEMP'])/'lan400-native-evidence';E.mkdir(exist_ok=True)
HEAD='3acc3f74d92f646cf95cdcb8c4d92a7ec97afc9a';R={'head':HEAD,'status':'IN_PROGRESS','profile':'Native full component TUs, C++20/O2/staticCRT, actual Windows compatibility shim; direct compiler qualification, not root-target/fullhelper','compiler_env':{x:os.environ.get(x) for x in ['VCToolsVersion','WindowsSDKVersion','ImageVersion','PROCESSOR_ARCHITECTURE']},'commands':[],'platform':platform.platform(),'results':{},'no_product_edits':None}
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(): (E/'result.json').write_text(json.dumps(R,indent=2)+'\n')
def run(label,args,timeout=60):
 start=time.monotonic();log=E/(label+'.log');timed_out=False
 with log.open('wb') as output:
  process=subprocess.Popen(args,cwd=E,stdout=output,stderr=subprocess.STDOUT)
  try:process.wait(timeout=timeout)
  except subprocess.TimeoutExpired:
   timed_out=True;R['status']='TIMEOUT';R['active_command']=label;save()
   cleanup=subprocess.run(['taskkill','/PID',str(process.pid),'/T','/F'],capture_output=True,timeout=15)
   (E/(label+'-timeout-cleanup.log')).write_bytes(cleanup.stdout+cleanup.stderr)
   process.wait(timeout=15);timed_out=True
 text=log.read_text(errors='replace');R['commands'].append({'label':label,'args':list(map(str,args)),'rc':process.returncode,'seconds':round(time.monotonic()-start,2),'timed_out':timed_out,'sha256':sha(log)});save();print(label,process.returncode,text[-3500:],flush=True)
 if timed_out:R['status']='TIMEOUT';R['active_command']=label;save();raise TimeoutError(label)
 class Outcome:pass
 result=Outcome();result.returncode=process.returncode;result.stdout=text;return result

def source_identity(label):
 assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=S,text=True).strip()==HEAD
 entries={}
 for record in subprocess.check_output(['git','ls-tree','-rz',HEAD],cwd=S).split(b'\0'):
  if not record:continue
  meta,name=record.split(b'\t',1);mode,kind,oid=meta.decode().split();assert kind=='blob';name=name.decode();p=S/name
  if mode=='120000':
   expected=subprocess.check_output(['git','cat-file','blob',oid],cwd=S)
   data=os.readlink(p).replace('\\','/').encode() if p.is_symlink() else p.read_bytes();assert data==expected,name
  else:
   assert not p.is_symlink(),name
   data=p.read_bytes();assert hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()==oid,name
  entries[name]={'mode':mode,'blob':oid,'working_sha256':hashlib.sha256(data).hexdigest()}
 (E/(label+'-source.json')).write_text(json.dumps(entries,indent=2)+'\n');R[label+'_source_entries']=len(entries);save();return entries
try:
 before=source_identity('before');R['ci_head']=os.environ.get('GITHUB_SHA');R['runner_sha256']=sha(P/'runner.py');(E/'profile-reference.json').write_bytes((P/'profile-reference.json').read_bytes());save()
 # Match critical definitions/ABI/shim settings from the existing real CMake command.
 definitions=['NOMINMAX','UNICODE','WIN32_LEAN_AND_MEAN','_CRT_SECURE_NO_WARNINGS','_SILENCE_CXX17_CODECVT_HEADER_DEPRECATION_WARNING','_UNICODE','_WIN32_IE=0x0A00','_WIN32_WINNT=0x0A00','WIN32','_WINDOWS']
 common=['/nologo','/TP','/std:c++20','/O2','/MT','/EHsc','/Gy','/Gw','/W3','/utf-8','/Zc:preprocessor','/Zc:__cplusplus','/sdl']+['/D'+x for x in definitions]+['/FI'+str(S/'src/compat/mingw/posix_extra.h')]+['/I'+str(S/x) for x in ['src/compat/msvc','src/compat/mingw','src','src/univalue/include','src/libbitcoinpqc/include']]
 R['profile_omissions']='No root-generated schema macros, OpenSSL include, or OpenMP flag: unused by tested LAN component paths. No rootCMake/fullproject claim.'
 for compiler in ['cl','clang-cl']:
  out=E/compiler;out.mkdir(exist_ok=True);run(compiler+'-version',[compiler,'/Bv' if compiler=='cl' else '--version'],20)
  objects=[]
  for label,file in [('discovery',S/'src/modelnet/native_discovery.cpp'),('nat',S/'src/modelnet/model_nat.cpp'),('fixture',P/'lan_native.cpp')]:
   obj=out/(label+'.obj');p=run(compiler+'-'+label,[compiler,*common,'/c',str(file),'/Fo'+str(obj)])
   if p.returncode: R['status']='NATIVE_COMPILE_BLOCKED';R['first_failed_stage']=compiler+'-'+label;save();raise SystemExit(1)
   objects.append(obj)
  exe=out/'lan-native.exe';p=run(compiler+'-link',[compiler,'/nologo','/MT',*map(str,objects),'/Fe'+str(exe),'/link','/OPT:REF','/INCREMENTAL:NO','ws2_32.lib','iphlpapi.lib','bcrypt.lib','userenv.lib','advapi32.lib','ole32.lib'])
  if p.returncode:R['status']='COMPONENT_LINK_BLOCKED';R['first_failed_stage']=compiler+'-link';save();raise SystemExit(1)
  p=run(compiler+'-runtime',[str(exe)],20);R['results'][compiler]={'rc':p.returncode,'exe_sha256':sha(exe),'objects':{x.name:sha(x) for x in objects},'runtime_pass':p.returncode==0}
  if p.returncode:R['status']='RUNTIME_ENVIRONMENT_LIMIT' if p.returncode==77 else 'RUNTIME_NOT_QUALIFIED';R['first_failed_stage']=compiler+'-runtime';save();raise SystemExit(1)
 after=source_identity('after');assert before==after
 R['status']='PASS_NATIVE_COMPONENT_AND_VALID_DISCOVERY';R['harness_sha256']=sha(P/'lan_native.cpp');R['logs']={x.name:sha(x) for x in E.glob('*.log')};save()
except BaseException as exc:
 if R['status']=='IN_PROGRESS':R['status']='ERROR'
 R['error']=str(exc);save();raise

finally:
 if 'before' in globals():
  try:
   final=source_identity('after-finally');R['source_unchanged_verified']=final==before;R['no_product_edits']=final==before
   if final!=before:raise RuntimeError('Source changed during qualification')
  except BaseException as guard_error:
   R['source_guard_error']=str(guard_error);R['status']='SOURCE_IDENTITY_ERROR';save();raise
 R['harness_sha256']=sha(P/'lan_native.cpp');R['logs']={x.name:sha(x) for x in E.glob('*.log')};save()
