from pathlib import Path
import hashlib
import json
import os
import shutil
import signal
import socket
import subprocess
import time


MAX_RPC_BYTES = 1024 * 1024


def sha_bytes(data):
    return hashlib.sha256(data).hexdigest()


def sha(path):
    return sha_bytes(path.read_bytes())


def require(ok, message):
    if not ok:
        raise RuntimeError(message)


class Helper:
    """Adapted from the delivered #495 real Linux Unix-socket fixture."""
    def __init__(self, binary, root, output, label):
        self.binary = binary.resolve()
        self.root, self.output, self.label = root, output, label
        self.store = root / 'modeldir'
        self.store.mkdir(parents=True)
        self.sock = root / 'rpc.sock'
        self.proc = self.log = None
        self.seq = self.starts = 0
        self.transcript, self.cleanup_signals = [], []

    def start(self):
        require(self.proc is None and not self.sock.exists(), 'owned helper not stopped')
        self.starts += 1
        self.log = (self.output / f'{self.label}-{self.starts}.log').open('wb')
        home = self.root / 'home'
        home.mkdir(exist_ok=True)
        args = [str(self.binary), '-modeldir=' + str(self.store),
                '-modelrpcsocket=' + str(self.sock), '-modelstorage=8MiB',
                '-modellandiscovery=0', '-modelfollowpeers=0', '-modelnatpmp=0',
                '-modelhost=0', '-modelseed=off', '-pwcchain=regtest']
        self.proc = subprocess.Popen(args, stdout=self.log, stderr=subprocess.STDOUT,
            start_new_session=True, restore_signals=False,
            env=dict(os.environ, **getattr(self, "extra_env", {}), HOME=str(home),
                XDG_DATA_HOME=str(home / 'data'), XDG_RUNTIME_DIR=str(self.root)))
        until = time.monotonic() + 30
        while not self.sock.exists():
            require(self.proc.poll() is None and time.monotonic() < until,
                    'helper startup failed or exceeded 30s')
            time.sleep(.1)
        require(Path(f'/proc/{self.proc.pid}/exe').resolve() == self.binary,
                'Linux process does not use the pinned binary')
        info = self.ok('getmodelnetworkinfo', [])
        require(info['follow_configured_peers'] is False, 'peer following enabled')

    def rpc(self, method, params):
        self.seq += 1
        request_id = self.seq
        request = {'jsonrpc': '1.0', 'id': request_id, 'method': method, 'params': params}
        with socket.socket(socket.AF_UNIX) as client:
            client.settimeout(10)
            client.connect(str(self.sock))
            client.sendall(json.dumps(request).encode() + b'\n')
            client.shutdown(socket.SHUT_WR)
            with client.makefile('rb') as stream:
                raw = stream.read(MAX_RPC_BYTES + 1)
        require(len(raw) <= MAX_RPC_BYTES, 'RPC response exceeded fixture bound')
        response = json.loads(raw)
        require(response['id'] == request_id, 'RPC id mismatch')
        self.transcript.append({'at': time.time(), 'request': request, 'response': response})
        return response

    def ok(self, method, params):
        answer = self.rpc(method, params)
        require(answer.get('error') is None, f'{method} legitimate control failed: {answer}')
        return answer['result']

    def stop(self):
        if self.proc is None:
            return
        require(self.proc.poll() is None, 'helper exited unexpectedly')
        self.proc.send_signal(signal.SIGTERM)
        self.proc.wait(timeout=25)
        require(self.proc.returncode == 0 and not self.sock.exists(),
                'helper shutdown was not clean')
        self.proc = None
        self.log.close()
        self.log = None

    def cleanup(self):
        try:
            self.stop()
        finally:
            if self.proc is not None and self.proc.poll() is None:
                self.cleanup_signals.append('SIGKILL')
                os.killpg(self.proc.pid, signal.SIGKILL)
                self.proc.wait(timeout=10)
            if self.log:
                self.log.close()
            require(self.proc is None or self.proc.poll() is not None, 'owned process left alive')
            shutil.rmtree(self.root)


