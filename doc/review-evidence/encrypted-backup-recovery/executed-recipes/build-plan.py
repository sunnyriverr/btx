"""Restore immutable Qt cache and inspect daemon/CLI/Qt plans; no BTX compile."""
from pathlib import Path
import os,json,subprocess,shutil,sys,tarfile,time,signal
from checkpoint import sha,restore_timestamps,verify_restored
BASE='dac9aee53520bd49ed320ec7a49b9072fc7d88d9'
TAR='90391b49487f57e3c820200f28142e6873b0fecbb2a2d4b82091e48050437176'

def verdict(r):
    gates=('checkpoint_verified','source_verified','configured','plans_verified','objects_preserved','input_preserved')
    return 'PLAN_PASS' if not r.get('error') and all(r.get(k) is True for k in gates) and r.get('compile_started') is False else 'INCOMPLETE'

def main():
    w=Path(os.environ['GITHUB_WORKSPACE']).resolve();out=w/'wallet-plan-records';out.mkdir(exist_ok=False)
    r={'source':BASE,'commands':[],'compile_started':False}
    def save():(out/'result.json').write_text(json.dumps(dict(r,verdict=verdict(r)),indent=2)+'\n')
    def run(args,label,limit=180,cwd=None):
        with (out/(label+'.log')).open('wb') as log:
            child=subprocess.Popen(list(map(str,args)),cwd=cwd,stdout=log,stderr=subprocess.STDOUT,start_new_session=True);start=time.monotonic();stop=None
            while child.poll() is None:
                if time.monotonic()-start>limit:stop='timeout'
                if shutil.disk_usage(w).free<2*1024**3:stop='disk_reserve'
                if stop:
                    os.killpg(child.pid,signal.SIGTERM)
                    try:child.wait(10)
                    except subprocess.TimeoutExpired:os.killpg(child.pid,signal.SIGKILL);child.wait()
                    break
                time.sleep(.5)
        r['commands'].append({'label':label,'exit':child.returncode,'seconds':time.monotonic()-start,'stop':stop});save()
        assert child.returncode==0 and not stop,label
        return (out/(label+'.log')).read_text(errors='replace')
    try:
        assert shutil.disk_usage(w).free>=10*1024**3
        saved=w/'saved-checkpoint';tar=saved/'build-state.tar.gz';m=json.loads((saved/'manifest.json').read_text())
        assert sha(tar)==TAR==m['archive_sha256'] and m['identity']['source']==BASE
        assert Path(m['workspace'])==w
        assert not (w/'product').exists()
        with tarfile.open(tar) as archive:archive.extractall(w,filter='data')
        restore_timestamps(w,m);verify_restored(w,m);r['checkpoint_verified']=True
        source=w/'product';build=w/'gui-pilot-runtime/qtbuild';accepted=w/'accepted-source'
        assert run(['git','rev-parse','HEAD'],'accepted-head',cwd=accepted).strip()==BASE
        assert not run(['git','status','--porcelain'],'accepted-clean',cwd=accepted).strip()
        names=run(['git','ls-files'],'accepted-files',cwd=accepted).splitlines()
        for name in names:
            a=accepted/name;b=source/name
            if a.is_symlink():assert b.is_symlink() and os.readlink(a)==os.readlink(b),name
            else:assert a.is_file() and b.is_file() and sha(a)==sha(b),name
        r['source_verified']=True
        r['original_wallet_sha256']=sha(source/'src/wallet/wallet.cpp')
        objects={str(f.relative_to(build)):sha(f) for f in build.rglob('*.o')}
        r['objects_before']=len(objects)
        assert run(['g++','-dumpfullversion'],'gcc').strip()=='11.4.0'
        assert 'OpenSSL 3.5.9' in run([w/'gui-pilot-runtime/openssl/bin/openssl','version'],'openssl')
        run(['cmake','-S',source,'-B',build,'-DBUILD_DAEMON=ON','-DBUILD_CLI=ON'],'configure',300)
        cache=(build/'CMakeCache.txt').read_text()
        for flag in ['BUILD_DAEMON:BOOL=ON','BUILD_CLI:BOOL=ON','BUILD_GUI:BOOL=ON','BUILD_TESTS:BOOL=OFF','WITH_MODELNET:BOOL=ON','ENABLE_WALLET:BOOL=ON','WITH_SQLITE:BOOL=ON']:assert flag in cache,flag
        r['configured']=True
        run(['cmake','-P',build/'CMakeFiles/VerifyGlobs.cmake'],'verify-globs',cwd=build)
        observed=out/'observed.ninja';shutil.copy2(build/'build.ninja',observed)
        for phase in ['baseline','candidate']:
            if phase=='candidate':
                shutil.copy2(w/'contrib/devtools/wallet-recovery-plan/candidate/src/wallet/wallet.cpp',source/'src/wallet/wallet.cpp')
            dry=run(['ninja','-C',build,'-f',observed,'-d','explain','-n','btxd','btx-cli','btx-qt'],phase+'-dry-plan')
            assert 'Re-running CMake' not in dry and 'Re-checking globbed' not in dry
            r[phase+'_steps']=[line for line in dry.splitlines() if line.startswith('[')]
        r['candidate_wallet_sha256']=sha(source/'src/wallet/wallet.cpp')
        r['plans_verified']=True
        r['objects_preserved']=objects=={str(f.relative_to(build)):sha(f) for f in build.rglob('*.o')}
        r['input_preserved']=sha(tar)==TAR
        assert r['objects_preserved'] and r['input_preserved']
        for name in ['CMakeCache.txt','compile_commands.json','build.ninja']:shutil.copy2(build/name,out/name)
        r['free_bytes']=shutil.disk_usage(w).free
    except Exception as e:r['error']=repr(e)
    finally:save()
    return 0 if verdict(r)=='PLAN_PASS' else 1
if __name__=='__main__':sys.exit(main())
