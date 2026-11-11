import argparse
import hashlib
import json
import re
import signal
import socket
import struct
import tempfile
import time
import traceback
from pathlib import Path

from helpers import BINARY_SHA, PIECE, Helper, completion, digest, require
from relay import Relay, pacing

CAP = 256 << 20
SIZE = 68 << 20

def verdict(r):
    gates = ('binary_verified', 'pacing_verified', 'partial_verified', 'route_verified',
             'a_ready', 'b_stopped', 'clean_cleanup')
    if not all(r.get(g) is True for g in gates):
        return 'INCONCLUSIVE'
    if r.get('same_job') and r.get('a_attempt') and r.get('same_job_complete') and r.get('exact_completion'):
        return 'RECOVERED'
    if (r.get('same_job') and not r.get('a_attempt') and r.get('worker_b_retry')
            and r.get('observed_seconds', 0) >= 20 and r.get('still_pending')
            and r.get('control_complete') and r.get('exact_completion')):
        return 'STALLED'
    return 'INCONCLUSIVE'

def ports():
    with socket.socket() as a, socket.socket() as b:
        a.bind(('127.0.0.1', 0))
        b.bind(('127.0.0.1', 0))
        return a.getsockname()[1], b.getsockname()[1]

def trace_events(lines):
    connections = []
    children = []
    for line in lines:
        match = re.match(r'(\d+)\s+(\d+\.\d+) (.*)', line)
        if not match:
            continue
        tid, at, call = int(match[1]), float(match[2]), match[3]
        if call.startswith(('clone(', 'clone3(', '<... clone resumed>', '<... clone3 resumed>')):
            child = re.search(r' = (\d+)$', call)
            if child:
                children.append((tid, int(child[1])))
        if call.startswith('connect(') and 'sa_family=AF_INET' in call:
            port = re.search(r'sin_port=htons\((\d+)\).*?inet_addr\("127\.0\.0\.1"\)', call)
            connections.append((at, tid, int(port[1]) if port else None))
    return connections, children


def descendants(root, links):
    found = {root}
    while True:
        expanded = found | {child for parent, child in links if parent in found}
        if expanded == found:
            return found
        found = expanded


def trace(path):
    return trace_events(path.read_text().splitlines() if path.exists() else [])


def make_model(path):
    header = json.dumps({'t': {'dtype':'U8','shape':[SIZE],'data_offsets':[0,SIZE]}},
                        separators=(',',':')).encode()
    with path.open('wb') as f:
        f.write(struct.pack('<Q', len(header)) + header)
        for i in range(68):
            f.write(hashlib.shake_256(f'failover:{i}'.encode()).digest(1 << 20))

def verify_pieces(path, pieces):
    require(pieces, 'no retained pieces')
    with path.open('rb') as f:
        for name, meta in pieces.items():
            f.seek(int(name.removesuffix('.piece')) * PIECE)
            data = f.read(PIECE)
            require(len(data)==meta['bytes'] and hashlib.sha256(data).hexdigest()==meta['sha256'],
                    'piece differs from source')

