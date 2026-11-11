"""Exercise the real Linux helper's list-save failure and retry over Unix RPC."""
import json
from pathlib import Path
import resource
import signal
import tempfile

from helpers import Helper, require, sha, sha_bytes


def exercise(binary, output, candidate):
    root = Path(tempfile.mkdtemp(prefix='id505-'))
    output.mkdir()
    helper = Helper(binary, root, output, 'identity')
    listing = helper.store / 'identities.json'

    def keys():
        return {p.name: (p.stat().st_size, sha(p))
                for p in (helper.store / 'tls').glob('identity-*.sk')}

    def read_identities():
        return helper.ok('listmodelidentities', [])['identities']

    previous_signal = signal.signal(signal.SIGXFSZ, signal.SIG_IGN)
    try:
        helper.start()
        old = helper.ok('createmodelidentity', ['existing identity'])
        prior = read_identities()
        require(any(row['id'] == old['id'] for row in prior), 'healthy identity missing')
        raw = listing.read_bytes()
        old_keys = keys()
        require(old_keys and all(size == 2560 for size, _ in old_keys.values()),
                'expected complete ML-DSA-44 key files')
        cap = max(len(raw) + 128, 2561)
        label = 'retry-' + 'x' * (cap + 512)
        status = Path(f'/proc/{helper.proc.pid}/status').read_text().splitlines()
        ignored = next(row.split()[1] for row in status if row.startswith('SigIgn:'))
        require(int(ignored, 16) & (1 << (signal.SIGXFSZ - 1)),
                'helper must receive a write error instead of a termination signal')
        original = resource.prlimit(helper.proc.pid, resource.RLIMIT_FSIZE)
        try:
            resource.prlimit(helper.proc.pid, resource.RLIMIT_FSIZE, (cap, original[1]))
            answer = helper.rpc('createmodelidentity', [label])
        finally:
            resource.prlimit(helper.proc.pid, resource.RLIMIT_FSIZE, original)
        after = listing.read_bytes()
        new_keys = keys()
        error = answer.get('error')
        result = {
            'limit': cap, 'old_identity_count': len(prior),
            'old_list_sha256': sha_bytes(raw), 'after_fault_sha256': sha_bytes(after),
            'size_after_fault': len(after), 'rpc_error': error,
            'old_list_unchanged': after == raw, 'old_keys_unchanged': new_keys == old_keys,
            'no_temp_files': not (helper.store / 'identities.json.tmp').exists()
            and not list((helper.store / 'tls').glob('identity-*.sk.tmp')),
        }
        (output / 'fault.json').write_text(json.dumps(result, indent=2)+'\n')
        require(result['no_temp_files'], 'temporary file leaked')
        if candidate:
            require(error and error['code'] == 'IO' and error['message'].endswith('identities.json'),
                    'expected identity-list write error')
            require(result['old_list_unchanged'] and result['old_keys_unchanged'],
                    'failed save changed the prior list or keys')
            require(read_identities() == prior, 'prior entries no longer readable')
            created = helper.ok('createmodelidentity', [label])
            expected = read_identities()
            require(len(expected) == len(prior) + 1 and expected[:-1] == prior
                    and expected[-1]['id'] == created['id'] and expected[-1]['label'] == label,
                    'retry did not preserve the prior list and add exactly one identity')
            expected_keys = keys()
            require(len(expected_keys) == len(old_keys) + 1
                    and all(expected_keys.get(name) == info for name, info in old_keys.items())
                    and all(size == 2560 for size, _ in expected_keys.values()),
                    'retry did not preserve old keys and add one full key')
            saved = listing.read_bytes()
            helper.stop()
            helper.start()
            require(read_identities() == expected and listing.read_bytes() == saved
                    and keys() == expected_keys, 'retry or old identity changed after restart')
            result.update(retry_survived_restart=True, final_identity_count=len(expected),
                          final_list_sha256=sha_bytes(saved))
        else:
            require(error is None and answer['result'].get('id'), 'baseline did not acknowledge')
            require(len(after) == cap and not result['old_list_unchanged'],
                    'baseline did not truncate at the injected limit')
            try:
                json.loads(after)
            except json.JSONDecodeError:
                result['baseline_list_invalid_json'] = True
            else:
                raise RuntimeError('baseline did not lose readable list')
            require(read_identities() == [], 'baseline still lists prior identities')
            require(len(new_keys) == len(old_keys) + 1
                    and all(new_keys.get(name) == info for name, info in old_keys.items())
                    and all(size == 2560 for size, _ in new_keys.values()),
                    'fault affected the key write rather than only the list')
        helper.stop()
    finally:
        signal.signal(signal.SIGXFSZ, previous_signal)
        helper.cleanup()
    require(not root.exists() and not helper.cleanup_signals, 'fixture cleanup incomplete')
    result.update(clean_shutdown=True, removed_disposable_store=True)
    return result
