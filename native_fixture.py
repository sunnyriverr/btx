"""Real disposable helper RPC controls for #504 and #494."""
from concurrent.futures import ThreadPoolExecutor, TimeoutError
import json
from pathlib import Path
import resource
import signal
import struct
import tempfile
import time

from helpers import Helper, require, sha


def identities(helper, root, candidate):
    listing = helper.store / 'identities.json'
    keys = helper.store / 'tls'
    default, = helper.ok('listmodelidentities', [])['identities']
    existing_key = keys / ('identity-' + default['id'][:16] + '.sk')
    original_key = sha(existing_key)
    # Force default re-creation in this disposable store while preserving its
    # existing research key. The gate pauses after the second list read.
    listing.write_text('{}\n')
    (root / 'arm').touch()
    with ThreadPoolExecutor(max_workers=2) as pool:
        automatic = pool.submit(helper.ok, 'checkmodelsetup', [])
        try:
            until = time.monotonic() + 4
            while not (root / 'arrived').exists():
                require(not automatic.done() and time.monotonic() < until, 'second list read did not reach gate')
                time.sleep(.02)
            explicit = pool.submit(helper.ok, 'createmodelidentity', ['parallel identity'])
            try:
                explicit.result(timeout=1)
                finished_before_release = True
            except TimeoutError:
                finished_before_release = False
        finally:
            (root / 'release').touch()
        automatic.result(timeout=5)
        new = explicit.result(timeout=5)
    (root / 'arm').unlink()
    rows = helper.ok('listmodelidentities', [])['identities']
    found = {row['id'] for row in rows}
    require(finished_before_release == (not candidate), 'identity writer did not follow the expected gate schedule')
    require(found == ({default['id'], new['id']} if candidate else {default['id']}),
            'unexpected identity list under forced overlap')
    new_key = keys / ('identity-' + new['id'][:16] + '.sk')
    require(new_key.stat().st_size == existing_key.stat().st_size == 2560, 'incomplete key')
    require(sha(existing_key) == original_key, 'existing key changed')
    disk = listing.read_bytes()
    key_hashes = {f.name: sha(f) for f in (existing_key, new_key)}
    helper.stop()
    helper.start()
    require(helper.ok('listmodelidentities', [])['identities'] == rows and listing.read_bytes() == disk,
            'restart changed identities')
    require({f.name: sha(f) for f in (existing_key, new_key)} == key_hashes, 'restart changed keys')
    serial = helper.ok('createmodelidentity', ['serial control'])
    require({x['id'] for x in helper.ok('listmodelidentities', [])['identities']} == found | {serial['id']},
            'serial creation failed')
    return {'gate_reached': True, 'explicit_finished_before_release': finished_before_release,
            'list_after_overlap': len(found), 'full_key_files_after_overlap': 2,
            'existing_key_unchanged': True, 'restart_preserved_observed_state': True,
            'serial_creation_passed': True}


def exports(helper, root, candidate):
    model_ids = []
    for tag in ('old', 'new'):
        source = root / tag
        source.mkdir()
        header = json.dumps({'__metadata__': {'t': tag}}).encode()
        (source / 'model.safetensors').write_bytes(struct.pack('<Q', len(header)) + header)
        result = helper.ok('importmodel', [str(source), {'pin': True, 'publish': False}])
        model_ids.append(result['model_id'])
    def link(path, revision):
        return 'exportmodellink', [model_ids[revision], str(path)]
    def package(path, revision):
        return 'exportbtxbundle', [{'payload': {'kind': 'btxbundle', 'schema_version': 1,
                                               'title': ('old bundle', 'new bundle')[revision]}, 'path': str(path)}]
    observed = {}
    pid = helper.proc.pid
    ignored = next(row.split()[1] for row in Path(f'/proc/{pid}/status').read_text().splitlines()
                   if row.startswith('SigIgn:'))
    require(int(ignored, 16) & (1 << (signal.SIGXFSZ - 1)), 'size-limit signal would kill helper')
    for name, request, code, refused in (('link', link, 'IO', 'INVALID_PARAMETER'),
                                         ('bundle', package, 'IO_ERROR', 'SYMLINK_REFUSED')):
        target = root / name
        helper.ok(*request(target, 0))
        previous = target.read_bytes()
        target.chmod(0o640)
        expected_path = root / (name + '-expected')
        helper.ok(*request(expected_path, 1))
        expected = expected_path.read_bytes()
        # Require distinct bytes where the format includes the changed input.
        require(previous != expected, f'{name} fixtures must export distinct bytes')
        for dest in (target, root / (name + '-fresh')):
            saved = resource.prlimit(pid, resource.RLIMIT_FSIZE)
            try:
                resource.prlimit(pid, resource.RLIMIT_FSIZE, (8, saved[1]))
                error = helper.rpc(*request(dest, 1))['error']
            finally:
                resource.prlimit(pid, resource.RLIMIT_FSIZE, saved)
            require(error and error['code'] == code, f'{name} did not reach short write: {error}')
            if dest == target and candidate:
                require(dest.read_bytes() == previous and dest.stat().st_mode & 0o777 == 0o640,
                        f'{name} old bytes or permissions changed')
            else:
                require(not dest.exists(), f'{name} unexpected file after failed save')
            require(not list(root.glob('.btx-export-*.tmp')), 'temporary export leaked')
            helper.ok(*request(dest, 1))
            require(dest.read_bytes() == expected, f'{name} retry exported different bytes')
        symlink = root / (name + '-symlink')
        symlink.symlink_to(target)
        error = helper.rpc(*request(symlink, 0))['error']
        require(error and error['code'] == refused and symlink.is_symlink()
                and target.read_bytes() == expected, f'{name} symlink refusal failed')
        observed[name] = {'short_write_error': code, 'old_destination_preserved': candidate,
                          'fresh_failure_clean': True, 'byte_exact_retry': True, 'symlink_refused': True}
    return observed


def exercise(number, binary, output, candidate, gate):
    root = Path(tempfile.mkdtemp(prefix='bt-review-'))
    output.mkdir()
    helper = Helper(binary, root, output, number)
    if number == '504':
        helper.extra_env = {'LD_PRELOAD': str(gate), 'BTX_TEST_IDENTITY_LIST': str(helper.store/'identities.json'),
                            'BTX_TEST_ARM': str(root/'arm'), 'BTX_TEST_ARRIVED': str(root/'arrived'),
                            'BTX_TEST_RELEASE': str(root/'release')}
    previous = signal.signal(signal.SIGXFSZ, signal.SIG_IGN)
    try:
        helper.start()
        result = identities(helper, root, candidate) if number == '504' else exports(helper, root, candidate)
        helper.stop()
    finally:
        signal.signal(signal.SIGXFSZ, previous)
        helper.cleanup()
    require(not root.exists() and not helper.cleanup_signals, 'fixture cleanup incomplete')
    return dict(result, clean_shutdown=True)
