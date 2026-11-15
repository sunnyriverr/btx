from pathlib import Path
import subprocess,os,json,hashlib,shutil,time,re,sys,urllib.request
R=Path('D:/btx-native-035');B=R/'project-build';S=Path(os.environ['GITHUB_WORKSPACE'])/'btx';E=R/'preflight-evidence';E.mkdir(parents=True,exist_ok=True)
T='074dac167c26c1e091198f691ed5727817dba88a';OLD='dac9aee53520bd49ed320ec7a49b9072fc7d88d9'
result={'target':T,'compile_invoked':False,'tests_invoked':False,'cache_saved':False,'status':'STARTED'}
def save(): (E/'result.json').write_text(json.dumps(result,indent=2)+'\n')
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for x in iter(lambda:f.read(1048576),b''):h.update(x)
 return h.hexdigest()
def run(name,args,cwd=S,limit=180):
 st=time.monotonic();p=subprocess.run(args,cwd=cwd,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=limit);(E/(name+'.log')).write_bytes(p.stdout);result.setdefault('commands',[]).append({'name':name,'args':list(map(str,args)),'exit':p.returncode,'seconds':round(time.monotonic()-st,2)});save();print(name,p.returncode,p.stdout.decode(errors='replace')[-2000:],flush=True)
 if p.returncode:raise RuntimeError(name+' failed')
 return p.stdout.decode(errors='replace')
try:
 assert shutil.disk_usage(R).free>8*1024**3,'Require8GiB free after restore'
 marker=B/'btx-checkpoint.json';assert sha(marker)=='2482100da1abb82abda529df0223f815ee8f498fd8cfb470f0803f865db4bdec','Wrong stock checkpoint'
 cp=json.loads(marker.read_text());result['saved_profile']=cp['profile'];result['source']=run('source-head',['git','rev-parse','HEAD']).strip();assert result['source']==OLD
 clang=run('compiler',['clang-cl','--version']);cmake=run('cmake',['cmake','--version']);ninja=run('ninja',['ninja','--version']);result['toolset']=os.environ.get('VCToolsVersion');result['sdk']=os.environ.get('WindowsSDKVersion');save()
 assert '20.1.8' in clang and result['toolset'].rstrip('\\')=='14.51.36231','Native compiler/toolset changed; refuse assumed object reuse'
 assert '4.4.5' in cmake and '1.13.2' in ninja,'Build tools changed; quantify separately'
 # Verify every checkpoint file before touching the ephemeral restored tree.
 for name,info in cp['files'].items():
  p=R/name;assert p.is_relative_to(R) and '..' not in p.parts;assert p.is_file() and sha(p)==info['sha256'],name
 result['verified_checkpoint_files']=len(cp['files']);result['verified_objects']=sum(n.endswith('.obj') for n in cp['files']);save()
 # Old source bytes/timestamps must match before switch; unchanged files alone retain those timestamps.
 for name,stamp in cp['source_mtimes'].items():
  p=S/name;info=cp['source_catalog']['files'][name]
  if p.is_symlink():continue
  assert sha(p)==info['working_sha256'],name;os.utime(p,ns=(p.stat().st_atime_ns,stamp))
 oldcmd=json.loads((B/'compile_commands.json').read_text());shutil.copyfile(B/'CMakeCache.txt',E/'old-CMakeCache.txt')
 run('fetch',['git','fetch','--no-tags','--depth=1','https://github.com/btxchain/btx.git',T]);run('checkout',['git','checkout','--detach',T])
 restored=0
 for name,stamp in cp['source_mtimes'].items():
  p=S/name;info=cp['source_catalog']['files'][name]
  if p.is_file() and not p.is_symlink() and info.get('working_sha256')==sha(p):os.utime(p,ns=(p.stat().st_atime_ns,stamp));restored+=1
 result['unchanged_source_timestamps_restored']=restored
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
 args=['cmake','--preset','windows-clangcl-static','-S',str(S),'-B',str(B),'-DBUILD_TESTS=OFF','-DBUILD_GUI=OFF','-DWITH_MODELNET=ON','-DENABLE_WALLET=ON','-DWITH_ZMQ=ON','-DVCPKG_MANIFEST_NO_DEFAULT_FEATURES=ON','-DVCPKG_MANIFEST_FEATURES=wallet;tests;zeromq','-DVCPKG_INSTALLED_DIR='+str(R/'vcpkg-installed'),'-DVCPKG_INSTALL_OPTIONS=--only-binarycaching','-DOPENSSL_ROOT_DIR='+str(R/'openssl-3.5.4-static'),'-DOPENSSL_USE_STATIC_LIBS=ON','-DOPENSSL_MSVC_STATIC_RT=ON','-DOPENSSL_INCLUDE_DIR='+str(R/'openssl-3.5.4-static/include'),'-DOPENSSL_SSL_LIBRARY='+str(R/'openssl-3.5.4-static/lib/libssl.lib'),'-DOPENSSL_CRYPTO_LIBRARY='+str(R/'openssl-3.5.4-static/lib/libcrypto.lib'),'-DCMAKE_EXPORT_COMPILE_COMMANDS=ON','-DPython3_EXECUTABLE='+sys.executable]
 run('configure',args,limit=600)
 newcmd=json.loads((B/'compile_commands.json').read_text());old={x['output']:x for x in oldcmd};new={x['output']:x for x in newcmd};result['compile_commands']={'before':len(old),'after':len(new),'added':len(new.keys()-old.keys()),'removed':len(old.keys()-new.keys()),'changed':sum(old[k]!=new[k] for k in old.keys()&new.keys())};shutil.copyfile(B/'compile_commands.json',E/'compile_commands.json');shutil.copyfile(B/'CMakeCache.txt',E/'CMakeCache.txt')
 glob=B/'CMakeFiles/VerifyGlobs.cmake'
 if glob.exists():run('verify-globs',['cmake','-P',str(glob)],cwd=B)
 # Snapshot manifest: dry-run must not invoke build-system regeneration.
 manifest=E/'plan.ninja';shutil.copyfile(B/'build.ninja',manifest)
 targets=['btxd','btx-cli','btx-tx','btx-util','btx-open','btx-modeld','btx-guardd','btx-security'];out=run('ninja-dry-run',['ninja','-C',str(B),'-f',str(manifest),'-n','-d','explain']+targets,cwd=B)
 actions=[l for l in out.splitlines() if re.match(r'^\[\d+/\d+\]',l)];result['planned_actions']=actions;result['planned_steps']=len(actions);result['plan_counts']={k:sum(k in l for l in actions) for k in ['Building CXX object','Building C object','Linking CXX static library','Linking CXX executable','Generating']};result['regeneration_in_plan']=any('Re-running CMake' in l or 'Re-checking' in l for l in actions)
 for name,info in cp['files'].items():
  if name.endswith(('.obj','.exe','.lib')):assert sha(R/name)==info['sha256'],name
 result['objects_binaries_libraries_unchanged']=True;result['status']='CONFIGURED_DRY_RUN_COMPLETE'
except BaseException as e:result['status']='PREFLIGHT_BLOCKED';result['error']=repr(e);raise
finally:save()
