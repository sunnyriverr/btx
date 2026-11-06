"""Bounded fork-only supplied-parent PSBT acceptance; unchanged wallet-enabled product."""
from pathlib import Path
import configparser,hashlib,json,os,platform,shutil,signal,stat,subprocess,sys,tarfile,threading,time,urllib.request
BASE='666673a3153225ba264c7870e0e82e354df86765'; SSLVER='3.5.9'; SSLHASH='603f5602e2eef00d77fbd429d34dcd5822bb301757a1bc9cdb24c670f1eb859a'
WORK=Path(os.environ['GITHUB_WORKSPACE']).resolve();PRODUCT=WORK/'p2mr-parent-product';OUT=WORK/'generate-cli-results';OUT.mkdir(exist_ok=True)
TASK=WORK/'p2mr-parent-native';BUILD=TASK/'build';PREFIX=TASK/'openssl';RUNTIME=WORK/'generate-cli-runtime';FLOOR=2*1024**3
STATEFILE=OUT/'state.json';STATE=json.loads(STATEFILE.read_text()) if STATEFILE.exists() else {'base':BASE,'commands':[],'errors':[],'phases':{}}
ENV=dict(os.environ,CC='gcc-13',CXX='g++-13',BTX_OPENSSL=str(PREFIX/'bin/openssl'),PKG_CONFIG_PATH=str(PREFIX/'lib/pkgconfig'),PYTHONPATH=str(PRODUCT/'test/functional'),CCACHE_DIR=str(TASK/'ccache'),CCACHE_BASEDIR=str(WORK),CCACHE_COMPILERCHECK='content',CCACHE_MAXSIZE='700M')
NAMES=['btxd','btx-cli','btx-modeld']
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

HERE=WORK/'contrib/devtools/generate-cli'
EXPECTED=json.loads((HERE/'expected-inputs.json').read_text())

def preflight():
 assert platform.system()=='Linux' and platform.machine()=='x86_64'
 assert shutil.disk_usage(OUT).free>8*1024**3
 STATE['runner']={'platform':platform.platform(),'run_id':os.environ['GITHUB_RUN_ID'],'fixture_head':os.environ['GITHUB_SHA']}
 save();audit('before')

def dependencies():
 command(['sudo','apt-get','-o','Acquire::http::Timeout=30','-o','Acquire::https::Timeout=30','-o','Acquire::Retries=1','update'],'apt-update',timeout=240)
 command(['sudo','apt-get','-o','Acquire::http::Timeout=30','-o','Acquire::https::Timeout=30','-o','Acquire::Retries=1','install','-y','--no-install-recommends','g++-13','ninja-build','pkgconf','libevent-dev','libboost-dev','libsqlite3-dev','libzmq3-dev','ccache'],'apt-install',timeout=420)
 for label,args in [('gcc-version',['g++-13','--version']),('cmake-version',['cmake','--version']),('dependency-versions',['dpkg-query','-W','g++-13','libboost-dev','libevent-dev','libsqlite3-dev','libzmq3-dev','ninja-build','ccache'])]:command(args,label,timeout=30)

def build():
 # Fail closed on cache miss or changed binaries: no fallback full rebuild.
 for n,expected in EXPECTED['binaries'].items():
  assert sha(BUILD/'bin'/n)==expected['sha256'], 'Restored binary differs: '+n
 for name,want in EXPECTED['openssl']['files'].items():assert sha(PREFIX/name)==want, 'OpenSSL cache differs'
 STATE['restored_binaries']=EXPECTED['binaries'];STATE['retained_cache_id']=EXPECTED['cache_id'];save()
 cache=(BUILD/'CMakeCache.txt').read_text()
 for wanted in ['ENABLE_WALLET:BOOL=ON','WITH_MODELNET:BOOL=ON','CMAKE_CXX_FLAGS_RELEASE:STRING=-O1 -DNDEBUG']:
  assert wanted in cache,wanted
 command(['ldd',BUILD/'bin/btxd'],'ldd-node',timeout=30)
 command(['ldd',BUILD/'bin/btx-cli'],'ldd-cli',timeout=30)
 # Source bytes/modes have already been checked. A fresh checkout's timestamps
 # must not force all retained objects to rebuild from identical inputs.
 raw=subprocess.check_output(['git','ls-tree','-r','--name-only','-z',BASE],cwd=PRODUCT)
 for name in raw.split(b'\0'):
  if name:os.utime(PRODUCT/os.fsdecode(name),(1700000000,1700000000),follow_symlinks=False)
 command(['cmake','-S',PRODUCT,'-B',BUILD],'cached-configure',timeout=120)
 plan=command(['ninja','-C',BUILD,'-n','btx-modeld'],'helper-build-plan',timeout=60).read_text()
 steps=[line for line in plan.splitlines() if line.startswith('[')]
 STATE['planned_helper_steps']=steps;save()
 assert len(steps)<=12, 'Unexpected rebuild footprint; stop before expensive work'
 command(['cmake','--build',BUILD,'--target','btx-modeld','--parallel','2'],'helper-target-build',timeout=240)
 for n,expected in EXPECTED['binaries'].items():assert sha(BUILD/'bin'/n)==expected['sha256']
 STATE['binaries']={n:{'sha256':sha(BUILD/'bin'/n),'bytes':(BUILD/'bin'/n).stat().st_size} for n in NAMES}
 shutil.copyfile(BUILD/'CMakeCache.txt',OUT/'CMakeCache.txt')
 shutil.copyfile(BUILD/'test/config.ini',OUT/'functional-config.ini')
 save();audit('after-build')

def test():
 assert not RUNTIME.exists() and not owned_processes()
 RUNTIME.mkdir(mode=0o700)
 ENV['GENERATE_RUNTIME']=str(RUNTIME);ENV['GENERATE_RESULTS']=str(OUT)
 STATE['fixture_sha256']=sha(HERE/'case.py');save()
 command(['python3',HERE/'case.py','--configfile='+str(BUILD/'test/config.ini'),'--tmpdir='+str(RUNTIME/'node-test'),'--cachedir='+str(RUNTIME/'chain-cache'),'--portseed=42325','--nocleanup'],'node-cli-object-comparison',timeout=180)
 collect_logs();STATE['workflow_pass']=True;save();audit('after-test')

def finalize():
 collect_logs();before=owned_processes();actions=[]
 for sig,wait in [(signal.SIGTERM,20),(signal.SIGKILL,3)]:
  for row in before:
   if identity_matches(row):
    os.kill(row['pid'],sig);actions.append({**row,'signal':sig.value})
  end=time.monotonic()+wait
  while owned_processes() and time.monotonic()<end:time.sleep(.2)
  if not owned_processes():break
 remaining=owned_processes();STATE['cleanup']={'before':before,'signals':actions,'remaining':remaining,'runtime_removed':False}
 if not remaining and RUNTIME.exists():shutil.rmtree(RUNTIME);STATE['cleanup']['runtime_removed']=True
 try:audit('final')
 except Exception as error:STATE['errors'].append(str(error))
 STATE['qualification_pass']=bool(STATE.get('workflow_pass') and not before and not actions and not remaining and not STATE['errors'])
 save();(OUT/'result.json').write_text(json.dumps(STATE,indent=2)+'\n');assert STATE['qualification_pass'], 'Incomplete observation; inspect retained result'

phase=sys.argv[1]
try:globals()[phase]();STATE['phases'][phase]='pass';save()
except Exception as error:STATE['phases'][phase]='fail';STATE['errors'].append(phase+': '+repr(error));save();raise
