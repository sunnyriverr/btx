"""Observe one default-peer mainnet header sync in a fresh datadir."""
import base64
import hashlib
import json
from pathlib import Path
import re
import shutil
import signal
import socket
import subprocess
import tempfile
import time
import urllib.request

root = Path.cwd()
daemon = root / 'btxd'
inputs = json.loads((root / 'input.json').read_text())
sha = hashlib.file_digest(daemon.open('rb'), 'sha256').hexdigest()
assert sha == inputs['daemon_sha256']
assert shutil.disk_usage(root).free >= 4 * 1024**3
out = root / 'receipt'
out.mkdir(exist_ok=True)
result = dict(source=inputs['source'], daemon_sha256=sha, observed_seconds=0,
              outcome='inconclusive', presync_height=0, ordinary_height=0, headers=0,
              outbound_peers_max=0, inbound_peers_max=0, abort_counts={},
              rpc_seen=False, shutdown_clean=False, owned_process_exited=False)
(out / 'sync.json').write_text(json.dumps(result, indent=2)+'\n')
scratch = Path(tempfile.mkdtemp(prefix='btx-headers-', dir=root))
home = scratch / 'home'
home.mkdir(mode=0o700)
with socket.socket() as listener:
    listener.bind(('127.0.0.1',0))
    port = listener.getsockname()[1]
cookie = scratch / '.cookie'
opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))

def rpc(method):
    secret = base64.b64encode(cookie.read_bytes().strip()).decode()
    req = urllib.request.Request(f'http://127.0.0.1:{port}', json.dumps(
        {'jsonrpc':'1.0','id':1,'method':method,'params':[]}).encode(),
        {'Authorization':'Basic '+secret,'Content-Type':'application/json'})
    with opener.open(req, timeout=2) as response:
        row = json.load(response)
    if row.get('error'):
        raise RuntimeError(method)
    return row['result']

pre = re.compile(r'Pre-synchronizing blockheaders, height: (\d+)')
ordinary = re.compile(r'(?<!Pre-)Synchronizing blockheaders, height: (\d+)')
abort = re.compile(r'Initial headers sync aborted with peer=\d+: (.+)')
args = [str(daemon), '-chain=main', f'-datadir={scratch}', '-disablewallet',
        '-listen=0', '-modelnet=0', '-swapnet=0', '-autoupdate=0',
        f'-rpcport={port}', '-rpcbind=127.0.0.1', '-debug=net',
        '-printtoconsole=1', '-debuglogfile=0']
result['profile'] = ['main', 'fresh datadir', 'wallet disabled', 'outbound default peers',
                     'ModelNet, SwapNet and updater disabled', 'stock consensus and limits']

def interrupted(signum, frame):
    raise InterruptedError(f'signal {signum}')

signal.signal(signal.SIGTERM, interrupted)
log = scratch / 'console.log'
process = None
start = time.monotonic()
try:
    with log.open('wb') as stream:
        process = subprocess.Popen(args, stdout=stream, stderr=subprocess.STDOUT,
                                   env={'PATH':'/usr/bin:/bin', 'HOME':str(home), 'LC_ALL':'C'})
    with log.open('r', errors='replace') as stream:
        while time.monotonic()-start < 1200:
            for line in stream:
                for pattern, key in ((pre, 'presync_height'),(ordinary, 'ordinary_height')):
                    if match := pattern.search(line):
                        result[key] = max(result[key], int(match[1]))
                if match := abort.search(line):
                    reason = match[1].split(' at height=')[0][:150]
                    counts = result['abort_counts']
                    counts[reason] = counts.get(reason,0)+1
            if process.poll() is not None:
                result['stop_reason'] = 'daemon exited before sync verdict'
                break
            try:
                chain = rpc('getblockchaininfo')
                assert chain['chain'] == 'main'
                result['rpc_seen'] = True
                result['headers'] = max(result['headers'], chain['headers'])
                peers = rpc('getpeerinfo')
                inbound = sum(bool(peer['inbound']) for peer in peers)
                result['inbound_peers_max'] = max(inbound,result['inbound_peers_max'])
                result['outbound_peers_max'] = max(len(peers)-inbound,result['outbound_peers_max'])
                assert inbound == 0
            except (OSError, ValueError, RuntimeError):
                pass
            if result['ordinary_height'] >= 185000 and result['headers'] >= result['ordinary_height']:
                result.update(outcome='pass',stop_reason='ordinary header sync confirmed by log and RPC')
                break
            if log.stat().st_size > 128*1024**2 or shutil.disk_usage(root).free < 2*1024**3:
                result['stop_reason'] = 'scratch disk bound'
                break
            time.sleep(2)
        else:
            result['stop_reason'] = '20-minute observation cap'
except Exception as exc:
    result['stop_reason'] = type(exc).__name__
finally:
    result['observed_seconds'] = round(time.monotonic()-start, 2)
    if process is not None:
        result['alive_at_shutdown'] = process.poll() is None
        if process.poll() is None:
            try:
                rpc('stop')
                result['shutdown_clean'] = process.wait(timeout=30)==0
            except (OSError, ValueError, RuntimeError, subprocess.TimeoutExpired):
                if process.poll() is None:
                    process.terminate()
                try:
                    process.wait(timeout=15)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=5)
        result['owned_process_exited'] = process.poll() is not None
        result['exit'] = process.returncode
    if not result['shutdown_clean'] and result['outcome']=='pass':
        result.update(outcome='inconclusive',stop_reason='transition observed but clean shutdown not verified')
    (out/'sync.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))
