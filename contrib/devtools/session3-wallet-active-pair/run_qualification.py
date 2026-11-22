"""Future authorized native entry; retained binaries, private scratch, sanitized evidence."""
import argparse,configparser,hashlib,json,os,shutil,signal,subprocess,sys,tempfile,time
from pathlib import Path
from collector import assess,read_progress,public_completed_stages
from restore_binaries import BINARY,SOURCE
from diagnostics import collect_diagnostics,exception_kind

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def install_interrupt_handlers(state):
    def interrupted(signum, frame):
        state['signal']=signum
        for sig in (signal.SIGTERM,signal.SIGINT):signal.signal(sig,signal.SIG_IGN)
        raise InterruptedError('Qualification controller interrupted')
    for sig in (signal.SIGTERM,signal.SIGINT):signal.signal(sig,interrupted)


def stop_group(process):
    pgid=process.pid
    process.poll()  # Reap our own leader before checking group presence.
    try:os.killpg(pgid,0)
    except ProcessLookupError:return True
    try:os.killpg(pgid,signal.SIGTERM)
    except ProcessLookupError:return True
    end=time.monotonic()+10
    while time.monotonic()<end:
        process.poll()
        try:os.killpg(pgid,0)
        except ProcessLookupError:return True
        time.sleep(0.1)
    try:os.killpg(pgid,signal.SIGKILL)
    except ProcessLookupError:return True
    end=time.monotonic()+5
    while time.monotonic()<end:
        process.poll()
        try:os.killpg(pgid,0)
        except ProcessLookupError:return True
        time.sleep(0.1)
    return False

