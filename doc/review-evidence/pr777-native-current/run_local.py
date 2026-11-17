"""Bounded local consumer of the same retained native binary and controller."""
from pathlib import Path
import os,json,hashlib,shutil,subprocess,time,signal,socket,platform,urllib.request
P=Path(__file__).resolve().parent;W=P/'local';R=W/'records';M=json.loads((P/'manifest.json').read_text());RESERVE=1342177280
SCRATCH=W/'native777-runtime';SCRATCH.mkdir(exist_ok=True,mode=0o700)
STATE={'complete':False,'compiled':False,'tests_started':False,'tests_passed':False,'source':M['source'],'cases':{},'platform':{'macos':platform.mac_ver()[0],'architecture':platform.machine()},'execution':'local; exact saved Mac15 binary/private matched runtime'}
def save(): (R/'runtime-result.json').write_text(json.dumps(STATE,indent=2)+'\n')
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def size():
    total=0
    for p in SCRATCH.rglob('*'):
        try:
            if p.is_file() and not p.is_symlink():total+=p.stat().st_size
        except FileNotFoundError:pass
    return total

def absent(pid):
    try:os.killpg(pid,0);return False
    except ProcessLookupError:return True

def bounded(args,name,seconds,env=None):
    start=time.monotonic();reason=None;path=R/(name+'.log')
    assert shutil.disk_usage(W).free>RESERVE+512*1024**2
    with path.open('wb') as log:
        process=subprocess.Popen([str(x) for x in args],stdout=log,stderr=subprocess.STDOUT,start_new_session=True,env=env)
        try:
            while process.poll() is None:
                if time.monotonic()-start>seconds:reason='time'
                elif shutil.disk_usage(W).free<RESERVE:reason='storage'
                elif size()>512*1024**2:reason='scratch'
                if reason:break
                time.sleep(1)
        finally:
            if not absent(process.pid):
                os.killpg(process.pid,signal.SIGTERM)
                until=time.monotonic()+10
                while time.monotonic()<until and not absent(process.pid):time.sleep(.2)
                if not absent(process.pid):os.killpg(process.pid,signal.SIGKILL)
            process.wait(timeout=15)
    STATE[name]={'exit':process.returncode,'seconds':round(time.monotonic()-start,3),'bound':reason,'cleanup_absent':absent(process.pid),'log_sha256':sha(path)};save()
    assert not reason and process.returncode==0 and absent(process.pid),(name,STATE[name])
    return path.read_text(errors='replace')

