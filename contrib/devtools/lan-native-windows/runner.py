from pathlib import Path
import os,sys,json,subprocess,hashlib,time,platform
S=Path(os.environ['GITHUB_WORKSPACE'])/'source';P=Path(__file__).resolve().parent;E=Path(os.environ['RUNNER_TEMP'])/'lan400-native-evidence';E.mkdir(exist_ok=True)
HEAD='d6be75960231f2c28e0ae355c75232f71bef40b7';BASELINE='3acc3f74d92f646cf95cdcb8c4d92a7ec97afc9a';R={'head':HEAD,'status':'IN_PROGRESS','profile':'Native full component TUs, C++20/O2/staticCRT, actual Windows compatibility shim; direct compiler qualification, not root-target/fullhelper','compiler_env':{x:os.environ.get(x) for x in ['VCToolsVersion','WindowsSDKVersion','ImageVersion','PROCESSOR_ARCHITECTURE']},'commands':[],'platform':platform.platform(),'results':{},'no_product_edits':None}
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
 before=source_identity('before');R['ci_head']=os.environ.get('GITHUB_SHA');R['runner_sha256']=sha(P/'runner.py')
 R['profile']='Native MinGW GCC full discovery/NAT TUs, C++20/O2/static/function sections; component runtime only, not root or MSVC LINK'
 R['prior_msvc_compile_pair_run']=41776498958;save()
 (E/'profile-reference.json').write_bytes((P/'profile-reference.json').read_bytes())
 compiler=Path('C:/mingw64/bin/g++.exe');assert compiler.is_file(),'Preinstalled native MinGW unavailable'
 os.environ['PATH']=str(compiler.parent)+os.pathsep+os.environ['PATH']
 R['compiler_sha256']=sha(compiler)
 run('gcc-version',[str(compiler),'-v'],20)
 target=run('gcc-target',[str(compiler),'-dumpmachine'],20)
 assert target.returncode==0 and target.stdout.strip()=='x86_64-w64-mingw32'
 run('ld-version',['C:/mingw64/bin/ld.exe','--version'],20)
 common=['-std=c++20','-O2','-ffunction-sections','-fdata-sections','-static','-pthread']
 libraries=['-lws2_32','-liphlpapi','-lbcrypt','-luserenv','-ladvapi32','-lole32','-luuid']
 for mode in ['dead','live']:
  probe=P/('probe-'+mode+'.cpp');p=run('gc-probe-'+mode,[str(compiler),*common,str(probe),'-Wl,--gc-sections','-o',str(E/('gc-'+mode+'.exe'))])
  if mode=='dead':assert p.returncode==0,'Unused-dependency linker control failed'
  else:assert p.returncode!=0 and 'UnavailableProbeDependency' in p.stdout,'Reachable-dependency linker control failed'
 assert run('gc-probe-runtime',[str(E/'gc-dead.exe')],20).returncode==0
 definitions=['WIN32','_WINDOWS','NOMINMAX','UNICODE','WIN32_LEAN_AND_MEAN','_UNICODE','_WIN32_WINNT=0x0A00','_WIN32_IE=0x0A00']
 common+=['-D'+x for x in definitions]+['-include',str(S/'src/compat/mingw/posix_extra.h')]
 common+=['-I'+str(S/x) for x in ['src/compat/mingw','src','src/univalue/include','src/libbitcoinpqc/include']]
 objects=[]
 for label,file in [('discovery',S/'src/modelnet/native_discovery.cpp'),('nat',S/'src/modelnet/model_nat.cpp'),('fixture',P/'lan_native.cpp')]:
  obj=E/(label+'.obj');p=run('gcc-'+label,[str(compiler),*common,'-c',str(file),'-o',str(obj)])
  if p.returncode:R['status']='NATIVE_COMPILE_BLOCKED';R['first_failed_stage']='gcc-'+label;save();raise SystemExit(1)
  objects.append(obj)
 exe=E/'lan-native.exe'
 p=run('gcc-link',[str(compiler),'-static','-pthread','-Wl,--gc-sections','-Wl,-Map,'+str(E/'component.map'),*map(str,objects),*libraries,'-o',str(exe)])
 if p.returncode:R['status']='COMPONENT_LINK_BLOCKED';R['first_failed_stage']='gcc-link';save();raise SystemExit(1)
 p=run('gcc-runtime',[str(exe)],20)
 R['results']['gcc']={'rc':p.returncode,'exe_sha256':sha(exe),'objects':{x.name:sha(x) for x in objects},'runtime_pass':p.returncode==0}
 if p.returncode:R['status']='RUNTIME_ENVIRONMENT_LIMIT' if p.returncode==77 else 'RUNTIME_NOT_QUALIFIED';R['first_failed_stage']='gcc-runtime';save();raise SystemExit(1)
 assert source_identity('after')==before
 R['status']='PASS_NATIVE_MINGW_COMPONENT_AND_VALID_DISCOVERY';save()
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