def main():
    p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--binaries',type=Path,required=True);p.add_argument('--records',type=Path,required=True);p.add_argument('--packet-repository',type=Path,required=True);a=p.parse_args()
    if (a.records.resolve()/'RESULT.json').exists():p.error('Preserve prior results')
    interruption={'signal':None};install_interrupt_handlers(interruption)
    a.source=a.source.resolve();a.binaries=a.binaries.resolve();a.records=a.records.resolve();a.records.mkdir(parents=True,exist_ok=True)
    proposal=Path(__file__).resolve().parent
    expected=json.loads((proposal/'INPUTS.json').read_text())
    result={'status':'FAIL_OR_INCOMPLETE','reason':'SETUP_NOT_FINISHED','native_product_verdict':'UNQUALIFIED'}
    progress_error=None
    diagnostic_hints={"kind":"NOT_COLLECTED","raw_logs_retained":False}
    controller_exception_class=None
    code=None;timed_out=False;cleanup_ok=False;provenance_ok=False;process=None;stages=[];private=None;trace_lines=[];started=time.monotonic()
    try:
        assert sys.platform=='linux' and os.uname().machine=='x86_64' and sys.version_info[:2]==(3,12)
        assert subprocess.check_output(['git','-C',str(a.source),'rev-parse','HEAD'],text=True).strip()==SOURCE
        for name,h in expected['packet_files'].items():assert sha(proposal/name)==h
        assert sha(a.packet_repository/expected['workflow_path'])==expected['workflow_sha256']
        for name,h in expected['framework_files'].items():assert sha(a.source/name)==h
        assert {name:sha(a.binaries/name)for name in BINARY}==BINARY
        assert shutil.disk_usage(a.records).free>=2*1024**3
        with tempfile.TemporaryDirectory(prefix='btx917-',dir='/tmp')as temp:
            private=Path(temp);(private/'home').mkdir();(private/'build/bin').mkdir(parents=True)
            for name in BINARY:(private/'build/bin'/name).symlink_to(a.binaries/name)
            config=private/'config.ini'
            config.write_text('[environment]\nCLIENT_NAME=BTX\nCLIENT_BUGREPORT=not-used\nSRCDIR='+str(a.source)+'\nBUILDDIR='+str(private/'build')+'\nEXEEXT=\nRPCAUTH='+str(a.source/'share/rpcauth/rpcauth.py')+'\n[components]\nENABLE_WALLET=true\nUSE_SQLITE=true\nUSE_BDB=false\nENABLE_CLI=true\nENABLE_BITCOIND=true\nENABLE_MODELNET=true\nENABLE_ZMQ=false\nENABLE_EXTERNAL_SIGNER=false\n')
            shim=private/'no-build';shim.mkdir();guard=shim/'cmake'
            guard.write_text('#!/bin/sh\nprintf "blocked\\n" >> "$BTX_NO_BUILD_LOG"\nexit 125\n');guard.chmod(0o755)
            for name in ['ninja','make','cc','gcc','g++','clang','clang++','c++']:(shim/name).symlink_to('cmake')
            env={'PATH':str(shim)+':/usr/bin:/bin','HOME':str(private/'home'),'LC_ALL':'C','PYTHONDONTWRITEBYTECODE':'1','PYTHONUNBUFFERED':'1',
                 'PYTHONPATH':str(a.source/'test/functional'),'TMPDIR':str(private),'XDG_RUNTIME_DIR':str(private),
                 'BTX917_PROGRESS_FILE':str(private/'progress.jsonl'),'BTX_NO_BUILD_LOG':str(private/'build-attempts'),
                 'BTXD':str(a.binaries/'btxd'),'BTXCLI':str(a.binaries/'btx-cli'),'NO_PROXY':'127.0.0.1,localhost'}
            argv=[sys.executable,'-B',str(proposal/'wallet_active_pair_recovery.py'),'--configfile='+str(config),'--descriptors',
                  '--timeout-factor=1','--portseed=917','--tmpdir='+str(private/'regtest'),'--nocleanup']
            with (private/'private-run.log').open('wb')as log:
                process=subprocess.Popen(argv,cwd=a.source,env=env,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
                try:code=process.wait(timeout=900)
                except subprocess.TimeoutExpired:timed_out=True
                finally:
                    cleanup_ok=stop_group(process)
                    try:process.wait(timeout=5)
                    except subprocess.TimeoutExpired:process.kill();process.wait(timeout=5);cleanup_ok=False
                    # Capture safe completed evidence even while an interruption unwinds.
                    diagnostic_hints=collect_diagnostics(private)
                    trace_lines=sorted({frame['line']for entry in diagnostic_hints['sources']
                                        for frame in entry.get('frames',[])
                                        if frame['file']=='wallet_active_pair_recovery.py'})
                    try:stages=read_progress(private/'progress.jsonl')
                    except (ValueError,UnicodeError)as error:
                        progress_error=exception_kind(type(error).__name__)
                        prefix=[]
                        for line in (private/'progress.jsonl').read_text(errors='replace').splitlines():
                            try:prefix.append(json.loads(line))
                            except ValueError:break
                        stages=public_completed_stages(prefix)
            provenance_ok=progress_error is None and not (private/'build-attempts').exists() and {name:sha(a.binaries/name)for name in BINARY}==BINARY
            result=assess(code,stages,timed_out=timed_out,cleanup_ok=cleanup_ok,provenance_ok=provenance_ok)
        cleanup_ok=cleanup_ok and not private.exists()
        if not cleanup_ok:result.update(status='FAIL_OR_INCOMPLETE',reason='CLEANUP_FAILURE',native_product_verdict='UNQUALIFIED')
    except Exception as error:
        controller_exception_class=exception_kind(type(error).__name__)
        result=assess(code,stages,timed_out=timed_out,cleanup_ok=cleanup_ok,provenance_ok=provenance_ok)
        result.update(status='FAIL_OR_INCOMPLETE',reason='SETUP_OR_COLLECTION_'+controller_exception_class,native_product_verdict='UNQUALIFIED')
    finally:
        if process is not None:
            cleanup_ok=stop_group(process) and cleanup_ok
        if process is not None and not cleanup_ok:
            result.update(status="FAIL_OR_INCOMPLETE",reason="FINAL_CLEANUP_FAILURE",native_product_verdict="UNQUALIFIED")
        result.update(source=SOURCE,fixture_sha256=sha(proposal/'wallet_active_pair_recovery.py'),binary_sha256=BINARY,
                      native_exit=code,native_timed_out=timed_out,external_interrupt=interruption['signal'],progress_error=progress_error,scratch_removed=bool(private and not private.exists()),
                      cleanup_ok=cleanup_ok,fixture_trace_lines=trace_lines,diagnostic_hints=diagnostic_hints,
                      controller_exception_class=controller_exception_class,elapsed_seconds=round(time.monotonic()-started,3),
                      profile='two-node loopback diagnostic regtest; transparentcoinbase; MatMul activation overrides; SwapNetoff',
                      no_full_release_claim=True)
        (a.records/'RESULT.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'status':result['status'],'result':str(a.records/'RESULT.json')}))
    return 0 if result['status']=='PASS'else 1
if __name__=='__main__':sys.exit(main())
