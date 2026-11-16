import json
import sys


def validate(r, code):
    assert code == 0 and r['status'] == 'PASS' and not r.get('failure')
    assert r['cloud_endpoint_unavailable'] is True
    assert r['cloud_recovery']['cloud_hydrated'] is True
    assert r['provider'] == 'MINIO' and r['fake'] is False and r['originals_preserved'] is True
    assert set(r['cases']) == {'cloud', 'independent_export'}
    assert len(r['files']) >= 4 and 'model.safetensors' in r['files'] and 'config.json' in r['files']
    c = r['control']
    assert c['text'].strip() and c['backend'] == 'transformers' and c['device'] == 'cpu'
    assert c['model_id'] == r['model_id'] and c['artifact_id'] == r['artifact_id']
    for name, case in r['cases'].items():
        assert case['status'] == 'PASS' and case['restart_offline'] is True and case['generation'] == c
        if name == 'cloud':
            assert case['origin_used'] is True and case['original_absent'] is True
        else:
            assert case['fresh_catalog'] is True and case['source_absent'] is True


if __name__ == '__main__':
    validate(json.load(open(sys.argv[1])), int(sys.argv[2]))
    print('RECOVERY_TO_USE_SCOPED_PASS')
