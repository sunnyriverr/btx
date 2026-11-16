"""Strict observation validator; a reproduced defect is classified, not hidden.

No native product is executed here. Origin's metadata establishes the response
path while the native driver establishes upload return and object readback.
"""
import copy


MAX_DATA = 64 * 1024 * 1024


def validate_scenario(native, origin, payload_sha256, payload_bytes, expected_first='success'):
    assert expected_first in ('success', 'error200', 'error500'), 'unknown scenario'
    assert native.get('fake') is False, 'FakeS3 or absent backend identity'
    assert native.get('length') == payload_bytes, 'native payload length mismatch'
    assert native.get('payload_sha256') == payload_sha256, 'native payload digest mismatch'
    assert isinstance(origin.get('requests'), list) and origin['requests'], 'no real HTTP observation'
    requests = origin['requests']
    assert len(requests) <= 64 and origin.get('retained_bytes', MAX_DATA + 1) <= MAX_DATA, 'fixture bounds exceeded'
    assert all(not row.get('fixture_error') for row in requests), 'fixture failed'
    assert all(row.get('authorization_present') and row.get('sigv4_scheme') and
               row.get('credential_scope') and row.get('amz_date_present')
               for row in requests), 'real signed request path missing'
    attempts = native.get('attempts')
    assert isinstance(attempts, list) and len(attempts) == (1 if expected_first == 'success' else 2), 'wrong attempt count'
    assert all(0 <= attempt.get('max_buffer', MAX_DATA + 1) <= min(MAX_DATA, payload_bytes)
               for attempt in attempts), 'upload buffer observation missing or out of range'
    completions = [row for row in requests if row.get('response_kind') in ('multipart-error', 'multipart-success')]
    assert sum(row.get('response_kind') == 'multipart-begin' for row in requests) == len(completions), 'multipart sequence incomplete'
    final = attempts[-1]
    assert final.get('upload_ok') is True, 'healthy upload/retry failed'
    assert final.get('head_ok') is True and final.get('head_size') == payload_bytes, 'healthy HEAD failed'
    assert final.get('get_ok') is True and final.get('bytes_match') is True, 'healthy GET bytes differ'
    objects = origin.get('objects')
    assert isinstance(objects, dict) and len(objects) == 1, 'unexpected finalized object count'
    final_path, final_object = next(iter(objects.items()))
    assert final_object.get('bytes') == payload_bytes and final_object.get('sha256') == payload_sha256, 'origin object differs'
    assert any(row['path'] == final_path and row.get('response_kind') == 'object-read' for row in requests), 'no actual object read'
    if expected_first == 'success':
        if payload_bytes > 8 * 1024 * 1024:
            assert len(completions) == 1 and completions[0]['response_kind'] == 'multipart-success', 'multipart success control absent'
            assert completions[0]['response_status'] == 200 and completions[0]['object_exists_after'], 'invalid completion control'
        else:
            assert not completions and any(row.get('response_kind') == 'ordinary-put' for row in requests), 'small PUT control took wrong path'
        return {'classification': 'valid_upload_pass', 'byte_exact': True,
                'signed_requests_observed': len(requests), 'multipart_completions': len(completions)}
    assert len(completions) == 2, 'error/retry did not reach two real completions'
    first, last = completions
    assert first['completion_mode'] == expected_first and first['response_kind'] == 'multipart-error', 'first completion path wrong'
    assert first['response_status'] == (200 if expected_first == 'error200' else 500), 'wrong HTTP status control'
    assert first['object_exists_after'] is False, 'fault unexpectedly finalized an object'
    assert last['response_kind'] == 'multipart-success' and last['response_status'] == 200, 'retry completion missing'
    assert last['path'] == first['path'] == final_path and last['object_exists_after'], 'retry changed target or did not finalize'
    assert last['object_sha256_after'] == payload_sha256, 'retry completed wrong bytes'
    failed = attempts[0]
    assert failed.get('head_ok') is False and failed.get('get_ok') is False and failed.get('bytes_match') is False, 'first object absence not proved natively'
    assert failed.get('head_error') and failed.get('get_error'), 'missing native object-absence error'
    uid = first['query']['uploadId'][0]
    aborts = [row for row in requests if row.get('response_kind') == 'multipart-abort' and row['query'].get('uploadId') == [uid]]
    if failed.get('upload_ok') is True:
        assert expected_first == 'error200', 'HTTP500 incorrectly reported success'
        assert not aborts, 'success-return path unexpectedly aborted upload'
        classification = 'false_success_reproduced'
    else:
        assert failed.get('upload_ok') is False and failed.get('upload_error'), 'failure lacks native error'
        assert len(aborts) == 1 and uid in origin.get('aborted_uploads', []), 'rejected completion cleanup missing'
        assert requests.index(first) < requests.index(aborts[0]) < requests.index(last), 'abort order invalid'
        classification = 'documented_error_correctly_rejected'
    return {'classification': classification, 'byte_exact_retry': True,
            'same_object_path': True, 'first_upload_ok': failed['upload_ok'],
            'first_http_status': first['response_status'], 'abort_observed': bool(aborts),
            'signed_requests_observed': len(requests), 'multipart_completions': 2}


