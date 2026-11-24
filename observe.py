import json
import shutil
import signal
import socket
import subprocess
import sys
import time
from pathlib import Path

root, evidence = map(Path, sys.argv[1:])
install = json.loads((evidence / 'install.json').read_text())
base = '0104909051a017c9045faf7382627e89c5b83c4bbd3c1270706d5d2ef2ab0c87'
datadir = root / 'node'
datadir.mkdir()
with socket.socket() as listener:
    listener.bind(('127.0.0.1', 0))
    port = listener.getsockname()[1]
common = ['-chain=main', f'-datadir={datadir}', f'-rpcport={port}']
result = {'outcome': 'incomplete', 'stage': 'header', 'base': base, 'headers': 0, 'shutdowns': []}
process = None
started = time.monotonic()

def save(name, value):
    (evidence / (name + '.json')).write_text(json.dumps(value, indent=2) + '\n')

def rpc(method, *args, limit=10):
    cmd = [install['btx_cli'], *common, f'-rpcclienttimeout={limit}', method, *args]
    call = subprocess.run(cmd, text=True, capture_output=True, timeout=limit + 3)
    if call.returncode:
        raise RuntimeError(f'{method}: {call.stderr.strip()[:700]}')
    return call.stdout

def output(method, *args, limit=10):
    return json.loads(rpc(method, *args, limit=limit))

def start(offline=False):
    global process
    args = ['-rpcbind=127.0.0.1', '-listen=0', '-disablewallet=1', '-modelnet=0',
            '-swapnet=0', '-autoupdate=0', '-prune=4096']
    if offline:
        args += ['-networkactive=0']
    with (root / 'console.log').open('ab') as log:
        process = subprocess.Popen([install['btxd'], *common, *args], stdout=log, stderr=log)

def stop(force=False):
    global process
    if process is None:
        return
    if process.poll() is None:
        try:
            rpc('stop')
        except Exception:
            if not force:
                raise
            process.terminate()
    try:
        code = process.wait(timeout=55)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait()
        raise
    process = None
    result['shutdowns'].append(code)
    if code:
        raise RuntimeError(f'daemon exit {code}')

def disk_and_process():
    if process.poll() is not None:
        raise RuntimeError(f'daemon exited {process.returncode}')
    if shutil.disk_usage(root).free < 2 * 1024**3:
        raise RuntimeError('scratch disk reserve reached')

def chainstate():
    states = output('getchainstates')['chainstates']
    assert len(states) == 2
    assert states[-1]['snapshot_blockhash'] == base
    assert states[-1]['blocks'] >= 228000
    assert states[-1]['validated'] is False
    assert 'snapshot_blockhash' not in states[0]
    return states

def terminate(signum, _frame):
    raise InterruptedError(f'runner signal {signum}')

signal.signal(signal.SIGTERM, terminate)
try:
    start()
    while time.monotonic() - started < 6000:
        disk_and_process()
        try:
            info = output('getblockchaininfo', limit=3)
            assert info['chain'] == 'main'
            result.update(headers=info['headers'], blocks=info['blocks'])
            if info['headers'] >= 228000:
                header = output('getblockheader', base, limit=3)
                assert header['hash'] == base and header['height'] == 228000
                save('base-header', header)
                break
        except (RuntimeError, subprocess.TimeoutExpired) as error:
            result['header_last_rpc_error'] = str(error)
        save('progress', result)
        time.sleep(8)
    else:
        raise TimeoutError('exact base header was not observed within 100 minutes')

    signal.signal(signal.SIGALRM, terminate)
    signal.alarm(1200)
    result['stage'] = 'activation'
    save('progress', result)
    rpc('setnetworkactive', 'false')
    def verify_offline(name):
        network = output('getnetworkinfo')
        save(name, {'networkactive': network['networkactive'], 'connections': network['connections']})
        assert network['networkactive'] is False and network['connections'] == 0
    verify_offline('offline-at-load')
    loaded = output('loadtxoutset', str(root / 'assumeutxo-228000.dat'), limit=780)
    save('load', loaded)
    assert loaded['base_height'] == 228000 and loaded['tip_hash'] == base
    assert loaded['coins_loaded'] == 141474
    before = chainstate()
    save('before-restart', before)
    stop()

    result['stage'] = 'restart'
    start(offline=True)
    for _ in range(60):
        disk_and_process()
        try:
            output('getblockchaininfo', limit=3)
            break
        except (RuntimeError, subprocess.TimeoutExpired):
            time.sleep(2)
    else:
        raise TimeoutError('restarted daemon did not become ready')
    verify_offline('offline-after-restart')
    after = chainstate()
    save('after-restart', after)
    assert after[-1]['bestblockhash'] == before[-1]['bestblockhash'] == base
    assert after[0]['blocks'] >= before[0]['blocks']
    assert rpc('getblockhash', str(before[0]['blocks'])).strip() == before[0]['bestblockhash']
    if before[0]['blocks'] == after[0]['blocks']:
        assert before[0]['bestblockhash'] == after[0]['bestblockhash']
    stop()
    result.update(outcome='pass', stage='complete')
except Exception as error:
    result['error'] = f'{type(error).__name__}: {error}'
finally:
    try:
        stop(force=True)
    except Exception as error:
        result['cleanup_error'] = str(error)
    result['seconds'] = round(time.monotonic() - started, 2)
    save('result', result)
    print(json.dumps(result))
sys.exit(0 if result['outcome'] == 'pass' and result['shutdowns'] == [0, 0] else 1)
