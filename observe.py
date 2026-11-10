"""Run a bounded native ordinary-Qt observation and preserve exact provenance."""
import configparser
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import time

w = Path(os.environ['GITHUB_WORKSPACE'])
out = w/'native-records'
out.mkdir()
source = w/'accepted-source'
result = {'status':'preflight'}

def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream,'sha256').hexdigest()

try:
    inputs = json.loads((w/'qualification-input.json').read_text())
    built = json.loads((w/'verified-build/result.json').read_text())
    assert built['phase']=='built' and built['accepted_base']==inputs['base']
    assert built['author499']==inputs['author499']
    assert built['patch498_sha256']==inputs['patch498_sha256']
    assert sha(w/'native_fixture.py')==inputs['fixture_sha256']
    for name,digest in built['candidate_binaries'].items():
        path=w/'candidate/bin'/name
        assert sha(path)==digest
        path.chmod(0o755)
        loaded=subprocess.check_output(['ldd',str(path)],text=True,timeout=20)
        (out/(name+'-ldd.log')).write_text(loaded)
        assert 'not found' not in loaded
    config=configparser.ConfigParser()
    config['environment']={'CLIENT_NAME':'BTX','CLIENT_BUGREPORT':'https://github.com/btxchain/btx/issues','SRCDIR':str(source),'BUILDDIR':str(w/'candidate'),'EXEEXT':'','RPCAUTH':str(source/'share/rpcauth/rpcauth.py')}
    config['components']={'ENABLE_WALLET':'true','USE_SQLITE':'true','USE_BDB':'false','ENABLE_ZMQ':'true','ENABLE_MODELNET':'true','ENABLE_EXTERNAL_SIGNER':'true','ENABLE_CLI':'true','ENABLE_BITCOIND':'true','ENABLE_WALLET_TOOL':'false','ENABLE_BITCOIN_UTIL':'false','ENABLE_USDT_TRACEPOINTS':'false'}
    ini=out/'config.ini'
    with ini.open('w') as stream: config.write(stream)
    runtime=w/'isolated-qt-shielded-state'
    env=dict(os.environ,QT_SHIELDED_FUNCTIONAL=str(source/'test/functional'),QT_SHIELDED_RECORDS=str(out),QT_SHIELDED_QT=str(w/'candidate/bin/btx-qt'),QT_SHIELDED_QT_SHA256=built['candidate_binaries']['btx-qt'])
    command=['dbus-run-session','--','xvfb-run','-a','-s','-screen 0 1440x1000x24 -nolisten tcp','sh','-ec','openbox >/dev/null 2>&1 & exec /usr/bin/python3 "$@"','sh',str(w/'native_fixture.py'),'--descriptors','--configfile='+str(ini),'--tmpdir='+str(runtime),'--nocleanup']
    result.update(status='running',inputs=inputs,build=built,command=command)
    start=time.monotonic()
    with (out/'test.log').open('wb') as log:
        process=subprocess.Popen(command,env=env,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
        try:
            code=process.wait(timeout=600)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid,signal.SIGTERM)
            try: process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid,signal.SIGKILL); process.wait()
            raise
        finally:
            for name in ('test_framework.log','node0/regtest/debug.log'):
                p=runtime/name
                if p.is_file(): shutil.copyfile(p,out/Path(name).name)
            for directory in ('stdout', 'stderr'):
                stream_dir=runtime/'node0'/directory
                if stream_dir.exists(): shutil.copytree(stream_dir,out/directory,dirs_exist_ok=True)
            # Runtime is exclusively ours. Stop only processes explicitly naming
            # this unique datadir if the framework failed to clean them itself.
            observed=subprocess.check_output(['ps','-eo','pid,args'],text=True)
            owned=[]
            for row in observed.splitlines():
                parts=row.strip().split(None,1)
                if len(parts)==2 and str(runtime/'node0') in parts[1] and ('btx-qt' in parts[1] or 'btxd' in parts[1]):
                    pid=int(parts[0]); owned.append(pid)
                    try:os.kill(pid,signal.SIGTERM)
                    except ProcessLookupError:pass
            result['cleanup_sigterm_owned_pids']=list(owned)
            until=time.monotonic()+10
            while owned and time.monotonic()<until:
                owned=[pid for pid in owned if Path('/proc',str(pid)).exists()];time.sleep(0.2)
            for pid in owned:
                try:os.kill(pid,signal.SIGKILL)
                except ProcessLookupError:pass
            result['cleanup_terminated_owned_pids']=owned
            shutil.rmtree(runtime,ignore_errors=True)
    result.update(exit=code,elapsed_seconds=round(time.monotonic()-start,3))
    assert code==0
    observation=json.loads((out/'observation.json').read_text())
    assert observation['status']=='observation_complete'
    assert observation['rpc_control_matches_baseline']
    assert observation['native_action_relocked']
    assert observation['native_unlock_required_rpc_succeeded']
    result.update(status='observation_complete',qt_accounting_matches_baseline=observation['qt_accounting_matches_baseline'],interpretation=observation['interpretation'])
except Exception as error:
    result.update(status='setup_or_control_failure',error=repr(error))
    raise
finally:
    (out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
