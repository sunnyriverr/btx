#!/usr/bin/env python3
"""Private macOS actual-helper connection probe. No peer authentication/models.

The only allowed IP destinations are this computer's loopback and selected own
private IPv4 address. Numeric address is selected from existing interfaces; no
interface, route, firewall, or machine settings are changed. All scratch identities
are disposable and are never included in the evidence.
"""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import socket
import struct
import subprocess
import tempfile
import time

HERE = Path(__file__).resolve().parent
BINARY = HERE.parent / 'modelnet-integration-2026-10-31/baseline-btx-modeld'
EXPECTED = 'ec92facce2c381daa59c4ddabafc9d3f7a7d69d2b44279c3014df50712acf200'


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def rpc(path, method):
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as c:
        c.settimeout(2)
        c.connect(str(path))
        c.sendall(json.dumps({'jsonrpc': '1.0', 'id': 1, 'method': method, 'params': []}).encode() + b'\n')
        data = b''
        while b'\n' not in data:
            part = c.recv(65536)
            if not part:
                break
            data += part
            require(len(data) < 1024 * 1024, 'unexpected RPC size')
        reply = json.loads(data)
        require(not reply.get('error'), 'helper RPC error')
        return reply['result']


def selected_private_ip():
    text = subprocess.check_output(['/sbin/ifconfig', '-a'], text=True)
    allowed = False
    for line in text.splitlines():
        if line and not line[0].isspace():
            flags = line.split('<', 1)[-1].split('>', 1)[0].split(',')
            allowed = 'UP' in flags and 'MULTICAST' in flags and 'LOOPBACK' not in flags
        if allowed and re.search(r'\binet\s', line):
            words = line.split()
            ip = words[words.index('inet') + 1]
            b = ip.split('.')
            if b[0] == '10' or b[:2] == ['192', '168'] or (b[0] == '172' and 16 <= int(b[1]) <= 31):
                return ip
    raise RuntimeError('no eligible private IPv4 interface')


def profile():
    return ('(version 1)\n(allow default)\n'
            '(deny network-outbound (remote ip))\n'
            '(allow network-outbound (remote ip "localhost:*"))\n'
            '(deny network-inbound (remote ip))\n'
            '(allow network-inbound (remote ip "localhost:*"))\n')


def emit_beacon(ip, port, network='regtest', malformed=False):
    # Same canonical 48-byte layout as EncodeLanBeacon. Nonzero synthetic nonce.
    b = bytearray(b'BTXLAN\x01\x00' + network.encode().ljust(16, b'\x00') + struct.pack('!H', port) + b'\x00' * 6 + b'\xa5' * 16)
    require(len(b) == 48, 'fixture size')
    if malformed:
        b[26] = 1
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.bind((ip, 0))
        s.connect(('127.0.0.1', 29448))
        require(s.send(b) == len(b), 'local beacon send failed')


def wait_no_connection(listener, seconds):
    listener.settimeout(seconds)
    try:
        c, _ = listener.accept()
    except socket.timeout:
        return True
    c.close()
    return False


