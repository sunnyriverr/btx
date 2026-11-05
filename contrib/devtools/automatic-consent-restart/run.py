"""Bounded fork-only acquisition/policy test; product unchanged, fixture reuses maintained tests."""
from pathlib import Path
import hashlib,json,os,platform,shutil,signal,stat,subprocess,sys,tarfile,threading,time,urllib.request
BASE='666673a3153225ba264c7870e0e82e354df86765'; SSLVER='3.5.9'; SSLHASH='603f5602e2eef00d77fbd429d34dcd5822bb301757a1bc9cdb24c670f1eb859a'
WORK=Path(os.environ['GITHUB_WORKSPACE']).resolve();PRODUCT=WORK/'consent-product';OUT=WORK/'consent-results';OUT.mkdir(exist_ok=True)
TASK=WORK/'consent-native';BUILD=TASK/'build';PREFIX=TASK/'openssl';RUNTIME=WORK/'consent-runtime';FLOOR=2*1024**3
STATEFILE=OUT/'state.json';STATE=json.loads(STATEFILE.read_text()) if STATEFILE.exists() else {'base':BASE,'commands':[],'errors':[],'phases':{}}
ENV=dict(os.environ,CC='gcc-13',CXX='g++-13',BTX_OPENSSL=str(PREFIX/'bin/openssl'),PKG_CONFIG_PATH=str(PREFIX/'lib/pkgconfig'),PYTHONPATH=str(PRODUCT/'test/functional'),CCACHE_DIR=str(TASK/'ccache'),CCACHE_BASEDIR=str(WORK),CCACHE_COMPILERCHECK='content',CCACHE_MAXSIZE='700M')
NAMES=['btxd','btx-modeld','btx-guardd','btx-cli']
def save():STATEFILE.write_text(json.dumps(STATE,indent=2)+'\n')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def command(args,label,cwd=None,timeout=300):
 print('START',label,flush=True);t=time.monotonic();stop=None
 with (OUT/(label+'.log')).open('wb') as f:
  p=subprocess.Popen([str(x) for x in args],cwd=cwd,env=ENV,stdout=f,stderr=subprocess.STDOUT,start_new_session=True)
  last_report=time.monotonic()
  while p.poll() is None:
   if time.monotonic()-t>timeout:stop='phase timeout'
   elif shutil.disk_usage(OUT).free<FLOOR:stop='runner free space below2GiB'
   if stop:
    try:os.killpg(p.pid,signal.SIGTERM)
    except ProcessLookupError:pass
    try:p.wait(timeout=15)
    except subprocess.TimeoutExpired:
     try:os.killpg(p.pid,signal.SIGKILL)
     except ProcessLookupError:pass
     p.wait(timeout=10)
    break
   if time.monotonic()-last_report>=20:
    f.flush();tail=(OUT/(label+'.log')).read_text(errors='replace').splitlines();print(label+': '+(tail[-1] if tail else 'running'),flush=True);last_report=time.monotonic()
   time.sleep(1)
 STATE['commands'].append({'label':label,'args':[str(x) for x in args],'cwd':str(cwd),'returncode':p.returncode,'seconds':round(time.monotonic()-t,2),'stop':stop,'log':label+'.log'});save();print('END',label,p.returncode,stop,flush=True)
 if p.returncode or stop:raise RuntimeError(label+': '+str(p.returncode)+' '+str(stop))
 return OUT/(label+'.log')
