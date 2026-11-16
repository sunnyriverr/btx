"""Bounded live-client response probe; observes product behavior, never edits it."""
import argparse
import hashlib
import json
from pathlib import Path
import resource
import subprocess
import time
from origin import Origin
from validator import validate_scenario


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--client', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True)
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    result = {'complete': False, 'cases': {}, 'scope': 'unmodified real S3 client and loopback HTTP transport; controlled origin, not AWS/MinIO/FakeS3; no signature-validation claim'}
    started = time.monotonic()
    cases = [('known_error200_retry','known','error200',2),
             ('unknown_error200_retry','unknown','error200',2),
             ('known_error500_retry','known','error500',2),
             ('clean_known','known','success',1),
             ('clean_unknown','unknown','success',1),
             ('small_put','known','success',1)]
    try:
        for name, length_mode, first_mode, attempts in cases:
            assert time.monotonic() - started < 110, 'total probe runtime exceeded'
            size = 4096 if name == 'small_put' else (8 << 20) + 4096
            pattern = bytes((i * 17 + 3) % 251 for i in range(251))
            expected = (pattern * (size // 251 + 1))[:size]
            digest = hashlib.sha256(expected).hexdigest()
            with Origin(mode=first_mode) as origin:
                if attempts == 2:
                    origin.completion_modes = [first_mode, 'success']
                command = [str(args.client), origin.endpoint, name, str(size), length_mode, str(attempts)]
                proc = subprocess.run(command, capture_output=True, text=True, timeout=20)
                (args.out / (name + '-stderr.log')).write_text(proc.stderr)
                (args.out / (name + '-stdout.json')).write_text(proc.stdout)
                assert proc.returncode == 0, (name, proc.returncode, proc.stderr)
                native = json.loads(proc.stdout)
                assert native['payload_sha256'] == digest and native['length'] == size
                assert native['fake'] is False
                state = origin.snapshot()
                (args.out / (name + '-native.json')).write_text(json.dumps(native, indent=2) + '\n')
                (args.out / (name + '-origin.json')).write_text(json.dumps(state, indent=2) + '\n')
                observed = validate_scenario(native, state, digest, size, expected_first=first_mode)
                assert origin.object_bytes('/completion-probe/' + name) == expected, 'healthy final copy differs'
                (args.out / (name + '-native.json')).write_text(json.dumps(native, indent=2) + '\n')
                (args.out / (name + '-origin.json')).write_text(json.dumps(state, indent=2) + '\n')
                result['cases'][name] = {'observation': observed, 'same_client_retry': attempts == 2,
                                         'length_mode': length_mode, 'bytes': size, 'payload_sha256': digest}
            result['cases'][name]['origin_closed'] = True
        result['seconds'] = time.monotonic() - started
        result['peak_parent_rss_kib'] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        result['peak_client_rss_kib'] = resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss
        assert result['peak_parent_rss_kib'] + result['peak_client_rss_kib'] < 256 * 1024, 'probe memory bound exceeded'
        result['complete'] = True
    except Exception as exc:
        result['error'] = repr(exc)
        raise
    finally:
        (args.out / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
