"""One injected lock failure through the driver with a real disposable wallet."""
import json
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
from types import SimpleNamespace

from swapnet.drivers import UTXODriver
from swapnet.embedded import Host
from swapnet.errors import SwapError
from swapnet.journal import Journal
from swapnet.rpcclient import LocalRPC
from swapnet.store import Store

with tempfile.TemporaryDirectory(prefix='relock-core-') as tmp:
    root = Path(tmp)
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        port = sock.getsockname()[1]
    url = f'http://127.0.0.1:{port}'
    cookie = root / 'regtest/.cookie'
    with (root / 'daemon.log').open('wb') as log:
        daemon = subprocess.Popen(
            [sys.argv[1], '-regtest', f'-datadir={root}', f'-rpcport={port}',
             '-rpcbind=127.0.0.1', '-listen=0', '-connect=0', '-dnsseed=0',
             '-discover=0', '-fallbackfee=0.0002'], stdout=log, stderr=log)
    try:
        rpc = LocalRPC(url, cookie_path=str(cookie), timeout=4)
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:
            assert daemon.poll() is None, 'Core stopped during startup'
            try:
                if cookie.exists() and rpc('getblockchaininfo')['chain'] == 'regtest':
                    break
            except SwapError:
                pass
            time.sleep(0.3)
        else:
            raise TimeoutError('Core regtest RPC did not become ready')
        rpc('createwallet', 'funding')
        wallet = LocalRPC(url + '/wallet/funding', cookie_path=str(cookie), timeout=4)
        rpc('generatetoaddress', 105, wallet('getnewaddress'))
        coins = wallet('listunspent')
        reserved, existing, sibling = [
            {'txid': c['txid'], 'vout': c['vout']} for c in coins[:3]
        ]
        assert wallet('lockunspent', False, [existing], True)
        asset = 'btc:' + rpc('getblockhash', 0) + ':0:native'
        store = Store(root / 'journal' / 'state.sqlite')
        try:
            journal = Journal(store)
            rows = [(asset, f"{c['txid']}:{c['vout']}", 'ab' * 32)
                    for c in (reserved, existing, sibling)]
            store.db.executemany('INSERT INTO coinlocks VALUES(?,?,?)', rows)
            injected = False
            tries = []

            def one_failure(method, *args):
                global injected
                if method == 'lockunspent' and args[1] == [reserved]:
                    tries.append('injected' if not injected else 'forwarded')
                    if not injected:
                        injected = True
                        raise SwapError('RPC_UNAVAILABLE', 'test callback failure')
                return wallet(method, *args)

            driver = UTXODriver(asset, rpc, one_failure, wallet, journal, None,
                                network='regtest', hrp='bcrt')
            host = Host.__new__(Host)
            host.drivers = {asset: driver}
            host._relock_pending = {asset}
            host.startup_errors = {}
            host.app = SimpleNamespace(tick=lambda: None)
            host.tick()
            first = wallet('listlockunspent')
            assert existing in first and sibling in first and reserved not in first, first
            assert asset in host._relock_pending and host.startup_errors[asset] == 'COINLOCK'
            host.tick()
            second = wallet('listlockunspent')
            assert all(c in second for c in (reserved, existing, sibling)), second
            assert asset not in host._relock_pending and asset not in host.startup_errors
            assert tries == ['injected', 'forwarded']
            assert set(store.db.execute('SELECT * FROM coinlocks')) == set(rows)
            print(json.dumps({'result':'PASS', 'core_version':rpc('getnetworkinfo')['subversion'],
                              'first':first, 'second':second, 'attempts':tries,
                              'wallet_reply_simulated_only_for_first_lock':True}))
        finally:
            store.db.close()
    finally:
        if daemon.poll() is None:
            daemon.terminate()
            assert daemon.wait(timeout=20) == 0
