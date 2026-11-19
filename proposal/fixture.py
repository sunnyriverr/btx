"""Bounded native helper settings qualification; no wallet/node/peers or queued action execution.

Baseline records expected product defects while keeping setup/valid controls strict.
Candidate requires every contract check to pass. All roots are disposable.
"""
import argparse
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import socket
import subprocess
import tempfile
import time
from uuid import uuid4


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class Fixture:
    def __init__(self, binary, root, out):
        self.binary, self.root, self.out = binary, root, out
        self.endpoint = root / 'rpc.sock'
        self.model = root / 'model'
        self.model.mkdir()
        self.calls = []
        self.starts = 0

    def rpc(self, method, *params):
        payload = {'id': 'settings-qualification', 'method': method, 'params': list(params)}
        row = {'method': method, 'params': list(params)}
        self.calls.append(row)
        with socket.socket(socket.AF_UNIX) as conn:
            conn.settimeout(110)
            conn.connect(str(self.endpoint))
            conn.sendall(json.dumps(payload).encode() + b'\n')
            conn.shutdown(socket.SHUT_WR)
            with conn.makefile('rb') as wire:
                line = wire.readline(2 * 1024 * 1024)
            row['raw_reply'] = line.decode('utf-8', errors='replace')
            assert line.endswith(b'\n'), 'missing/oversized RPC reply'
            reply = json.loads(line)
        row['reply'] = reply
        return reply

    def ok(self, method, *params):
        reply = self.rpc(method, *params)
        assert reply.get('error') is None, reply
        return reply['result']

    def watches(self):
        return self.ok('listmodelwatches')['watches']

    def peek(self):
        row = self.ok('getmodelwatchactions', {'drain': False})
        assert row['drained'] is False and row['executed_free_downloads'] is False, row
        assert row['automatic_spend_atoms'] == 0 and row['actions'] == [], row
        return row

    @contextmanager
    def running(self):
        self.starts += 1
        env = {k: v for k, v in os.environ.items()
               if not k.startswith(('BTX_', 'DYLD_', 'BITCOIN_'))}
        if os.environ.get('BTX_OPENSSL'):
            env['BTX_OPENSSL'] = os.environ['BTX_OPENSSL']
        logpath = self.out / f'helper-start-{self.starts}.log'
        with logpath.open('wb') as log:
            proc = subprocess.Popen([
                str(self.binary), f'-modeldir={self.model}',
                f'-modelrpcsocket={self.endpoint}', '-modelstorage=64MiB',
                '-modelbind=off', '-modellandiscovery=0', '-modelnatpmp=0', '-modelfollowpeers=0',
                '-modelseed=off', '-modelpreserverare=0', '-modeluploadlimit=1KiB',
            ], cwd=self.root, env=env, stdout=log, stderr=subprocess.STDOUT)
            try:
                deadline = time.monotonic() + 30
                while True:
                    assert proc.poll() is None, logpath.read_text(errors='replace')[-6000:]
                    try:
                        self.ok('listmodelwatches')
                        break
                    except (FileNotFoundError, ConnectionRefusedError):
                        if time.monotonic() >= deadline:
                            raise
                        time.sleep(.05)
                yield
                assert proc.poll() is None, logpath.read_text(errors='replace')[-6000:]
            finally:
                if proc.poll() is None:
                    proc.terminate()
                    try:
                        proc.wait(timeout=15)
                    except subprocess.TimeoutExpired:
                        proc.kill()
                        proc.wait(timeout=5)
                        raise AssertionError('helper exceeded clean shutdown bound')
                assert proc.returncode == 0, (proc.returncode, logpath.read_text(errors='replace')[-6000:])

    def finish(self):
        (self.out / 'calls.json').write_text(json.dumps(self.calls, indent=2) + '\n')


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--helper',type=Path,required=True);parser.add_argument('--out',type=Path,required=True);args=parser.parse_args()
    assert os.getuid()!=0, 'real delete-denial fixture must run unprivileged'
    args.out.mkdir(exist_ok=True,parents=True)
    r={'scope':'actual helper, FakeS3, disposable Unix RPC; no node/wallet/peers/real cloud','helper_sha256':sha(args.helper),'uid':os.getuid(),'complete':False,'checks':{}}
    def check(k,v):r['checks'][k]=bool(v)
    f=None
    try:
        with tempfile.TemporaryDirectory(prefix='detach-',dir='/tmp') as tmp:
            root=Path(tmp);f=Fixture(args.helper.resolve(),root,args.out)
            creds=root/'creds';creds.write_text('aws_access_key_id=TEST_KEY_NOT_REAL\naws_secret_access_key=TEST_SECRET_NOT_REAL\n');creds.chmod(0o600)
            with f.running():
                cfg={'endpoint':'https://detach-fixture.invalid','bucket':'fixture','provider':'GENERIC_S3','credential_ref':str(creds),'use_fake':True,'idempotency_key':'fixture-config'}
                attached=f.ok('setcloudstorage',cfg);assert attached['applied'] and attached['automatic_spend_atoms']==0,attached
                probe=f.ok('testcloudstorage');assert probe['probe_ok'],probe
                cloud=f.model/'cloud.json';before=cloud.read_bytes();budget=f.model/'cloud-budget.json';budget_before=budget.read_bytes()
                remote=f.model/'fakes3-objects.bin';assert remote.is_file() and remote.stat().st_size>0;remote_before=remote.read_bytes()
                unrelated=f.model/'unrelated-setting';unrelated.write_bytes(b'KEEP\n')
                migrate=f.ok('removemodelstorage',{'mode':'MIGRATE'});assert not migrate['executed'] and not migrate['detached'] and cloud.read_bytes()==before
                marker=f.model/'delete-check';marker.write_text('CHECK');f.model.chmod(0o500)
                try:
                    denied=False
                    try:marker.unlink()
                    except PermissionError:denied=True
                    assert denied,'delete fault is ineffective'
                    failed=f.rpc('removemodelstorage',{'mode':'DETACH'})
                    check('failed_detach_reports_IO_ERROR',failed.get('error') is not None and failed['error'].get('code')=='IO_ERROR')
                    assert cloud.read_bytes()==before,'failed detach lost config'
                finally:f.model.chmod(0o700)
                marker.unlink()
                ready=f.ok('getcloudstorageinfo');assert ready['configured'] and ready['automatic_spend_atoms']==0
                assert budget.read_bytes()==budget_before and remote.read_bytes()==remote_before
                check('failed_file_retained_and_live_configured',True)
            with f.running():
                assert f.ok('getcloudstorageinfo')['configured']
                detach=f.ok('removemodelstorage',{'mode':'DETACH'});assert detach['detached'] and not detach['remote_objects_deleted'] and detach['automatic_spend_atoms']==0
                assert not cloud.exists() and not f.ok('getcloudstorageinfo')['configured']
                again=f.ok('removemodelstorage',{'mode':'DETACH'});assert again['detached'] and not again['remote_objects_deleted']
                check('identical_retry_and_absent_detach',True)
            with f.running():
                assert not f.ok('getcloudstorageinfo')['configured']
                assert not cloud.exists() and remote.read_bytes()==remote_before and budget.read_bytes()==budget_before
                assert unrelated.read_bytes()==b'KEEP\n';check('detached_after_restart_objects_budget_and_unrelated_unchanged',True)
            r['complete']=True;r['clean_starts']=f.starts
    except Exception as exc:
        import traceback;r['error']=traceback.format_exc()
    finally:
        if f:f.finish()
        r['contract_pass']=r['complete'] and all(r['checks'].values());(args.out/'native-result.json').write_text(json.dumps(r,indent=2)+'\n')
    print(json.dumps(r,indent=2));return 0 if r['contract_pass'] else 1
if __name__=='__main__':raise SystemExit(main())