def audit(label):
 head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=PRODUCT,text=True).strip();assert head==BASE
 raw=subprocess.check_output(['git','ls-tree','-r','-z',BASE],cwd=PRODUCT);rows={};bad=[]
 for entry in raw.split(b'\0'):
  if not entry:continue
  meta,name=entry.split(b'\t',1);mode,kind,blob=meta.decode().split();name=os.fsdecode(name);p=PRODUCT/name;assert kind=='blob','Unexpected submodule'
  b=os.fsencode(os.readlink(p)) if mode=='120000' else p.read_bytes();actual=hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest();rows[name]={'blob':blob,'actual_blob':actual,'sha256':hashlib.sha256(b).hexdigest(),'bytes':len(b),'mode':mode}
  actual_mode='120000' if p.is_symlink() else ('100755' if stat.S_ISREG(p.lstat().st_mode) and p.lstat().st_mode & 0o111 else '100644' if stat.S_ISREG(p.lstat().st_mode) else 'invalid')
  rows[name]['actual_mode']=actual_mode
  if actual!=blob or actual_mode!=mode:bad.append(name)
 dest=OUT/('source-'+label+'.json');dest.write_text(json.dumps({'head':head,'files':rows,'mismatches':bad},indent=2)+'\n');assert not bad,'Tracked source differs: '+str(bad[:10]);STATE['source_'+label]={'head':head,'files':len(rows),'manifest_sha256':sha(dest)};save()
def owned_processes():
 rows=[]
 for p in Path('/proc').iterdir():
  if not p.name.isdigit():continue
  try:
   exe=Path(os.readlink(p/'exe'))
   if exe.parent!=BUILD/'bin' or exe.name not in NAMES:continue
   st=(p/'stat').read_text().rsplit(')',1)[1].split();rows.append({'pid':int(p.name),'exe':str(exe),'start_ticks':st[19],'ppid':int(st[1])})
  except (FileNotFoundError,ProcessLookupError,PermissionError):pass
 return rows
def identity_matches(row):return any(x['pid']==row['pid'] and x['start_ticks']==row['start_ticks'] and x['exe']==row['exe'] for x in owned_processes())
def monitor(stop):
 seen={}
 while not stop.wait(.2):
  for row in owned_processes():seen[(row['pid'],row['start_ticks'])]=row
  (OUT/'observed-owned-processes.json').write_text(json.dumps(list(seen.values()),indent=2)+'\n')
def collect_logs():
 if RUNTIME.is_dir():
  for p in RUNTIME.rglob('*'):
   if p.is_file() and p.name in ['test_framework.log','debug.log'] and p.stat().st_size<=10*1024**2:
    dest=OUT/'functional-logs'/p.relative_to(RUNTIME);dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,dest)
def preflight():
 assert platform.system()=='Linux' and platform.machine()=='x86_64';assert shutil.disk_usage(OUT).free>=10*1024**3,'Need10GiB free before dependency setup';TASK.mkdir(exist_ok=True)
 command(['python3',WORK/'contrib/devtools/automatic-consent-restart/feature_swarm_consent_restart.py','--help'],'fixture-cli-preflight',timeout=30)
 STATE['runner']={'platform':platform.platform(),'uname':list(platform.uname()),'free_bytes':shutil.disk_usage(OUT).free,'cpu':os.cpu_count(),'meminfo':Path('/proc/meminfo').read_text(),'run_id':os.environ['GITHUB_RUN_ID'],'fixture_head':os.environ['GITHUB_SHA']};save();audit('before')
 for label,args in [('cmake-version',['cmake','--version']),('python-version',['python3','--version']),('gcc-version',['g++-13','--version'])]:command(args,label,timeout=30)
def dependencies():
 command(['sudo','apt-get','update'],'apt-update',timeout=300)
 command(['sudo','apt-get','install','-y','--no-install-recommends','build-essential','gcc-13','g++-13','cmake','ninja-build','pkgconf','python3','libevent-dev','libboost-dev','libsqlite3-dev','libzmq3-dev','ccache'],'apt-install',timeout=600)
 command(['dpkg-query','-W','gcc-13','g++-13','cmake','ninja-build','python3','libevent-dev','libboost-dev','libsqlite3-dev','libzmq3-dev','ccache'],'dependency-versions',timeout=30)
