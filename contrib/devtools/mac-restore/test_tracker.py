import json, os, pathlib, subprocess, sys, tempfile, time, signal
from process_tracker import OwnedProcesses
import process_tracker

CHILD = '''import os,signal,time
os.setpgid(0,0) if os.environ['KIND']=='group' else os.setsid()
mem=bytearray(32*1024*1024)
for i in range(0,len(mem),4096):mem[i]=1
signal.signal(signal.SIGINT,signal.SIG_IGN);signal.signal(signal.SIGTERM,signal.SIG_IGN)
open(os.environ['READY']+os.environ['KIND'],'w').write(str(os.getpid()))
time.sleep(40)
'''
ROOT = '''import os,subprocess,sys,time
for kind in ['group','session']:
 subprocess.Popen([sys.executable,'-c',os.environ['CHILD']],env=dict(os.environ,KIND=kind))
while not os.path.exists(os.environ['EXIT']):time.sleep(.05)
'''
def main():
    quick = subprocess.Popen([sys.executable, '-c', 'pass'], start_new_session=True)
    quick.wait(timeout=5)
    completed = OwnedProcesses(quick)
    assert completed.update()['processes'] == [] and completed.stop()['processes'] == []
    # Reproduce the review catch: initialization must not launch a ps call outside
    # the protected observation/cleanup path. A one-shot observation error must
    # still stop the owned command, while preserving the unrelated sentinel.
    faultproc = subprocess.Popen([sys.executable, '-c', 'import time;time.sleep(40)'], start_new_session=True)
    original = process_tracker.snapshot
    calls = [0]
    def fail_once():
        calls[0] += 1
        if calls[0] == 1: raise subprocess.TimeoutExpired('ps fixture', .01)
        return original()
    process_tracker.snapshot = fail_once
    failure_tracker = None
    try:
        failure_tracker = OwnedProcesses(faultproc)
        try:
            failure_tracker.update()
            raise AssertionError('Observation fault was not injected')
        except subprocess.TimeoutExpired:
            pass
        finally:
            assert failure_tracker.stop()['processes'] == []
        assert faultproc.poll() is not None
    finally:
        process_tracker.snapshot = original
        if faultproc.poll() is None:
            faultproc.kill(); faultproc.wait(timeout=5)
    with tempfile.TemporaryDirectory(prefix='mac-tracker-') as td:
        root = pathlib.Path(td)
        sentinel = subprocess.Popen([sys.executable, '-c', 'import time;time.sleep(40)'], start_new_session=True)
        proc = subprocess.Popen([sys.executable,'-c',ROOT], env=dict(os.environ,CHILD=CHILD,READY=str(root/'ready-'),EXIT=str(root/'exit')), start_new_session=True)
        tracker = OwnedProcesses(proc)
        try:
            end=time.monotonic()+10
            while time.monotonic()<end:
                measured=tracker.update()
                if all((root/('ready-'+k)).exists() for k in ['group','session']):break
                time.sleep(.05)
            else:raise AssertionError('Fixture children not ready')
            measured=tracker.update();pids=[int((root/('ready-'+k)).read_text()) for k in ['group','session']]
            assert set(pids)<=set(x['pid'] for x in measured['processes'])
            old_rss=sum(x['rss_bytes'] for x in measured['processes'] if x['pgid']==proc.pid)
            assert measured['rss_bytes']-old_rss>48*1024**2
            assert len(measured['process_groups'])>=3 and len(measured['sessions'])>=2
            (root/'exit').touch();proc.wait(timeout=5)
            orphan=tracker.update();assert set(pids)<=set(x['pid'] for x in orphan['processes'])
            clean=tracker.stop();assert clean['processes']==[] and sentinel.poll() is None
            return {'pass':True,'already_completed_command_handled':True,'initial_observation_error_cleanup':True,'old_single_group_misses_children':True,'old_group_rss_bytes':old_rss,'owned_rss_bytes':measured['rss_bytes'],'observed_groups':measured['process_groups'],'observed_sessions':measured['sessions'],'orphan_children_retained':True,'SIGKILL_escalation_and_cleanup':True,'unrelated_sentinel_preserved':True}
        finally:
            tracker.stop()
            sentinel.terminate();sentinel.wait(timeout=5)
if __name__=='__main__':
    result=main();print(json.dumps(result,indent=2))