def main():
    global BINARY, HERE
    parser = argparse.ArgumentParser()
    parser.add_argument('--binary', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    BINARY = args.binary.resolve()
    HERE = args.output.resolve()
    HERE.mkdir(parents=True, exist_ok=True)
    result = {'started_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
              'scope': 'macOS native helper; own-host IP allowlist; zero storage, no configured peers, no completed TLS authentication/model retrieval or btxd',
              'binary_sha256': hashlib.sha256(BINARY.read_bytes()).hexdigest(), 'cases': []}
    ip = selected_private_ip()
    redact = lambda s: s.replace(ip, '<OWN_PRIVATE_IPV4>')
    try:
        with tempfile.TemporaryDirectory(prefix='btx-lan-', dir='/tmp') as scratch:
            scratch = Path(scratch)
            sb = scratch / 'local-only.sb'
            sb.write_text(profile())
            # Sandbox sensitivity check uses ONLY loopback routes: an allowed
            # 127.0.0.1 target and forbidden 127.0.0.2 target at the same listener.
            with socket.socket() as guard:
                guard.bind(('0.0.0.0', 0))
                guard.listen(8)
                code = ('import socket,json;out={};'
                        '\nfor h in ["127.0.0.1","127.0.0.2"]:'
                        '\n s=socket.socket();s.settimeout(1);out[h]=s.connect_ex((h,' + str(guard.getsockname()[1]) + '));s.close()'
                        '\nprint(json.dumps(out))')
                checked = subprocess.run(['/usr/bin/sandbox-exec', '-f', str(sb), '/usr/bin/python3', '-c', code], capture_output=True, text=True, timeout=5)
                require(checked.returncode == 0, 'sandbox control did not execute: ' + checked.stderr[:500])
                control = json.loads(checked.stdout)
                require(control['127.0.0.1'] == 0 and control['127.0.0.2'] == 1, 'sandbox IP boundary not enforced')
                result['sandbox_control'] = {'own_loopback_connect_succeeds': True, 'other_loopback_connect_EPERM': True}

            for kind in ['disabled', 'off_scope', 'valid_multicast']:
                enabled = kind != 'disabled'
                used = subprocess.run(['/usr/sbin/lsof', '-nP', '-iUDP:29448', '-F', 'p'], capture_output=True, text=True)
                require(not used.stdout.strip(), 'discovery port already used; do not interfere')
                case = {'kind': kind, 'lan_enabled_requested': enabled, 'configured_peers': 0, 'passed': True}
                result['cases'].append(case)
                modeldir = scratch / kind
                modeldir.mkdir(mode=0o700)
                path = modeldir / 'rpc.sock'
                with socket.socket() as listener, socket.socket() as reserve:
                    listener.bind((ip, 0)); listener.listen(8)
                    target_port = listener.getsockname()[1]
                    reserve.bind((ip, 0)); listen_port = reserve.getsockname()[1]
                    reserve.close()
                    command = ['/usr/bin/sandbox-exec', '-f', str(sb), str(BINARY),
                               '-modeldir=' + str(modeldir), '-modelrpcsocket=' + str(path),
                               '-modelbind=' + ip + ':' + str(listen_port), '-modelstorage=0',
                               '-modelnatpmp=0', '-pwcchain=regtest', '-modelhost=0',
                               '-modellandiscovery=' + str(int(enabled))]
                    logpath = scratch / (kind + '.log')
                    with logpath.open('wb') as log:
                        proc = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT,
                                                env={k: v for k, v in os.environ.items() if not k.startswith('BTX_')})
                        try:
                            ready = None
                            deadline = time.monotonic() + 12
                            while time.monotonic() < deadline:
                                require(proc.poll() is None, 'helper exited before ready')
                                if path.exists():
                                    try:
                                        ready = rpc(path, 'getmodelnetworkinfo')
                                        if ready.get('helper_ready') and ready.get('pq1_ready'):
                                            break
                                    except (OSError, ValueError):
                                        pass
                                time.sleep(0.1)
                            require(ready and ready.get('helper_ready') and ready.get('pq1_ready'), 'helper not ready')
                            native = ready.get('native_participation', {})
                            case['ready'] = {k: ready.get(k) for k in ['helper_ready', 'pq1_ready', 'automatic_spend_atoms', 'quota_bytes', 'follow_configured_peers']}
                            case['native_ready'] = {k: native.get(k) for k in ['lan_enabled', 'lan_error', 'hint_count']}
                            require(native.get('lan_enabled') is enabled, 'LAN open state differs from request')
                            require(ready.get('automatic_spend_atoms') in [0, '0'], 'nonzero automatic spend')
                            require(ready.get('quota_bytes') in [0, '0'], 'storage not disabled')
                            require(native.get('hint_count') == 0, 'unexpected existing hint')
                            require(wait_no_connection(listener, 6), 'unsolicited connection before any beacon')
                            case['before_beacon_no_connection_6s'] = True
                            if kind == 'off_scope':
                                emit_beacon(ip, target_port, network='main')
                                require(wait_no_connection(listener, 6), 'wrong network caused dial')
                                case['wrong_network_no_connection_6s'] = True
                                require(rpc(path, 'getmodelnetworkinfo')['native_participation']['hint_count'] == 0, 'wrong chain hint retained')
                                emit_beacon(ip, target_port, malformed=True)
                                require(wait_no_connection(listener, 6), 'malformed caused dial')
                                case['malformed_no_connection_6s'] = True
                                require(rpc(path, 'getmodelnetworkinfo')['native_participation']['hint_count'] == 0, 'malformed hint retained')
                            start = time.monotonic()
                            if kind == 'valid_multicast':
                                with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as witness, socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sender:
                                    witness.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                                    witness.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
                                    witness.bind(('0.0.0.0', 29448))
                                    witness.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, socket.inet_aton('239.192.0.35') + socket.inet_aton(ip))
                                    witness.setsockopt(socket.IPPROTO_IP, 20, 1)  # SDK IP_RECVIF
                                    witness.setsockopt(socket.IPPROTO_IP, 7, 1)   # SDK IP_RECVDSTADDR
                                    witness.settimeout(2)
                                    sender.bind((ip, 0))
                                    sender.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_IF, socket.inet_aton(ip))
                                    sender.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 0)
                                    sender.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_LOOP, 1)
                                    wire = b'BTXLAN\x01\x00' + b'regtest'.ljust(16, b'\x00') + struct.pack('!H', target_port) + b'\x00' * 6 + b'\xa5' * 16
                                    require(sender.sendto(wire, ('239.192.0.35', 29448)) == 48, 'TTL0 multicast send')
                                    packet, ancillary, flags, source = witness.recvmsg(128, 512)
                                    require(packet == wire and source[0] == ip, 'wrong positive witness packet')
                                    require(not flags & (socket.MSG_TRUNC | socket.MSG_CTRUNC), 'truncated witness metadata')
                                    incoming = None
                                    destination_group = False
                                    for level, option, data in ancillary:
                                        if level == socket.IPPROTO_IP and option == 20:
                                            incoming = socket.if_indextoname(struct.unpack_from('H', data, 2)[0])
                                        if level == socket.IPPROTO_IP and option == 7:
                                            destination_group = data == socket.inet_aton('239.192.0.35')
                                    require(incoming and incoming != 'lo0' and destination_group, 'positive not on real LAN interface')
                                    case['positive_kernel_witness'] = {'receive_interface': incoming, 'multicast_destination': destination_group, 'sender_ttl': sender.getsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL)}
                            else:
                                emit_beacon(ip, target_port)
                            listener.settimeout(9 if kind == 'valid_multicast' else 6)
                            connected = False
                            try:
                                connection, peer = listener.accept()
                            except socket.timeout:
                                pass
                            else:
                                with connection:
                                    connection.settimeout(3)
                                    hello = connection.recv(8192)
                                require(peer[0] == ip, 'unexpected TCP source')
                                require(len(hello) >= 6 and hello[0] == 22 and hello[1] == 3 and hello[5] == 1, 'not TLS ClientHello')
                                connected = True
                                case['automatic_connection'] = {'after_beacon_seconds': time.monotonic() - start, 'same_local_source': True, 'tls_client_hello': True, 'received_bytes': len(hello), 'authenticated': False}
                            case['connected'] = connected
                            case['passed'] = connected == (kind == 'valid_multicast')
                            after = rpc(path, 'getmodelnetworkinfo')
                            case['native_after'] = {k: after['native_participation'].get(k) for k in ['hint_count', 'authenticated_peers', 'acquired_models']}
                            require(case['native_after']['hint_count'] == int(connected), 'hint count differs from connection observation')
                            require(case['native_after']['authenticated_peers'] == 0 and case['native_after']['acquired_models'] == 0, 'dummy listener authenticated or acquired model')
                            require(proc.poll() is None, 'helper died after case')
                            case['unix_rpc_alive_after'] = True
                        finally:
                            start = time.monotonic()
                            if proc.poll() is None:
                                proc.terminate()
                                try:
                                    proc.wait(timeout=9)
                                except subprocess.TimeoutExpired:
                                    proc.kill(); proc.wait(timeout=3)
                                    case['forced_test_child_cleanup'] = True
                            case['helper_exit'] = proc.returncode
                            case['stop_seconds'] = time.monotonic() - start
                            log.flush()
                            cleanlog = redact(logpath.read_text(errors='replace')).replace(str(scratch), '<DISPOSABLE_SCRATCH>')
                            (HERE / ('helper-' + kind + '.log')).write_text(cleanlog)
                    cleanlog = redact(logpath.read_text(errors='replace')).replace(str(scratch), '<DISPOSABLE_SCRATCH>')
                    (HERE / ('helper-' + kind + '.log')).write_text(cleanlog)
                    require(case['helper_exit'] == 0, 'helper did not stop cleanly')
                print('CASE ' + kind + ': ' + ('PASS' if case['passed'] else 'FAIL_BOUNDARY'), flush=True)
            result['status'] = 'PASS_SAFE_DISCOVERY' if all(c['passed'] for c in result['cases']) else 'FAIL_OFF_SCOPE_AUTOMATIC_CONNECTION'
    except Exception as e:
        result['status'] = 'BLOCKED_OR_FAILED'
        result['error'] = redact(str(e))
    finally:
        result['finished_utc'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        result['harness_sha256'] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
        (HERE / 'helper-dial-result.json').write_text(json.dumps(result, indent=2) + '\n')
        print(json.dumps(result, indent=2), flush=True)
    return 0 if result['status'] == 'PASS_SAFE_DISCOVERY' else 1


if __name__ == '__main__':
    raise SystemExit(main())