def openssl():
 inputs={'source':SSLHASH,'compiler':sha(Path(shutil.which('gcc-13')).resolve()),'glibc':subprocess.check_output(['getconf','GNU_LIBC_VERSION'],text=True).strip(),'profile':'linux-x86_64 no-shared no-tests no-docs -fPIC'}
 if (PREFIX/'inputs.json').is_file():
  prior=json.loads((PREFIX/'inputs.json').read_text())
  if prior['inputs']==inputs and all((PREFIX/k).is_file() and sha(PREFIX/k)==v for k,v in prior['files'].items()):
   STATE['openssl']={'version':SSLVER,'source_sha256':SSLHASH,'cache_verified':True,'prefix':str(PREFIX),'files':prior['files']};save();command([PREFIX/'bin/openssl','version','-a'],'openssl-version',timeout=30);return
  shutil.rmtree(PREFIX) # Only this task-owned restored prefix; never a peer cache.
 archive=TASK/('openssl-'+SSLVER+'.tar.gz');url='https://github.com/openssl/openssl/releases/download/openssl-'+SSLVER+'/'+archive.name
 with urllib.request.urlopen(url,timeout=90) as z,archive.open('wb') as f:shutil.copyfileobj(z,f)
 assert sha(archive)==SSLHASH,'OpenSSL digest mismatch'
 with tarfile.open(archive) as tar:
  members=tar.getmembers();assert sum(x.size for x in members)<1024**3;assert all(not Path(x.name).is_absolute() and '..' not in Path(x.name).parts for x in members);tar.extractall(TASK,filter='data')
 src=TASK/('openssl-'+SSLVER);command(['perl','Configure','linux-x86_64','--prefix='+str(PREFIX),'--libdir=lib','no-shared','no-tests','no-docs','-fPIC'],'openssl-configure',src)
 command(['make','-j2'],'openssl-build',src,900);command(['make','install_sw'],'openssl-install',src,180)
 command([PREFIX/'bin/openssl','version','-a'],'openssl-version',timeout=30);kem=command([PREFIX/'bin/openssl','list','-kem-algorithms'],'openssl-kem',timeout=30);sig=command([PREFIX/'bin/openssl','list','-signature-algorithms'],'openssl-signatures',timeout=30);assert 'ML-KEM-768' in kem.read_text() and 'ML-DSA-44' in sig.read_text()
 STATE['openssl']={'version':SSLVER,'source_sha256':SSLHASH,'prefix':str(PREFIX),'files':{str(p.relative_to(PREFIX)):sha(p) for p in [PREFIX/'bin/openssl',PREFIX/'lib/libssl.a',PREFIX/'lib/libcrypto.a',PREFIX/'include/openssl/opensslv.h']}};save();(PREFIX/'inputs.json').write_text(json.dumps({'inputs':inputs,'files':STATE['openssl']['files']},indent=2)+'\n');shutil.rmtree(src);archive.unlink()
def configure():
 args=['cmake','-S',PRODUCT,'-B',BUILD,'-G','Ninja','-DCMAKE_BUILD_TYPE=Release','-DCMAKE_C_COMPILER=gcc-13','-DCMAKE_CXX_COMPILER=g++-13','-DCMAKE_EXPORT_COMPILE_COMMANDS=ON','-DCMAKE_C_FLAGS_RELEASE=-O1 -DNDEBUG','-DCMAKE_CXX_FLAGS_RELEASE=-O1 -DNDEBUG','-DBUILD_DAEMON=ON','-DBUILD_CLI=ON','-DBUILD_UTIL=ON','-DWITH_MODELNET=ON','-DBUILD_GUI=OFF','-DENABLE_WALLET=OFF','-DBUILD_TESTS=OFF','-DBUILD_BENCH=OFF','-DBUILD_TX=OFF','-DBUILD_FUZZ_BINARY=OFF','-DWITH_CCACHE=ON','-DCMAKE_C_COMPILER_LAUNCHER=ccache','-DCMAKE_CXX_COMPILER_LAUNCHER=ccache','-DWITH_SQLITE=ON','-DWITH_ZMQ=ON','-DOPENSSL_USE_STATIC_LIBS=ON','-DOPENSSL_ROOT_DIR='+str(PREFIX),'-DOPENSSL_INCLUDE_DIR='+str(PREFIX/'include'),'-DOPENSSL_SSL_LIBRARY='+str(PREFIX/'lib/libssl.a'),'-DOPENSSL_CRYPTO_LIBRARY='+str(PREFIX/'lib/libcrypto.a')]
 command(args,'root-configure',timeout=180)
 for n in ['CMakeCache.txt','build.ninja','compile_commands.json']:
  if (BUILD/n).is_file():shutil.copyfile(BUILD/n,OUT/n)
 assert (BUILD/'test/config.ini').is_file();shutil.copyfile(BUILD/'test/config.ini',OUT/'functional-config.ini');command(['ninja','-C',BUILD,'-n',*NAMES],'root-build-plan',timeout=30)
