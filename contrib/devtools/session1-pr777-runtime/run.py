"""Restore exact build and execute only two disposable native BTX/Anvil journeys."""
from pathlib import Path
import hashlib,json,os,platform,shutil,signal,socket,subprocess,tarfile,time,urllib.request
import restore
W,P,S,B,R,M=restore.W,restore.P,restore.S,restore.B,restore.R,restore.M
STATE={'complete':False,'compiled':False,'tests_started':False,'tests_passed':False,'source':M['source'],'cases':{}}
SCRATCH=W/'native777-runtime';SCRATCH.mkdir(mode=0o700)
def save(): (R/'runtime-result.json').write_text(json.dumps(STATE,indent=2)+'\n')
def sha(p): return restore.sha(p)
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
    assert shutil.disk_usage(W).free>restore.RESERVE+2*1024**3
    with path.open('wb') as log:
        process=subprocess.Popen([str(x) for x in args],stdout=log,stderr=subprocess.STDOUT,start_new_session=True,env=env)
        try:
            while process.poll() is None:
                if time.monotonic()-start>seconds:reason='time'
                elif shutil.disk_usage(W).free<restore.RESERVE:reason='storage'
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
    assert os.environ.get('GITHUB_ACTIONS')=='true' and os.environ.get('GITHUB_REPOSITORY')=='sunnyriverr/btx'
    assert platform.system()=='Darwin' and platform.machine()=='arm64'
    assert shutil.disk_usage(W).free>=15*1024**3
    assert subprocess.check_output(['git','-C',S,'rev-parse','HEAD'],text=True).strip()==M['source']
    assert not subprocess.check_output(['git','-C',S,'status','--porcelain'],text=True).strip()
    restore.restore();assert sha(B/'CMakeCache.txt')==M['cache_sha256']
    for n,identity in M['binaries'].items():assert (B/'bin'/n).stat().st_size==identity['bytes'] and sha(B/'bin'/n)==identity['sha256']
    py=Path(os.environ['BTX_BUILD_PYTHON']).resolve();assert sha(py)==M['python']['executable_sha256']
    assert sha(P/'dependencies.json')==M['dependency_lock_sha256']
    bounded([py,P/'bootstrap.py'],'dependency-bootstrap',300)
    env=os.environ.copy()
    for n in ['GH_TOKEN','GITHUB_TOKEN','PYTHONPATH','PYTHONHOME','LD_PRELOAD','DYLD_INSERT_LIBRARIES']:env.pop(n,None)
    env.update(PYTHONDONTWRITEBYTECODE='1',BTX_BINARY=str(B/'bin/btxd'),BTX_BINARY_SHA256=M['binaries']['btxd']['sha256'])
    # Foundry is a pinned disposable test dependency, not installed on the host.
    target=W/'foundry-mac.tar.gz';url='https://github.com/foundry-rs/foundry/releases/download/v1.9.0/foundry_v1.9.0_darwin_arm64.tar.gz'
    with urllib.request.urlopen(url,timeout=60) as src,target.open('wb') as out:
        total=0
        while True:
            block=src.read(1024**2)
            if not block:break
            total+=len(block);assert total<=122020568;out.write(block)
    assert total==122020568 and sha(target)=='38f9af72b266c38ce2e4dfc659ae9cbd1f78c01b34738a76b6c4cb9610579426'
    tools=W/'foundry777';tools.mkdir()
    with tarfile.open(target) as tar:
        for name in ['forge','anvil']:
            member=tar.getmember(name);assert member.isfile() and member.size<200*1024**2
            with tar.extractfile(member) as src,(tools/name).open('wb') as out:shutil.copyfileobj(src,out)
            (tools/name).chmod(0o755)
    target.unlink()
    env['PATH']=str(tools)+os.pathsep+env['PATH']
    STATE['dependencies']={'foundry_archive_sha256':'38f9af72b266c38ce2e4dfc659ae9cbd1f78c01b34738a76b6c4cb9610579426','anvil_binary_sha256':sha(tools/'anvil'),'forge_binary_sha256':sha(tools/'forge')}
    bounded([tools/'forge','--version'],'foundry-version',30,env)
    helptext=bounded([tools/'anvil','--help'],'anvil-help',30,env);assert '--silent' in helptext
    # Only the exact pinned Solidity contract is compiled; BTX objects are reused.
    bounded([tools/'forge','build','--root',S/'contrib/swapnet/contracts','--skip','test'],'contract-build',180,env)
    env['CONTRACT_ARTIFACT']=str(S/'contrib/swapnet/contracts/out/SwapNetHTLC.sol/SwapNetHTLC.json')
    assert Path(env['CONTRACT_ARTIFACT']).is_file()
    for case in ['settle','refund']:
        with socket.socket() as sock:sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
        env['ANVIL_URL']='http://127.0.0.1:'+str(port)
        with (R/('anvil-'+case+'.log')).open('wb') as log:
            anvil=subprocess.Popen([str(tools/'anvil'),'--host','127.0.0.1','--port',str(port),'--slots-in-an-epoch','1','--silent'],stdout=log,stderr=log,start_new_session=True,env=env)
        try:
            for _ in range(50):
                assert anvil.poll() is None,'Anvil exited before readiness'
                try:
                    with urllib.request.urlopen(urllib.request.Request(env['ANVIL_URL'],b'{"jsonrpc":"2.0","id":1,"method":"eth_chainId","params":[]}',{'Content-Type':'application/json'}),timeout=1) as f:assert json.load(f)['result'];break
                except OSError:time.sleep(.2)
            else:raise RuntimeError('Anvil readiness timeout')
            folder=SCRATCH/case;folder.mkdir(mode=0o700);STATE['tests_started']=True;save()
            bounded([py,'-u',P/'native_pair.py',folder,case],'native-'+case,600,env)
            record=json.loads((R/case/'result.json').read_text());assert record['status']=='PASS' and not record['cleanup_errors'];STATE['cases'][case]=record;save()
        finally:
            if anvil.poll() is None:anvil.terminate()
            try:anvil.wait(timeout=10)
            except subprocess.TimeoutExpired:anvil.kill();anvil.wait(timeout=10)
            assert anvil.returncode in (0,-15) and absent(anvil.pid),'Anvil cleanup failed'
    STATE['tests_passed']=len(STATE['cases'])==2;STATE['complete']=True;save()

if __name__=='__main__':
    try:main()
    except Exception as error:STATE['error']=f'{type(error).__name__}: {error}';save();raise