def run(binary, out, root):
    r = {}
    helpers = []
    relay = None
    def save():
        (out/'observations.json').write_text(json.dumps(r, indent=2)+'\n')
    def phase(name):
        r['phase'] = name
        print(name, flush=True)
        save()
    def timeout(*_):
        raise TimeoutError('300 second fixture bound')
    signal.signal(signal.SIGALRM, timeout)
    signal.alarm(300)
    try:
        r['binary_sha256'] = digest(binary)
        r['binary_verified'] = r['binary_sha256'] == BINARY_SHA
        require(r['binary_verified'], 'helper digest')
        ap, bp = ports()
        model = root/'model.safetensors'
        make_model(model)
        expected = digest(model, 'sha384')
        total = model.stat().st_size
        a = Helper(binary, root/'a', out, 'a', CAP, hostport=ap)
        b = Helper(binary, root/'b', out, 'b', CAP, hostport=bp)
        helpers.extend([a,b])
        phase('source setup')
        a.start()
        b.start()
        ia = a.ok('importmodel',[str(model),{'pin':True}])
        ib = b.ok('importmodel',[str(model),{'pin':True}])
        uri, artifact = ia['uri'], ia['artifact_id']
        require(ia['seeded'] and ib['seeded'] and ib['artifact_id']==artifact and ib['uri']==uri,'source identity')
        original_manifest = a.ok('getmodelmanifest',[uri])
        require(original_manifest['complete'] and original_manifest['files'][0]['sha384']==expected,'A manifest')
        a.stop()
        relay = Relay(bp)
        rp = relay.port
        receiver = Helper(binary, root/'receiver', out, 'receiver', CAP,
                          peer=[f'127.0.0.1:{ap}',f'127.0.0.1:{rp}'])
        helpers.append(receiver)
        receiver.trace = out/'receiver-connect.log'
        receiver.start()
        phase('A offline, wait for B prefix')
        began = time.time()
        jid, initial = receiver.request(uri)
        require(jid, 'manual job missing')
        r.update(initial_job=initial, original_job_id=jid, model_uri=uri,
                 artifact_id=artifact, source_sha384=expected, source_bytes=total,
                 ports={'a': ap, 'b': bp, 'relay': rp}, request_at=began)
        end = time.monotonic()+48
        while True:
            job = receiver.job(jid)
            pieces = receiver.pieces(artifact)
            if pieces and job.get('last_peer') == f'127.0.0.1:{rp}':
                break
            require(job.get('status') in ('queued','running') and time.monotonic()<end, f'no B prefix {job}')
            time.sleep(.15)
        connections, links = trace(receiver.trace)
        before = [(at, tid, port) for at, tid, port in connections if at >= began]
        starters = {tid for at, tid, port in before if port == ap
                    and any(t > at and p == rp and t_id == tid for t, t_id, p in before)}
        require(len(starters) == 1, f'could not identify retrieval worker {starters}')
        worker = starters.pop()
        require(any(child == worker for _, child in links), 'worker creation missing from trace')
        worker_before = [port for _, tid, port in before if tid == worker]
        require(worker_before[0] == ap and rp in worker_before, 'missing A-first/B-second evidence')
        r['worker_tid'] = worker
        r['initial_connections'] = before
        phase('restart A, then stop B')
        a.start()
        resumed_manifest = a.ok('getmodelmanifest',[uri])
        require(resumed_manifest['complete'] and resumed_manifest['artifact_id']==artifact
                and resumed_manifest['files'][0]['sha384']==expected,'recovered A manifest')
        with socket.create_connection(('127.0.0.1',ap),timeout=3):
            pass
        r['a_ready'] = True
        pieces = receiver.pieces(artifact)
        verify_pieces(model,pieces)
        used = sum(v['bytes'] for v in pieces.values())
        require(0 < used < total and receiver.job(jid).get('status')=='running','not incomplete at switch')
        r['partial_verified'] = True
        r['retained_pieces'] = pieces
        r['bytes_at_switch'] = used
        pre = receiver.job(jid).get('peer_retries',0)
        switched = time.time()
        r['switched_at'] = switched
        relay.close()
        b.stop()
        r['b_stopped'] = True
        samples = relay.samples
        r['pacing_verified'] = pacing(samples,relay.rate) and sum(n for _,n in samples)>=used
        r['pacing'] = {'bytes':sum(n for _,n in samples),'seconds':samples[-1][0]-samples[0][0],'rate_limit':relay.rate,'chunks':len(samples)}
        (out/'pacing-samples.json').write_text(json.dumps(samples)+'\n')
        require(r['pacing_verified'],'relay pace or byte count')
        phase('observe original job')
        first_retry = None
        absolute_end = time.monotonic()+65
        r['samples'] = []
        while time.monotonic()<absolute_end:
            job = receiver.job(jid)
            r['samples'].append(job)
            attempts, links = trace(receiver.trace)
            workers = descendants(worker, links)
            r['a_attempt'] = any(p == ap and t >= switched and tid in workers for t, tid, p in attempts)
            if job.get('peer_retries',0)>pre and job.get('last_peer')==f'127.0.0.1:{rp}':
                first_retry = first_retry or time.monotonic()
                r['worker_b_retry'] = True
            if job.get('status') in ('done','failed','cancelled'):
                break
            if first_retry and not r['a_attempt'] and time.monotonic()-first_retry>=20:
                r['observed_seconds'] = time.monotonic()-first_retry
                break
            time.sleep(.25)
        r['connections'], links = trace(receiver.trace)
        workers = descendants(worker, links)
        r['worker_descendants'] = sorted(workers - {worker})
        r['route_verified'] = all(p in (ap, rp) for t, _, p in r['connections'] if t >= began)
        r['a_attempt'] = any(p == ap and t >= switched and tid in workers
                             for t, tid, p in r['connections'])
        r['ambient_a_attempts'] = sum(p == ap and t >= switched and tid not in workers
                                      for t, tid, p in r['connections'])
        r['worker_b_connections'] = sum(p == rp and t >= switched and tid == worker
                                         for t, tid, p in r['connections'])
        r['worker_b_retry'] = bool(r.get('worker_b_retry') and r['worker_b_connections'])
        require(r['route_verified'],'extra route observed')
        r['original_job_final'] = job
        if job.get('status')=='done':
            r['same_job'] = job.get('job_id')==jid
            r['same_job_complete'] = True
            r['completion'] = completion(receiver,uri,expected)
        else:
            require(job.get('status')=='running' and r.get('observed_seconds',0)>=20
                    and not r['a_attempt'] and r.get('worker_b_retry'),'original outcome inconclusive')
            retry, reply = receiver.request(uri)
            r['repeat_request'] = reply
            r['same_job'] = retry==jid
            r['still_pending'] = receiver.job(jid).get('status')=='running'
            require(r['same_job'] and r['still_pending'],'retry identity')
            phase('recovery control after receiver restart')
            receiver.stop()
            receiver.trace = out/'control-connect.log'
            receiver.start()
            after_restart = receiver.pieces(artifact)
            require(all(after_restart.get(k)==v for k,v in pieces.items()),
                    'saved pieces did not survive restart')
            retry, control_reply = receiver.request(uri)
            r['control_request'] = control_reply
            r['control_job'] = receiver.settled(retry or jid, 60)
            require(r['control_job']['status'] == 'done', 'recovery control failed')
            r['completion'] = completion(receiver,uri,expected)
            r['control_connections'], _ = trace(receiver.trace)
            require(any(p == ap for _, _, p in r['control_connections']), 'control did not connect to A')
            require(r['control_job'].get('last_peer') == f'127.0.0.1:{ap}', 'control did not finish from A')
            r['control_complete'] = True
        kept = receiver.pieces(artifact)
        r['exact_completion'] = (r['completion']['sha384']==expected and r['completion']['bytes']==total
                                 and all(kept.get(k)==v for k,v in pieces.items()))
    except Exception as e:
        r['error'] = str(e)
        r['traceback'] = traceback.format_exc()
    finally:
        signal.alarm(0)
        if relay:
            try:
                relay.close()
            except Exception as error:
                r['error'] = r.get('error') or f'relay cleanup: {error}'
        for h in reversed(helpers):
            h.cleanup()
        r['clean_cleanup'] = all(not h.forced and not h.cleanup_error for h in helpers)
        r['result'] = verdict(r) if not r.get('error') else 'INCONCLUSIVE'
        save()
    return int(r['result']=='INCONCLUSIVE')

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--binary',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    args.output.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='btx-fo-') as tmp:
        raise SystemExit(run(args.binary.resolve(),args.output.resolve(),Path(tmp)))
