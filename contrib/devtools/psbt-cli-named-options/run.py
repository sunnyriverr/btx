"""Bounded diagnostic using verified existing binaries; no product edit/build."""
from pathlib import Path
import hashlib,json,os,platform,shutil,signal,stat,subprocess,time
W=Path(os.environ['GITHUB_WORKSPACE']);HERE=Path(__file__).parent;P=W/'p2mr-parent-product';T=W/'p2mr-parent-native';B=T/'build';O=W/'psbt-cli-results';O.mkdir(exist_ok=True);R=W/'psbt-cli-runtime';BASE='666673a3153225ba264c7870e0e82e354df86765'
E=json.loads((HERE/'expected.json').read_text());state={'source':BASE,'fixture':os.environ['GITHUB_SHA'],'run':os.environ['GITHUB_RUN_ID'],'commands':[],'platform':platform.platform(),'source_audits':{}}
env=dict(os.environ,PYTHONPATH=str(P/'test/functional'),PYTHONDONTWRITEBYTECODE='1',BTX_OPENSSL=str(T/'openssl/bin/openssl'),PSBT_RESULTS=str(O))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save():(O/'result.json').write_text(json.dumps(state,indent=2)+'\n')
def command(args,label,timeout=180):
 print('START',label,flush=True);t=time.monotonic()
 with (O/(label+'.log')).open('wb') as f:
  p=subprocess.Popen([str(x) for x in args],env=env,stdout=f,stderr=subprocess.STDOUT,start_new_session=True)
  try:rc=p.wait(timeout=timeout)
  except subprocess.TimeoutExpired:
   os.killpg(p.pid,signal.SIGTERM)
   try:p.wait(timeout=15)
   except subprocess.TimeoutExpired:os.killpg(p.pid,signal.SIGKILL);p.wait(timeout=5)
   raise
 state['commands'].append({'args':[str(x) for x in args],'label':label,'exit':rc,'seconds':round(time.monotonic()-t,3)});save();print('END',label,rc,flush=True);assert rc==0,(label,rc)
def audit(label):
 assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=P,text=True).strip()==BASE
 catalog={}
 for entry in subprocess.check_output(['git','ls-tree','-r','-z',BASE],cwd=P).split(b'\0'):
  if not entry:continue
  meta,name=entry.split(b'\t',1);mode,kind,want=meta.decode().split();assert kind=='blob';path=P/os.fsdecode(name)
  raw=os.fsencode(os.readlink(path)) if mode=='120000' else path.read_bytes();actual=hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest();assert actual==want,str(path)
  m='120000' if path.is_symlink() else '100755' if stat.S_ISREG(path.stat().st_mode) and path.stat().st_mode&0o111 else '100644';assert m==mode,str(path)
  catalog[os.fsdecode(name)]={'blob':actual,'mode':m}
 assert len(catalog)==14309
 state['source_audits'][label]={'files':len(catalog),'catalog_sha256':hashlib.sha256(json.dumps(catalog,sort_keys=True).encode()).hexdigest(),'all_git_blobs_and_modes_verified':True};save()
def processes():
 result=[]
 for p in Path('/proc').iterdir():
  if not p.name.isdigit():continue
  try:
   exe=Path(os.readlink(p/'exe'))
   if exe.parent!=B/'bin' or exe.name not in ['btxd','btx-cli','btx-modeld','btx-guardd']:continue
   start=(p/'stat').read_text().rsplit(')',1)[1].split()[19];result.append({'pid':int(p.name),'exe':str(exe),'start_ticks':start})
  except (OSError,PermissionError):pass
 return result
try:
 assert platform.system()=='Linux' and platform.machine()=='x86_64';assert shutil.disk_usage(W).free>2*1024**3;assert not R.exists() and not processes()
 audit('before')
 state['binaries_before']={n:sha(B/'bin'/n) for n in E['binaries']};assert all(state['binaries_before'][n]==x['sha256'] for n,x in E['binaries'].items())
 assert sha(B/'CMakeCache.txt')==E['cmake_cache_sha256']
 for n,want in E['openssl']['files'].items():assert sha(T/'openssl'/n)==want
 cache=(B/'CMakeCache.txt').read_text();assert 'ENABLE_WALLET:BOOL=ON' in cache and 'WITH_MODELNET:BOOL=ON' in cache
 state['cache_id']=E['cache_id'];state['configuration']={'wallet_compiled':True,'modelnet_compiled':True,'node_modelnet_runtime':False,'wallet_private_keys':False,'sign':False,'finalize':False,'build_performed':False,'cache_saved':False}
 command(['sudo','apt-get','-o','Acquire::http::Timeout=30','-o','Acquire::https::Timeout=30','-o','Acquire::Retries=1','update'],'apt-update',240)
 command(['sudo','apt-get','-o','Acquire::Retries=1','install','-y','--no-install-recommends','libevent-dev','libsqlite3-dev','libzmq3-dev'],'apt-install',300)
 command(['ldd',B/'bin/btxd'],'ldd-node',30);command(['ldd',B/'bin/btx-cli'],'ldd-cli',30)
 command(['dpkg-query','-W','libevent-dev','libsqlite3-dev','libzmq3-dev'],'runtime-packages',30)
 R.mkdir(mode=0o700);state['case_sha256']=sha(HERE/'case.py');save()
 command(['python3',HERE/'case.py','--configfile='+str(B/'test/config.ini'),'--tmpdir='+str(R/'node-test'),'--cachedir='+str(R/'chain-cache'),'--portseed=42819','--nocleanup'],'wallet-cli-diagnostic',150)
 observed=json.loads((O/'observations.json').read_text());assert observed['diagnostic_complete'] and observed['node_rpc_shutdown_complete'];assert len(observed['calls'])==8 and len(observed['comparisons'])==3
 assert observed['signing_disabled_every_request'] and observed['finalization_disabled_every_request'] and observed['wallet_before']==observed['wallet_after']
 state['observations']=observed;state['binaries_after']={n:sha(B/'bin'/n) for n in E['binaries']};assert state['binaries_after']==state['binaries_before']
 assert sha(HERE/'case.py')==state['case_sha256'];assert sha(B/'CMakeCache.txt')==E['cmake_cache_sha256'];audit('after');assert state['source_audits']['before']==state['source_audits']['after'];state['diagnosis_verified']=True
except Exception as error:state['error']=repr(error);raise
finally:
 remaining=processes();actions=[]
 for old in remaining:
  if old in processes():os.kill(old['pid'],signal.SIGTERM);actions.append({**old,'signal':'SIGTERM'})
 end=time.monotonic()+15
 while processes() and time.monotonic()<end:time.sleep(.1)
 survivors=processes()
 if R.exists():
  for p in R.rglob('*'):
   if p.is_file() and p.name in ['debug.log','test_framework.log'] and p.stat().st_size<5*1024**2:
    target=O/'logs'/p.relative_to(R);target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,target)
  if not survivors:shutil.rmtree(R)
 state['cleanup']={'before':remaining,'signals':actions,'remaining':survivors,'runtime_removed':not R.exists()};state['diagnosis_verified']=bool(state.get('diagnosis_verified') and not remaining and not actions and not survivors and not state.get('error'));save()
assert state['diagnosis_verified'],'Incomplete diagnostic; inspect records'
