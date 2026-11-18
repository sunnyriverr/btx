"""Strict native result admission; an expected product failure is not a setup pass."""
import hashlib
from regression import payload

def validate(r, phase):
    assert phase in ('baseline', 'candidate')
    assert r['complete'] is True and 'error' not in r
    assert r['exits'] == [0, 0] and r['origin_handlers_alive'] == 0
    assert r['same_key_retry'] and r['duplicate_replay'] and r['upload_retry']
    assert r['restart_preserves_configuration_and_budget']
    assert r['upload_bytes'] == len(payload())
    assert r['upload_sha256'] == hashlib.sha256(payload()).hexdigest()
    assert r['before_budget']['budget_used_gets'] == 1 and r['final_budget']['budget_used_gets'] == 2
    assert r['before_budget']['origin_bytes'] == 15 and r['final_budget']['origin_bytes'] == 30
    assert r['gate']['entered'] < r['gate']['released'] <= r['gate']['resumed']
    assert not any('error' in q for q in r['origin_requests'])
    c = r['paused_hello']
    if phase == 'baseline':
        assert r['verdict'] == 'REPRODUCED'
        assert set(r['violations']) == {'hello waited for upload release', 'busy controls not reached before release'}
        assert c['sent'] < r['gate']['released'] <= c['finished']
    else:
        assert r['verdict'] == 'PASS' and r['violations'] == [] and r['busy_controls']
        assert c['sent'] <= c['finished'] < r['gate']['released']
        assert r['paused_info']['helper_ready'] and r['paused_info']['cloud_storage_busy']
    return True
