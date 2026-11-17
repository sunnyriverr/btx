"""Strict observation classifier. A setup failure or missing path is never a pass."""
def classify(case):
    if not case.get('finished') or not case.get('clean_shutdown'):
        raise ValueError('incomplete execution or shutdown')
    if not case.get('first_part_seen'):
        raise ValueError('multipart path not reached')
    if case['catalog_sha384'] != case['original_sha384']:
        raise ValueError('import did not establish original identity')
    if case.get('changed') and not case.get('mutation_before_first_part_reply'):
        raise ValueError('source-change path not established')
    if not case.get('changed') and case.get('mutation_before_first_part_reply'):
        raise ValueError('control unexpectedly changed')
    if not case['cloud_success']:
        if not case.get('changed'):
            raise ValueError('unchanged control failed')
        return 'SOURCE_CHANGE_REPORTED_FAILURE'
    if case['remote_sha384'] == case['original_sha384']:
        return 'VERIFIED_BYTES_PRESERVED' if case.get('changed') else 'CONTROL_PASS'
    if case.get('changed') and case['remote_sha384'] == case['changed_sha384']:
        return 'CLOUD_SUCCESS_WITH_DIFFERENT_BYTES'
    raise ValueError('unexpected remote bytes; investigate fixture before claiming result')
