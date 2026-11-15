from pathlib import Path
import subprocess,os,json,hashlib,shutil,time,re,sys,urllib.request
R=Path('D:/btx-native-035');B=R/'project-build';S=Path(os.environ['GITHUB_WORKSPACE'])/'btx';E=R/'unit-plan-evidence';E.mkdir(parents=True,exist_ok=True)
result={'source':'61f13b8870ed98c7b10db2e32c04fb647023f4ef','product_compilation':False,'tests_run':False,'cache_saved':False}
def save():(E/'result.json').write_text(json.dumps(result,indent=2)+'\n')
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def run(name,args,cwd=S,limit=180):
 st=time.monotonic();p=subprocess.run(args,cwd=cwd,capture_output=True,timeout=limit);(E/(name+'.log')).write_bytes(p.stdout+p.stderr);result.setdefault('commands',[]).append({'name':name,'exit':p.returncode,'seconds':round(time.monotonic()-st,2)});save();print(name,p.returncode,flush=True);p.check_returncode();return p.stdout.decode(errors='replace')+p.stderr.decode(errors='replace')
try:
 assert shutil.disk_usage(R).free>8*1024**3
 assert sha(B/'btx-successor.json')=='0e1977306facc7112a3b665e70f583c605d419f105cea36d443c0ba706c2f8fc';cp=json.loads((B/'btx-successor.json').read_text());assert cp['source']==result['source'] and cp['build_result']['status']=='UNIT_BUILD_INCOMPLETE'
 assert run('head',['git','rev-parse','HEAD']).strip()==result['source']
 clang=run('compiler',['clang-cl','--version']);cmake=run('cmake',['cmake','--version']);ninja=run('ninja',['ninja','--version']);assert '20.1.8' in clang and '4.4.5' in cmake and '1.13.2' in ninja
 assert os.environ['VCToolsVersion'].rstrip('\\')=='14.51.36231';result['sdk']=os.environ.get('WindowsSDKVersion');result['toolset']=os.environ['VCToolsVersion']
 for n,info in cp['files'].items():assert sha(R/n)==info['sha256'],n
 for n,info in cp['source_files'].items():
  p=S/n;assert sha(p)==info['sha256'],n;os.utime(p,ns=(p.stat().st_atime_ns,info['mtime_ns']))
 result['verified_files']=len(cp['files']);result['verified_objects']=sum(n.endswith('.obj') for n in cp['files']);oldcmd=json.loads((B/'compile_commands.json').read_text());shutil.copy2(B/'CMakeCache.txt',E/'before-CMakeCache.txt')
 # Tool inputs only; no bootstrap/dependency compilation allowed.
 V=R/'vcpkg';run('vcpkg-clone',['git','clone','--no-checkout','https://github.com/microsoft/vcpkg.git',str(V)],cwd=R,limit=300);run('vcpkg-checkout',['git','-C',str(V),'checkout','--detach','afa249f12f52ed8a3b919f195495ba8b330288d1'],cwd=R)
 req=urllib.request.Request('https://api.github.com/repos/microsoft/vcpkg-tool/releases/assets/690264732',headers={'Accept':'application/octet-stream','User-Agent':'BTX-preflight','Authorization':'Bearer '+os.environ['GH_TOKEN']})
 # Strip credentials on cross-origin asset redirects.
 class Redirect(urllib.request.HTTPRedirectHandler):
  def redirect_request(self,req,fp,code,msg,headers,url):
   q=super().redirect_request(req,fp,code,msg,headers,url)
   if q and urllib.parse.urlparse(url).netloc!='api.github.com':q.remove_header('Authorization')
   return q
 with urllib.request.build_opener(Redirect).open(req,timeout=90) as f:data=f.read(10*1024**2)
 assert hashlib.sha256(data).hexdigest()=='191ee64b0887af80aad3eff6c5e888ab733d3ef2182885ed4747b4574c201834';(V/'vcpkg.exe').write_bytes(data);(V/'vcpkg.disable-metrics').write_text('')
 assert (R/'openssl-3.5.4-static/btx-build-provenance.json').is_file(),'Verified OpenSSL cache missing'
 result['openssl_receipt']=json.loads((R/'openssl-3.5.4-static/btx-build-provenance.json').read_text())
 run('python-dependencies',[sys.executable,'-I','-c','import cryptography,sqlite3;from cryptography.hazmat.primitives.ciphers.aead import AESGCM;print(cryptography.__version__)'])
 os.environ.update(VCPKG_ROOT=str(V),VCPKG_DISABLE_METRICS='1',VCPKG_BINARY_SOURCES='clear;files,'+str(R/'binary-cache')+',read')
 args=['cmake','--preset','windows-clangcl-static','-S',str(S),'-B',str(B),'-DBUILD_TESTS=ON','-DBUILD_GUI=OFF','-DWITH_MODELNET=ON','-DENABLE_WALLET=ON','-DWITH_ZMQ=ON','-DVCPKG_MANIFEST_NO_DEFAULT_FEATURES=ON','-DVCPKG_MANIFEST_FEATURES=wallet;tests;zeromq','-DVCPKG_INSTALLED_DIR='+str(R/'vcpkg-installed'),'-DVCPKG_INSTALL_OPTIONS=--only-binarycaching','-DOPENSSL_ROOT_DIR='+str(R/'openssl-3.5.4-static'),'-DOPENSSL_USE_STATIC_LIBS=ON','-DOPENSSL_MSVC_STATIC_RT=ON','-DOPENSSL_INCLUDE_DIR='+str(R/'openssl-3.5.4-static/include'),'-DOPENSSL_SSL_LIBRARY='+str(R/'openssl-3.5.4-static/lib/libssl.lib'),'-DOPENSSL_CRYPTO_LIBRARY='+str(R/'openssl-3.5.4-static/lib/libcrypto.lib'),'-DCMAKE_EXPORT_COMPILE_COMMANDS=ON','-DPython3_EXECUTABLE='+sys.executable]
 run('configure',args,limit=600)

 shutil.copy2(B/'CMakeCache.txt',E/'CMakeCache.txt');shutil.copy2(B/'compile_commands.json',E/'compile_commands.json')
 newcmd=json.loads((B/'compile_commands.json').read_text());a={x['output']:x for x in oldcmd};b={x['output']:x for x in newcmd};result['compile_commands']={'before':len(a),'after':len(b),'added':len(b.keys()-a.keys()),'changed':sum(a[k]!=b[k] for k in a.keys()&b.keys()),'removed':len(a.keys()-b.keys())}
 if (B/'CMakeFiles/VerifyGlobs.cmake').exists():run('verify-globs',['cmake','-P',str(B/'CMakeFiles/VerifyGlobs.cmake')],cwd=B)
 manifest=E/'plan.ninja';shutil.copy2(B/'build.ninja',manifest)
 entry=next(x for x in newcmd if x['file'].replace('\\','/').endswith('/modelnet/capability_ensure.cpp'));result['executed_generated_command']=entry
 original=S/'src/modelnet/capability_ensure.cpp';review=json.loads((Path(__file__).parent/'ensure-review.json').read_text());assert sha(original)==review['baseline_source_sha256'];candidate=Path(__file__).parent/'capability_ensure.fixed.cpp';assert sha(candidate)==review['candidate_source_sha256'];shutil.copyfile(candidate,original)
 st=time.monotonic();p=subprocess.run(entry['command'],cwd=entry['directory'],shell=True,capture_output=True,timeout=180);(E/'ensure-compile.log').write_bytes(p.stdout+p.stderr);result['object_exit']=p.returncode;result['object_seconds']=round(time.monotonic()-st,2);print((p.stdout+p.stderr).decode(errors='replace')[-1500:],flush=True);p.check_returncode()
 # Exact wrapper extracted from candidate; link against existing verified native security library.
 harness=Path(__file__).parent/'ensure-private-dir-controls.cpp';obj=E/'private-dir-controls.obj';exe=E/'private-dir-controls.exe'
 run('controls-compile',['clang-cl','/nologo','/std:c++20','/EHsc','/MT','/O2','/I'+str(S/'src'),'/I'+str(B/'src'),'/I'+str(S/'src/univalue/include'),'/I'+str(R/'vcpkg-installed/x64-windows-static/include'),'/c',str(harness),'/Fo'+str(obj)],cwd=B)
 import shlex
 ninja=(B/'build.ninja').read_text();block=ninja[ninja.index('build bin/btx-security.exe:'):];libs=next(l.split(' = ',1)[1] for l in block.splitlines() if l.startswith('  LINK_LIBRARIES = '));args=[x.strip('"') for x in shlex.split(libs,posix=False)]
 run('controls-link',['lld-link','/machine:x64','/subsystem:console','/OUT:'+str(exe),str(obj)]+args,cwd=B)
 run('controls-runtime',[str(exe),str(E/'native-private-dir-fixture')],cwd=B)
 for n,info in cp['files'].items():
  if n.endswith(('.obj','.exe','.lib')) and not n.replace('\\','/').endswith('/capability_ensure.cpp.obj'):assert sha(R/n)==info['sha256'],n
 result['unrelated_compiled_files_unchanged']=True;result['source_patch']='ensure-directory.patch';result['status']='ENSURE_CANDIDATE_PASS';result['product_compilation']=True
 (E/'build-result.json').write_text(json.dumps(result,indent=2))
except BaseException as e:result['status']='ENSURE_CHECK_FAILED';result['error']=repr(e);raise
finally:save()
