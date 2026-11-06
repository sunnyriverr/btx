from pathlib import Path
import ast,os,json,hashlib,subprocess,configparser,signal,shutil,stat,time,sys
W=Path(os.environ['GITHUB_WORKSPACE']);HERE=Path(__file__).parent;P=W/'p2mr-parent-product';T=W/'p2mr-parent-native';B=T/'build';O=W/'rpc-help-live-results';O.mkdir(exist_ok=True);R=W/'rpc-help-live-runtime';BASE='666673a3153225ba264c7870e0e82e354df86765'
state={'base':BASE,'fixture':os.environ['GITHUB_SHA'],'commands':[]};expected=json.loads((HERE/'expected.json').read_text());env=dict(os.environ,BTX_OPENSSL=str(T/'openssl/bin/openssl'),PYTHONDONTWRITEBYTECODE='1',PYTHONPATH=str(P/'test/functional'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(): (O/'result.json').write_text(json.dumps(state,indent=2))
def command(args,label,allowed=(0,),timeout=240):
 with (O/(label+'.log')).open('wb') as f:
  p=subprocess.Popen([str(x) for x in args],stdout=f,stderr=subprocess.STDOUT,env=env,start_new_session=True);t=time.monotonic()
  try:rc=p.wait(timeout=timeout)
  except subprocess.TimeoutExpired:
   os.killpg(p.pid,signal.SIGTERM);p.wait(timeout=20);raise
 state['commands'].append({'args':[str(x) for x in args],'label':label,'rc':rc,'seconds':time.monotonic()-t});save();assert rc in allowed,(label,rc);print(label,rc,flush=True)
def audit():
 assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=P,text=True).strip()==BASE
 result={}
 for e in subprocess.check_output(['git','ls-tree','-r','-z',BASE],cwd=P).split(b'\0'):
  if not e:continue
  meta,name=e.split(b'\t',1);mode,kind,want=meta.decode().split();path=P/os.fsdecode(name);data=os.fsencode(os.readlink(path)) if mode=='120000' else path.read_bytes()
  actual=hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest();assert actual==want,str(path)
  actual_mode='120000' if path.is_symlink() else '100755' if path.stat().st_mode&0o111 else '100644';assert actual_mode==mode,str(path)
  result[os.fsdecode(name)]=want
 return hashlib.sha256(json.dumps(result,sort_keys=True).encode()).hexdigest(),len(result)
def processes():
 out=[]
 for p in Path('/proc').iterdir():
  if not p.name.isdigit():continue
  try:
   exe=os.readlink(p/'exe')
   if exe in [str(B/'bin'/n) for n in ['btxd','btx-cli','btx-modeld']]:out.append({'pid':int(p.name),'exe':exe})
  except (OSError,PermissionError):pass
 return out
try:
 assert shutil.disk_usage(W).free>2*1024**3
 state['audit_before']=audit();assert not processes()
 for n,e in expected['binaries'].items():
  if n!='btx-modeld':assert sha(B/'bin'/n)==e['sha256'],n
 assert sha(B/'CMakeCache.txt')==expected['cmake_cache_sha256']
 for n,want in expected['openssl']['files'].items():assert sha(T/'openssl'/n)==want
 state['binaries_before']={n:sha(B/'bin'/n) for n in expected['binaries'] if n!='btx-modeld'}
 cache=(B/'CMakeCache.txt').read_text();assert 'ENABLE_WALLET:BOOL=ON' in cache and 'WITH_MODELNET:BOOL=ON' in cache
 command(['sudo','apt-get','-o','Acquire::Retries=1','update'],'apt-update')
 command(['sudo','apt-get','install','-y','--no-install-recommends','libevent-dev','libsqlite3-dev','libzmq3-dev','g++-13','ninja-build','pkgconf','libboost-dev','ccache'],'apt-install')
 command(['ldd',B/'bin/btxd'],'ldd')
 env.update(CC='gcc-13',CXX='g++-13',CCACHE_DIR=str(T/'ccache'),CCACHE_BASEDIR=str(W),CCACHE_COMPILERCHECK='content',PKG_CONFIG_PATH=str(T/'openssl/lib/pkgconfig'))
 for name in subprocess.check_output(['git','ls-tree','-r','--name-only','-z',BASE],cwd=P).split(b'\0'):
  if name:os.utime(P/os.fsdecode(name),(1700000000,1700000000),follow_symlinks=False)
 command(['cmake','-S',P,'-B',B],'cached-configure',timeout=120)
 command(['ninja','-C',B,'-n','btx-modeld'],'helper-build-plan',timeout=60)
 steps=[x for x in (O/'helper-build-plan.log').read_text().splitlines() if x.startswith('[')]
 assert len(steps)<=12,'Unexpected helper rebuild footprint'
 command(['cmake','--build',B,'--target','btx-modeld','--parallel','2'],'helper-only-build',timeout=240)
 assert sha(B/'bin/btx-modeld')==expected['binaries']['btx-modeld']['sha256']
 state['binaries_before']['btx-modeld']=sha(B/'bin/btx-modeld');save()

 config=configparser.ConfigParser();config.read(B/'test/config.ini');assert config.getboolean('components','ENABLE_WALLET');assert Path(config['environment']['SRCDIR'])==P
 config['components']['ENABLE_MODELNET']='true'
 configpath=O/'functional-config.ini'
 with configpath.open('w') as f:config.write(f)
 state['config_overlay']='Existing generated config plus verified CMakeCache WITH_MODELNET=ON as explicit ENABLE_MODELNET=true; root config generation already qualified locally, no root reconfigure/build.'
 R.mkdir(mode=0o700)
 wrapper=P/'contrib/modelnet/btx-model';original=wrapper.read_bytes();state['pair']={}
 try:
  for variant in ['baseline','candidate']:
   if variant=='candidate':wrapper.write_bytes((HERE/'candidate-wrapper.py').read_bytes())
   env['MIRROR_VARIANT']=variant
   command(['python3',HERE/'case.py','--configfile='+str(configpath),'--tmpdir='+str(R/(variant+'-node')),'--cachedir='+str(R/(variant+'-cache')),'--portseed='+str(42800+(variant=='candidate')),'--nocleanup'],'mirror-'+variant,allowed=(1,) if variant=='baseline' else (0,),timeout=150)
   obs=json.loads((O/(variant+'-observations.json')).read_text())
   assert obs['method_pass']==(variant=='candidate')
   assert obs['node_stopped'] and obs['helper_exit']==0 and not obs['socket_remaining'] and not processes()
   if variant=='baseline':assert 'idempotency_key required' in (O/'mirror-baseline.log').read_text()
   state['pair'][variant]=obs;save()
 finally:wrapper.write_bytes(original)
 assert state['pair']['baseline']['method_sha256']==state['pair']['candidate']['method_sha256']
 state['binaries_after']={n:sha(B/'bin'/n) for n in expected['binaries']};assert state['binaries_after']==state['binaries_before'];state['audit_after']=audit();assert state['audit_after']==state['audit_before'];state['qualification_pass']=True
except Exception as e:state['error']=repr(e);raise
finally:
 state['cleanup_before']=processes();state['cleanup_signals']=[]
 for row in state['cleanup_before']:
  os.kill(row['pid'],signal.SIGTERM);state['cleanup_signals'].append(row)
 for _ in range(50):
  if not processes():break
  time.sleep(.1)
 state['cleanup_remaining']=processes()
 if R.exists():
  for p in R.rglob('*'):
   if p.is_file() and p.name in ['test_framework.log','debug.log']:
    dest=O/'logs'/p.relative_to(R);dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,dest)
  if not state['cleanup_remaining']:shutil.rmtree(R)
 state['runtime_removed']=not R.exists();state['qualification_pass']=bool(state.get('qualification_pass') and not state['cleanup_before'] and not state['cleanup_remaining']);save()
assert state['qualification_pass']
