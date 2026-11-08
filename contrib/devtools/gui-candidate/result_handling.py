"""GUI evidence contract. Never reuse functional-test log markers for this workflow."""
import hashlib,os

ARCHIVE = os.environ.get('BTX_CANDIDATE_SHA256','offline-candidate-identity')

def verdict(s, evidence_root):
    def intact(name):
        row = s.get(name, {})
        try:
            path = (evidence_root / row['file']).resolve()
            return (path.is_relative_to(evidence_root.resolve()) and path.is_file()
                    and path.stat().st_size > 0
                    and hashlib.sha256(path.read_bytes()).hexdigest() == row['sha256'])
        except (KeyError, OSError, TypeError):
            return False
    launch = (s.get('app_alive') is True and intact('launch_image')
              and 'The node is the network.' in s.get('launch_text', '')
              and 'NOT CONNECTED' in s.get('launch_text', ''))
    observations = s.get('connected_observations', [])
    connected = (launch and s.get('native_confirmation_checked') is True
                 and s.get('rpc_control') == {'chain': 'regtest', 'blocks': 0, 'peers': 0}
                 and len(observations) == 2
                 and all('LIVE LOCAL' in o.get('text', '') and 'regtest' in o.get('text', '')
                         and '0 blocks' in o.get('text', '') for o in observations)
                 and observations[1].get('time', 0) - observations[0].get('time', 0) >= 5
                 and intact('connected_image'))
    integrity = (s.get('archive_sha256') == ARCHIVE and bool(s.get('package_before'))
                 and s.get('package_before') == s.get('package_after'))
    cleanup = (s.get('cleanup_remaining') == [] and s.get('cleanup_signals') == []
               and s.get('runtime_removed') is True)
    if s.get('failure') or s.get('app_crashed') is True:
        overall = 'FAIL'
    elif s.get('setup_blocker'):
        overall = 'BLOCKED'
    elif connected and integrity and cleanup and not s.get('error'):
        overall = 'PASS'
    else:
        overall = 'INCOMPLETE'
    return {'launch': 'PASS' if launch else 'INCOMPLETE',
            'connection': 'PASS' if connected else 'INCOMPLETE',
            'integrity_ok': integrity, 'cleanup_ok': cleanup, 'overall': overall}
