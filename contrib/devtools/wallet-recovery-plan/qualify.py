"""Paired exact-source builds and one maintained regression; no production access."""
from pathlib import Path
import os,sys,json,subprocess,time,signal,shutil,configparser
import run as pilot
from checkpoint import sha,create
MARKERS=('CONTROL: original locked encrypted wallet recognizes both receipts',
         'CONTROL: plain backup recovers both receipts without encrypted recovery warning',
         'RECOVERY: explicit refill/rescan restores exact receipts at same tip; relock succeeds')
def baseline_verdict(code,text):
    return code==1 and all(x in text for x in MARKERS) and 'assert_equal(warnings.count(RECOVERY_WARNING), 1)' in text and 'AssertionError: not(0 == 1)' in text
def candidate_verdict(code,text):
    return code==0 and all(x in text for x in MARKERS) and 'Tests successful' in text

def main():
    w=Path(os.environ['GITHUB_WORKSPACE']).resolve();out=w/'wallet-qualification-records';out.mkdir(exist_ok=False)
    r={'source':pilot.BASE,'commands':[],'test_pass':False};runtime=w/'wallet-qualification-runtime';outputs=w/'wallet-qualification-binaries';outputs.mkdir(exist_ok=False)
    source=w/'product';build=w/'gui-pilot-runtime/qtbuild';helper=w/'contrib/devtools/wallet-recovery-plan';case=helper/'candidate/test/functional/wallet_encrypted_backup_recovery.py'
    def save():(out/'result.json').write_text(json.dumps(r,indent=2)+'\n')
    def processes():
        found=[]
        for pid in Path('/proc').iterdir():
            if not pid.name.isdigit():continue
            try:
                exe=Path(os.readlink(pid/'exe'))
                if exe.is_relative_to(outputs):found.append(int(pid.name))
            except (OSError,PermissionError):pass
        return found
    def command(args,label,limit,env=None,allowed=(0,)):
        print('START',label,flush=True)
        with (out/(label+'.log')).open('wb') as log:
            child=subprocess.Popen(list(map(str,args)),stdout=log,stderr=subprocess.STDOUT,env=env,start_new_session=True);start=time.monotonic();stop=None
            while child.poll() is None:
                if time.monotonic()-start>limit:stop='timeout'
                if shutil.disk_usage(w).free<2*1024**3:stop='disk_reserve'
                if stop:
                    os.killpg(child.pid,signal.SIGTERM)
                    try:child.wait(15)
                    except subprocess.TimeoutExpired:os.killpg(child.pid,signal.SIGKILL);child.wait()
                    break
                time.sleep(.5)
        r['commands'].append({'label':label,'exit':child.returncode,'stop':stop,'seconds':time.monotonic()-start});save();print('END',label,child.returncode,flush=True)
        assert not stop and child.returncode in allowed,label
        return child.returncode,(out/(label+'.log')).read_text(errors='replace')
    try:
        assert pilot.main()==0
        plan=json.loads((w/'wallet-plan-records/result.json').read_text());assert pilot.verdict(plan)=='PLAN_PASS'
        assert len(plan['baseline_steps'])<=20 and len(plan['candidate_steps'])<=22,'Changed build scope needs review'
        assert sha(source/'src/wallet/wallet.cpp')==plan['candidate_wallet_sha256']
        shutil.copy2(w/'accepted-source/src/wallet/wallet.cpp',source/'src/wallet/wallet.cpp')
        assert sha(source/'src/wallet/wallet.cpp')==plan['original_wallet_sha256']
        r['case_sha256']=sha(case);r['source_wallet_before']=sha(source/'src/wallet/wallet.cpp')
        # Both binaries use the same accepted source, compiler/cache and flags;
        # the candidate changes only the reviewed RestoreWallet warning.
        runtime.mkdir(mode=0o700)
        r['builds']={};r['tests']={}
        for phase in ['baseline','candidate']:
            if phase=='candidate':shutil.copy2(helper/'candidate/src/wallet/wallet.cpp',source/'src/wallet/wallet.cpp')
            command(['ninja','-C',build,'-j2','btxd','btx-cli','btx-qt'],phase+'-build',900)
            dest=outputs/phase;binary=dest/'bin';binary.mkdir(parents=True)
            for name in ['btxd','btx-cli','btx-qt']:shutil.copy2(build/'bin'/name,binary/name)
            r['builds'][phase]={'wallet_sha256':sha(source/'src/wallet/wallet.cpp'),'binaries':{f.name:sha(f) for f in binary.iterdir()}}
            command([binary/'btxd','-version'],phase+'-version',30)
            command(['ldd',binary/'btxd'],phase+'-dependencies',30)
            config=configparser.ConfigParser();config['environment']={'CLIENT_NAME':'BTX','CLIENT_BUGREPORT':'https://github.com/btxchain/btx/issues','SRCDIR':str(source),'BUILDDIR':str(dest),'EXEEXT':'','RPCAUTH':str(source/'share/rpcauth/rpcauth.py')}
            cache=(build/'CMakeCache.txt').read_text();features={}
            for flag in ['ENABLE_WALLET','WITH_MODELNET','WITH_ZMQ','WITH_SQLITE','ENABLE_EXTERNAL_SIGNER']:
                lines=[x for x in cache.splitlines() if x.startswith(flag+':')];features[flag]=len(lines)==1 and lines[0].endswith('=ON')
            assert features['ENABLE_WALLET'] and features['WITH_MODELNET'] and features['WITH_SQLITE']
            config['components']={'ENABLE_WALLET':'true','ENABLE_MODELNET':str(features['WITH_MODELNET']).lower(),'ENABLE_ZMQ':str(features['WITH_ZMQ']).lower(),'ENABLE_EXTERNAL_SIGNER':str(features['ENABLE_EXTERNAL_SIGNER']).lower(),'USE_SQLITE':'true','USE_BDB':'false','ENABLE_CLI':'true','ENABLE_BITCOIND':'true','ENABLE_WALLET_TOOL':'false','ENABLE_BITCOIN_UTIL':'false','ENABLE_USDT_TRACEPOINTS':'false'}
            configfile=out/(phase+'-config.ini')
            with configfile.open('w') as f:config.write(f)
            env=dict(os.environ,PYTHONPATH=str(source/'test/functional'))
            rc,text=command(['python3',case,'--descriptors','--configfile='+str(configfile),'--tmpdir='+str(runtime/phase),'--cachedir='+str(runtime/(phase+'-cache')),'--portseed='+('27531' if phase=='baseline' else '27532'),'--nocleanup'],phase+'-test',240,env=env,allowed=(0,1,77))
            good=baseline_verdict(rc,text) if phase=='baseline' else candidate_verdict(rc,text)
            r['tests'][phase]={'exit':rc,'expected_verdict':good,'control_markers':{x:x in text for x in MARKERS}};save();assert good,phase+'-test-verdict'
            assert not processes(),phase+'-left-runtime'
        assert r['builds']['baseline']['wallet_sha256']!=r['builds']['candidate']['wallet_sha256']
        assert sha(case)==r['case_sha256']
        names=subprocess.check_output(['git','ls-files'],cwd=w/'accepted-source',text=True).splitlines()
        for name in names:
            original=w/'accepted-source'/name;actual=source/name
            if name=='src/wallet/wallet.cpp':assert sha(actual)==r['builds']['candidate']['wallet_sha256']
            elif original.is_symlink():assert actual.is_symlink() and os.readlink(original)==os.readlink(actual),name
            else:assert sha(actual)==sha(original),name
        r['source_after_verified']=True
        r['input_checkpoint_unchanged']=sha(w/'saved-checkpoint/build-state.tar.gz')==pilot.TAR
        r['test_pass']=True
    except Exception as e:r['error']=repr(e)
    finally:
        r['cleanup_before']=processes();r['cleanup_signals']=[]
        for pid in r['cleanup_before']:
            try:os.kill(pid,signal.SIGTERM);r['cleanup_signals'].append(pid)
            except ProcessLookupError:pass
        for _ in range(50):
            if not processes():break
            time.sleep(.1)
        r['cleanup_remaining']=processes()
        if runtime.exists():
            for f in runtime.rglob('*'):
                if f.is_file() and f.name in ['debug.log','test_framework.log']:
                    target=out/'logs'/f.relative_to(runtime);target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(f,target)
            if not r['cleanup_remaining']:shutil.rmtree(runtime)
        r['runtime_removed']=not runtime.exists()
        # Record and retain already completed binaries even if a later test fails.
        r['retained_binaries']={str(f.relative_to(outputs)):sha(f) for f in outputs.rglob('*') if f.is_file()}
        r['cleanup_ok']=not r['cleanup_remaining'] and r['runtime_removed'] and not r['cleanup_signals']
        try:
            if build.exists():
                m=create(w,w/'wallet-successor-checkpoint',{'source':pilot.BASE,'wallet_candidate_sha256':sha(source/'src/wallet/wallet.cpp'),'test_pass':r['test_pass']})
                r['successor_checkpoint']={'archive_sha256':m['archive_sha256'],'entries':len(m['rows'])}
        except Exception as e:r['checkpoint_error']=repr(e)
        r['qualified']=r['test_pass'] and r['cleanup_ok'] and r.get('input_checkpoint_unchanged') is True and 'error' not in r
        save()
    return 0 if r['qualified'] else 1
if __name__=='__main__':sys.exit(main())
