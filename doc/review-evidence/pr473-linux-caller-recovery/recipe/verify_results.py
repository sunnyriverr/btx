"""Reject incomplete setup, shallow IO checks and retries with changed accounting."""
from copy import deepcopy
from result_contract import GATES

def qualified(record):
    if not all(record.get(gate) is True for gate in GATES):
        return False
    if record.get('error') or record.get('cleanup_signals') != [] or record.get('leftovers') != []:
        return False
    if any(record.get(key) is not False for key in ('rpc_acknowledged', 'memory_changed', 'disk_changed', 'restart_retained_change')):
        return False
    reply = record.get('fault_reply', {})
    if reply.get('result') is not None or reply.get('error', {}).get('code') != 'INTERNAL':
        return False
    if 'pledge not recorded' not in reply.get('error', {}).get('message', ''):
        return False
    return (record.get('restart_amount') == 1 and record.get('recovery_amount') == 10000001
            and record.get('same_request_retry_once') is True
            and record.get('rejected_increment_not_resurrected') is True)

def offline_checks():
    good = {gate: True for gate in GATES}
    good.update(cleanup_signals=[], leftovers=[], rpc_acknowledged=False,
                memory_changed=False, disk_changed=False, restart_retained_change=False,
                fault_reply={'result': None, 'error': {'code': 'INTERNAL', 'message': 'cannot save campaigns.json; pledge not recorded'}},
                restart_amount=1, recovery_amount=10000001,
                same_request_retry_once=True, rejected_increment_not_resurrected=True)
    assert qualified(good)
    count = 0
    for key in (*GATES, 'same_request_retry_once', 'rejected_increment_not_resurrected'):
        bad = deepcopy(good)
        bad[key] = False
        assert not qualified(bad), key
        count += 1
    for key in ('rpc_acknowledged', 'memory_changed', 'disk_changed', 'restart_retained_change'):
        bad = deepcopy(good)
        bad[key] = True
        assert not qualified(bad), key
        count += 1
    for key in ('restart_amount', 'recovery_amount'):
        bad = deepcopy(good)
        bad[key] += 1
        assert not qualified(bad)
        count += 1
    bad = deepcopy(good)
    bad['fault_reply']['error']['code'] = 'NOT_FOUND'
    assert not qualified(bad)
    count += 1
    return {'offline_only': True, 'negative_controls': count, 'pass': True}

if __name__ == '__main__':
    import json
    print(json.dumps(offline_checks()))
