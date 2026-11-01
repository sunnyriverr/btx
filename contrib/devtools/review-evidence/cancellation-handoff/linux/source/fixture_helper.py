#!/usr/bin/env python3
"""Private Unix-only helper fixture. No model execution or public network."""
from pathlib import Path
import json, os, signal, socket, sys, threading, time

args = dict(x[1:].split('=', 1) for x in sys.argv[1:] if x.startswith('-') and '=' in x)
root = Path(args['modeldir'])
root.mkdir(parents=True, exist_ok=True)
path = Path(args['modelrpcsocket'])
path.parent.mkdir(parents=True, exist_ok=True)
os.chmod(path.parent, 0o700)
lock = threading.Lock()

def event(kind, **data):
    with lock:
        with (root / 'fixture-events.jsonl').open('a') as f:
            f.write(json.dumps({'kind': kind, 'time': time.time(), **data}) + '\n')

def on_signal(signum, frame):
    event('signal', signum=signum)
    if not (root / 'fixture-ignore-term').exists():
        raise SystemExit(0)

signal.signal(signal.SIGTERM, on_signal)
signal.signal(signal.SIGINT, on_signal)

def reply(c, result=None, error=None):
    c.sendall(json.dumps({'result': result, 'error': error, 'id': 'model'}).encode() + b'\n')

def client(c):
    try:
        raw = b''
        while len(raw) < 8192:
            b = c.recv(8192)
            if not b:
                break
            raw += b
            if b'\n' in raw:
                break
        if not raw:
            return
        req = json.loads(raw)
        method = req['method']
        event('request', method=method)
        if method == 'fixture_ping':
            reply(c, {'pid': os.getpid(), 'alive': True})
            return
        if method == 'getmodel':
            if req['params'][0] == 'fixture-refusal':
                reply(c, error={'code': 'INVALID_PARAMETER', 'message': 'fixture refusal'})
                return
            delay = float((root / 'fixture-long-delay').read_text())
            (root / 'fixture-long-started').write_text(str(time.time()))
            time.sleep(delay)  # Deliberately silent, not a resetting partial-read timer.
            reply(c, {'fixture_long_reply': True, 'automatic_spend_atoms': 0})
            event('long-response', seconds=delay)
            return
        fault = (root / 'fixture-fault').exists()
        if fault:
            mode = (root / 'fixture-fault').read_text().strip()
            if mode == 'partial':
                c.sendall(b'{"result":')
            (root / ('fixture-stalled-' + method)).write_text(str(time.time()))
            event('stalled', method=method, mode=mode)
            while not (root / 'fixture-release').exists():
                if mode == 'partial':
                    c.sendall(b' ')
                time.sleep(.05)
            if mode == 'partial':
                c.sendall(b'{"helper_ready":true},"error":null}\n')
            else:
                reply(c, {'helper_ready': True})
            event('released', method=method)
        else:
            reply(c, {'helper_ready': True, 'advertised_host': False,
                      'public_host_reachable': False, 'automatic_spend_atoms': 0})
    except (BrokenPipeError, ConnectionResetError):
        event('disconnected')
    finally:
        c.close()

server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
server.bind(str(path))
os.chmod(path, 0o600)
server.listen(16)
(root / 'fixture-pid').write_text(str(os.getpid()))
event('ready', pid=os.getpid())
while True:
    if (root / 'fixture-pause-accept').exists():
        (root / 'fixture-accept-paused').touch()
        while (root / 'fixture-pause-accept').exists():
            time.sleep(.025)
    c, _ = server.accept()
    threading.Thread(target=client, args=(c,), daemon=True).start()
