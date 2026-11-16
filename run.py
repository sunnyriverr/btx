"""One retained-binary normal-suite run. No compilation or wallet/log uploads."""
from pathlib import Path
import csv
import hashlib
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import time

root = Path.cwd()
records = root / 'records'
producer = json.loads((root / 'saved/producer.json').read_text())
assert producer['source_identity'] == '1e2f8b5f12295002334d3390c12cac0bb4ae2aff'
def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()
inputs = json.loads((root / 'inputs.json').read_text())
for name, digest in inputs.items():
    source = root / 'suite-inputs' / name
    assert sha(source) == digest
    (root / 'source/test/functional' / name).write_bytes(source.read_bytes())
for name, digest in producer['binary_sha256'].items():
    assert sha(root / 'build/bin' / name) == digest
# Configure normally creates per-script links; add only this new test link.
link = root / 'build/test/functional/wallet_bcp1_recovery.py'
assert not link.exists() and not link.is_symlink()
link.symlink_to(root / 'source/test/functional/wallet_bcp1_recovery.py')
assert (root / 'build/test/functional/wallet_bcp1_recovery.py').is_file()
private = root / 'deposit-private'
assert not private.exists()
private.mkdir(mode=0o700)
(private / 'rt').mkdir()
env = dict(os.environ, XDG_RUNTIME_DIR=str(private / 'rt'))
for variable, binary in [('BTXD','btxd'), ('BITCOIND','btxd'), ('BTXCLI','btx-cli'), ('BITCOINCLI','btx-cli')]:
    env[variable] = str(root / 'build/bin' / binary)
command = [sys.executable, str(root / 'source/test/functional/test_runner.py'),
           'wallet_bcp1_recovery.py', '--configfile='+str(root / 'build/test/config.ini'),
           '-j1', '--tmpdirprefix='+str(private), '--resultsfile='+str(private / 'results.csv'), '--nocleanup']
receipt = dict(source=producer['source_identity'], binaries=producer['binary_sha256'], inputs=inputs,
               normal_runner=True, compiled=False, deadline_seconds=600, scratch_limit_bytes=512*2**20)
started=time.monotonic();process=None;reason=None;peak=0

def group_exists(pid):
    try: os.killpg(pid, 0); return True
    except ProcessLookupError: return False

def stop_owned(process):
    assert process.pid != os.getpgrp()
    for sig, seconds in [(signal.SIGTERM, 10), (signal.SIGKILL, 5)]:
        if not group_exists(process.pid): break
        os.killpg(process.pid, sig)
        end=time.monotonic()+seconds
        while group_exists(process.pid) and time.monotonic()<end:
            process.poll(); time.sleep(.1)
    process.wait(timeout=5)
    return not group_exists(process.pid)

try:
    with (private / 'runner.log').open('w') as log:
        process=subprocess.Popen(command, cwd=root, env=env, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
        while process.poll() is None:
            peak=max(peak,sum(p.stat().st_size for p in private.rglob('*') if p.is_file() and not p.is_symlink()))
            if time.monotonic()-started>600: reason='DEADLINE'
            elif peak>512*2**20: reason='SCRATCH_LIMIT'
            elif shutil.disk_usage(root).free<1.25*2**30: reason='DISK_RESERVE'
            if reason: break
            time.sleep(1)
    receipt['group_absent']=stop_owned(process)
    receipt['exit_code']=process.returncode
    rows=list(csv.DictReader((private / 'results.csv').open())) if (private / 'results.csv').exists() else []
    receipt['results_csv']=rows
    receipt['stop_reason']=reason
    receipt['passed']=not reason and receipt['group_absent'] and process.returncode==0 and len(rows)==2 and all(r['status']=='Passed' for r in rows) and rows[0]['test']=='wallet_bcp1_recovery.py --descriptors' and rows[1]['test']=='ALL'
    raw=(private / 'runner.log').read_text(errors='replace')
    # Only source locations and exception names; never retain wallet/RPC dumps.
    receipt['failure_frames']=[dict(file=f.replace(str(root),'WORKSPACE'),line=int(n),function=fn)
         for f,n,fn in re.findall(r'File "([^"\n]+)", line (\d+), in ([^\n]+)', raw)][-12:]
    receipt['exception_classes']=re.findall(r'(?m)^([A-Za-z_]\w*(?:Error|Exception))(?=:|$)',raw)[-5:]
finally:
    if process is not None and group_exists(process.pid): receipt['group_absent']=stop_owned(process)
    if process is None or receipt.get('group_absent'): shutil.rmtree(private)
    receipt.update(elapsed_seconds=round(time.monotonic()-started,2),peak_sampled_private_bytes=peak,
                   private_data_removed=not private.exists(),raw_logs_uploaded=False)
    for name,digest in producer['binary_sha256'].items(): assert sha(root / 'build/bin' / name)==digest
    (records / 'deposit-result.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps(receipt),flush=True)
raise SystemExit(0 if receipt.get('passed') else 1)
