"""Check result gates and exercise the shared pacing clock on two TCP flows."""
from concurrent.futures import ThreadPoolExecutor
from socket import create_connection
from socketserver import BaseRequestHandler, ThreadingTCPServer
from threading import Thread
import time

from native_fixture import verdict
from relay import Relay, pacing


def check_verdicts():
    common = dict.fromkeys(
        ('binary_verified', 'pacing_verified', 'partial_verified', 'route_verified',
         'a_ready', 'b_stopped', 'clean_cleanup', 'same_job', 'exact_completion'), True)
    recovered = dict(common, a_attempt=True, same_job_complete=True)
    stalled = dict(common, a_attempt=False, worker_b_retry=True, observed_seconds=20,
                   still_pending=True, control_complete=True)
    assert verdict(recovered) == 'RECOVERED'
    assert verdict(stalled) == 'STALLED'
    for valid in (recovered, stalled):
        for field in common:
            assert verdict(dict(valid, **{field: False})) == 'INCONCLUSIVE', field
    for field, value in [('worker_b_retry', False), ('observed_seconds', 19),
                         ('control_complete', False), ('a_attempt', True)]:
        assert verdict(dict(stalled, **{field: value})) == 'INCONCLUSIVE', field


def check_pacing():
    payload = bytes(range(256)) * 128
    rate = 32768

    class Server(BaseRequestHandler):
        def handle(self):
            assert self.request.recv(1) == b'x'
            self.request.sendall(payload)
            self.request.recv(1)

    with ThreadingTCPServer(('127.0.0.1', 0), Server) as server:
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()
        relay = Relay(server.server_address[1], rate=rate)
        try:
            def fetch():
                with create_connection(('127.0.0.1', relay.port), timeout=8) as client:
                    client.sendall(b'x')
                    data = b''
                    while len(data) < len(payload):
                        chunk = client.recv(16384)
                        assert chunk
                        data += chunk
                    return data

            start = time.monotonic()
            with ThreadPoolExecutor(max_workers=2) as pool:
                assert list(pool.map(lambda _: fetch(), range(2))) == [payload, payload]
            assert time.monotonic() - start >= 1.49
            assert sum(count for _, count in relay.samples) == 2 * len(payload)
            assert pacing(relay.samples, rate)
            assert not pacing([(0, 16384), (.1, 16384)], rate)
        finally:
            relay.close()
            server.shutdown()
            thread.join(5)


if __name__ == '__main__':
    check_verdicts()
    check_pacing()
    print('Offline verdict gates and two-flow aggregate TCP pacing passed.')