def build():
 command(['cmake','--build',BUILD,'--target',*NAMES,'--parallel','2'],'root-build',timeout=2400)
 STATE['binaries']={n:{'path':str(BUILD/'bin'/n),'sha256':sha(BUILD/'bin'/n),'bytes':(BUILD/'bin'/n).stat().st_size} for n in NAMES};save()
 for n in NAMES:command(['ldd',BUILD/'bin'/n],'ldd-'+n,timeout=30)
 command(['ccache','--show-stats'],'ccache-stats',timeout=30);audit('after-build')
def test():
 assert not RUNTIME.exists() and not owned_processes()
 target=WORK/'contrib/devtools/automatic-consent-restart/feature_swarm_consent_restart.py'
 STATE['test_identity']={'sha256':sha(target),'fixture':str(target),'runtime':str(RUNTIME),'product_changes':False,'repeat':1};save()
 stop=threading.Event();m=threading.Thread(target=monitor,args=(stop,),daemon=True);m.start()
 try:command(['python3',target,'--configfile='+str(BUILD/'test/config.ini'),'--tmpdir='+str(RUNTIME),'--portseed=41725','--nocleanup','--result-json='+str(OUT/'consent-observations.json')],'consent-test',timeout=420)
 finally:stop.set();m.join(timeout=3);collect_logs()
 assert 'Tests successful' in (OUT/'consent-test.log').read_text(errors='replace'),'Zero exit without framework success marker'
 STATE['maintained_test_pass']=True;save();audit('after-test')
def finalize():
 collect_logs();before=owned_processes();actions=[]
 for rows,sig,wait in [([x for x in before if Path(x['exe']).name=='btxd'],signal.SIGTERM,15),(before,signal.SIGTERM,10),(before,signal.SIGKILL,3)]:
  for row in rows:
   if identity_matches(row):
    try:os.kill(row['pid'],sig);actions.append({**row,'signal':sig.value})
    except ProcessLookupError:pass
  end=time.monotonic()+wait
  while owned_processes() and time.monotonic()<end:time.sleep(.25)
  if not owned_processes():break
 remaining=owned_processes();STATE['cleanup']={'before':before,'signals':actions,'remaining':remaining,'owned_runtime_removed':False}
 if RUNTIME.exists() and not remaining:shutil.rmtree(RUNTIME);STATE['cleanup']['owned_runtime_removed']=True
 try:audit('final')
 except Exception as e:STATE['errors'].append('final source audit: '+str(e))
 STATE['final_free_bytes']=shutil.disk_usage(OUT).free;STATE['qualification_pass']=bool(STATE.get('maintained_test_pass') and STATE['phases'].get('build')=='pass' and STATE.get('source_final') and not before and not actions and not remaining and not STATE['errors']);save();(OUT/'result.json').write_text(json.dumps(STATE,indent=2)+'\n');assert not remaining,'Owned processes remain';print(json.dumps({'qualification_pass':STATE['qualification_pass'],'phases':STATE['phases'],'errors':STATE['errors'],'cleanup':STATE['cleanup']},indent=2),flush=True);assert STATE['qualification_pass'],'Qualification incomplete or failed; see retained result'
phase=sys.argv[1]
try:globals()[phase]();STATE['phases'][phase]='pass';save()
except Exception as e:STATE['phases'][phase]='fail';STATE['errors'].append(phase+': '+str(e));save();print('FAILED',phase,repr(e),flush=True);raise