def main():
    assert platform.system()=='Darwin' and platform.machine()=='arm64'
    assert W.resolve().is_relative_to(P.resolve()) and shutil.disk_usage(W).free>RESERVE+512*1024**2
    files=json.loads((P/'files.json').read_text())
    for remote,row in files.items():
        if row['local'] in ['native_pair.py','evm_verify.py']:assert sha(P/row['local'])==row['sha256']
    f=W/'python-runtime/Python.framework/Versions/3.12';py=f/'bin/python3.12'
    assert sha(py)==M['python']['executable_sha256']
    for n,v in M['binaries'].items():assert sha(W/'mac-config-build/bin'/n)==v['sha256']
    env=os.environ.copy()
    for name in ['GH_TOKEN','GITHUB_TOKEN','PYTHONPATH','PYTHONHOME','__PYVENV_LAUNCHER__','LD_PRELOAD','DYLD_INSERT_LIBRARIES']:env.pop(name,None)
    tools=W/'tools';home=W/'tool-home';home.mkdir(exist_ok=True)
    env.update(DYLD_FRAMEWORK_PATH=str(W/'python-runtime'),DYLD_LIBRARY_PATH=str(f/'lib'),PATH=str(tools)+os.pathsep+str(f/'bin')+os.pathsep+env['PATH'],HOME=str(home),PYTHONDONTWRITEBYTECODE='1',BTX_BINARY=str(W/'mac-config-build/bin/btxd'),BTX_BINARY_SHA256=M['binaries']['btxd']['sha256'])
    probe=bounded([py,'-B','-I','-c','import sys,platform,ssl,sqlite3,cryptography,cffi,pycparser,json;print(json.dumps(dict(version=list(sys.version_info[:3]),prefix=sys.prefix,architecture=platform.machine(),cryptography=cryptography.__version__,cffi=cffi.__version__,pycparser=pycparser.__version__,sqlite=sqlite3.sqlite_version,ssl=ssl.OPENSSL_VERSION)))'],'local-python-dependencies',30,env)
    info=json.loads(probe);assert info['version']==[3,12,10] and [info[k] for k in ['cryptography','cffi','pycparser']]==['46.0.4','2.1.1','3.12'] and Path(info['prefix']).is_relative_to(W)
    STATE['runtime']=info;STATE['binary_sha256']=M['binaries']['btxd']['sha256'];save()
    for name in ['btxd','btx-cli']:bounded(['otool','-L',W/'mac-config-build/bin'/name],name+'-linkage',30,env)
    versiondir=W/'version-probe';versiondir.mkdir(exist_ok=True)
    version=bounded([W/'mac-config-build/bin/btxd','-datadir='+str(versiondir),'-regtest','-autoupdate=0','-version'],'daemon-version',30,env)
    assert '0.34.17' in version
    bounded([tools/'forge','--version'],'foundry-version',30,env)
    assert '--quiet' in bounded([tools/'anvil','--help'],'anvil-help',30,env)
    bounded([tools/'forge','build','--root',W/'product/contrib/swapnet/contracts','--skip','test'],'contract-build',180,env)
    env['CONTRACT_ARTIFACT']=str(W/'product/contrib/swapnet/contracts/out/SwapNetHTLC.sol/SwapNetHTLC.json')
    assert Path(env['CONTRACT_ARTIFACT']).is_file()
    cases=os.environ.get('NATIVE_CASES','settle refund').split();assert cases and set(cases)<={'settle','refund'}
    for case in cases:
        prior=R/case/'result.json'
        if prior.exists() and json.loads(prior.read_text()).get('status')=='PASS':
            STATE['cases'][case]=json.loads(prior.read_text());continue
        with socket.socket() as sock:sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
        env['ANVIL_URL']='http://127.0.0.1:'+str(port)
        with (R/('anvil-'+case+'.log')).open('wb') as log:
            anvil=subprocess.Popen([str(tools/'anvil'),'--host','127.0.0.1','--port',str(port),'--slots-in-an-epoch','1','--quiet'],stdout=log,stderr=log,start_new_session=True,env=env)
        try:
            for _ in range(50):
                assert anvil.poll() is None,'Anvil exited before readiness'
                try:
                    with urllib.request.urlopen(urllib.request.Request(env['ANVIL_URL'],b'{"jsonrpc":"2.0","id":1,"method":"eth_chainId","params":[]}',{'Content-Type':'application/json'}),timeout=1) as f:assert json.load(f)['result'];break
                except OSError:time.sleep(.2)
            else:raise RuntimeError('Anvil readiness timeout')
            folder=SCRATCH/case;folder.mkdir(mode=0o700);STATE['tests_started']=True;save()
            bounded([py,'-B','-u',P/'native_pair.py',folder,case],'native-'+case,600,env)
            record=json.loads((R/case/'result.json').read_text());assert record['status']=='PASS' and not record['cleanup_errors'];STATE['cases'][case]=record;save()
        finally:
            if anvil.poll() is None:anvil.terminate()
            try:anvil.wait(timeout=10)
            except subprocess.TimeoutExpired:anvil.kill();anvil.wait(timeout=10)
            assert anvil.returncode in (0,-15) and absent(anvil.pid),'Anvil cleanup failed'
    STATE['tests_passed']=all(STATE['cases'].get(c,{}).get('status')=='PASS' for c in cases);STATE['complete']=True;save()

if __name__=='__main__':
    os.chdir(W)
    try:main()
    except Exception as error:STATE['error']=f'{type(error).__name__}: {error}';save();raise