def offline_controls():
    """Synthetic validator vectors only, never a native result."""
    sha = 'a' * 64
    length = 8 * 1024 * 1024 + 4096
    path = '/completion-probe/same-key'
    common = {'authorization_present': True, 'sigv4_scheme': True,
              'credential_scope': '20261116/us-east-1/s3/aws4_request', 'amz_date_present': True,
              'path': path, 'query': {}, 'response_status': 200}
    def row(kind, **extras):
        return {**common, 'response_kind': kind, **extras}
    native = {'fake': False, 'length': length, 'payload_sha256': sha,
              'attempts': [{'upload_ok': True, 'upload_error': '', 'head_ok': False, 'head_size': 0,
                            'get_ok': False, 'bytes_match': False, 'head_error': 'missing',
                            'get_error': 'missing', 'max_buffer': 8 * 1024 * 1024},
                           {'upload_ok': True, 'head_ok': True, 'head_size': length,
                            'get_ok': True, 'bytes_match': True, 'max_buffer': 8 * 1024 * 1024}]}
    origin = {'retained_bytes': length * 2, 'objects': {path: {'bytes': length, 'sha256': sha}},
              'aborted_uploads': [], 'requests': [row('multipart-begin'),
                  row('multipart-error', completion_mode='error200', object_exists_after=False,
                      query={'uploadId': ['one']}), row('missing-object'),
                  row('multipart-begin'), row('multipart-success', object_exists_after=True,
                      object_sha256_after=sha), row('object-read')]}
    good = validate_scenario(native, origin, sha, length, 'error200')
    assert good['classification'] == 'false_success_reproduced'
    # A native rejection must have the real cleanup path, rather than an earlier fixture failure.
    rejected = copy.deepcopy(native)
    rejected['attempts'][0].update(upload_ok=False, upload_error='s3 status500')
    o500 = copy.deepcopy(origin)
    o500['requests'][1].update(completion_mode='error500', response_status=500)
    o500['requests'].insert(3, row('multipart-abort', query={'uploadId': ['one']}))
    o500['aborted_uploads'] = ['one']
    assert validate_scenario(rejected, o500, sha, length, 'error500')['classification'] == 'documented_error_correctly_rejected'
    controls = {}
    for name in ('fake', 'missing_completion', 'retry_not_exact', 'fault_has_object', 'missing_signature'):
        n, o = copy.deepcopy(native), copy.deepcopy(origin)
        if name == 'fake': n['fake'] = True
        if name == 'missing_completion': o['requests'].pop(1)
        if name == 'retry_not_exact': n['attempts'][1]['bytes_match'] = False
        if name == 'fault_has_object': o['requests'][1]['object_exists_after'] = True
        if name == 'missing_signature': o['requests'][0]['sigv4_scheme'] = False
        try:
            validate_scenario(n, o, sha, length, 'error200')
        except AssertionError:
            controls[name] = 'rejected'
        else:
            raise AssertionError('negative vector accepted: ' + name)
    return {'synthetic_false_success': 'classified', 'synthetic_rejection_and_cleanup': 'accepted',
            'negative_vectors': controls, 'native_execution': False}


if __name__ == '__main__':
    import json
    print(json.dumps(offline_controls(), indent=2))
