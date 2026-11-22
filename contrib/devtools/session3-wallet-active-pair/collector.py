"""Validate public stage evidence; incomplete native execution never passes."""
import json,re
TXID=re.compile(r'^[0-9a-f]{64}$')
STAGES=['control','replacement','mixed_refusal']


def validate_record(record):
    assert isinstance(record,dict) and record.get('stage')in STAGES and record['status']=='PASS'
    if record['stage']=='mixed_refusal':
        assert set(record)=={'stage','status','error_code','mixed_pair_proven','output_absent'}
        assert record['error_code']==-4 and record['mixed_pair_proven']is True and record['output_absent']is True
        return
    assert set(record)=={'stage','status','receive_address','change_address','outpoint','spend_txid','confirmations',
                          'source_wallet_unloaded','exported_seed_matches','parent_descriptors_match','known_input_consumed'} | (
                          {'original_pair_inactive','replacement_distinct'}if record['stage']=='replacement'else set())
    assert all(record.get(k)is True for k in ['source_wallet_unloaded','exported_seed_matches','parent_descriptors_match','known_input_consumed'])
    assert type(record['confirmations'])is int and record['confirmations']>=1
    assert set(record['outpoint'])=={'txid','vout'} and TXID.fullmatch(record['outpoint']['txid'])
    assert type(record['outpoint']['vout'])is int and record['outpoint']['vout']>=0
    assert TXID.fullmatch(record['spend_txid']) and record['spend_txid']!=record['outpoint']['txid']
    assert all(isinstance(record[k],str) and record[k].startswith('btxrt1')for k in ['receive_address','change_address'])
    assert record['receive_address']!=record['change_address']
    if record['stage']=='replacement':assert record['original_pair_inactive']is True and record['replacement_distinct']is True


def public_completed_stages(records):
    safe=[]
    if not isinstance(records,list):return safe
    for index,record in enumerate(records):
        try:
            validate_record(record)
            assert index<len(STAGES) and record['stage']==STAGES[index]
        except (AssertionError,KeyError,TypeError):break
        safe.append(record)
    return safe


def assess(exit_code, records, *, timed_out=False, cleanup_ok=False, provenance_ok=False):
    completed=public_completed_stages(records)
    result={'status':'FAIL_OR_INCOMPLETE','native_exit':exit_code,'native_timed_out':timed_out,
            'cleanup_ok':cleanup_ok,'provenance_ok':provenance_ok,'stages':completed,
            'last_completed_stage':completed[-1]['stage']if completed else None,
            'native_product_verdict':'UNQUALIFIED'}
    if timed_out:result['reason']='OUTER_TIMEOUT';return result
    if exit_code==77:result['reason']='SKIPPED_NOT_PASS';return result
    if type(exit_code)is not int or exit_code!=0:result['reason']='NATIVE_NONZERO_NOT_A_PRODUCT_DIAGNOSIS';return result
    if not cleanup_ok or not provenance_ok:result['reason']='CLEANUP_OR_PROVENANCE_FAILURE';return result
    if not isinstance(records,list) or len(records)!=3 or len(completed)!=3:
        result['reason']='MISSING_DUPLICATE_OR_INVALID_STAGE';return result
    try:
        assert records[0]['outpoint']!=records[1]['outpoint']
        assert records[0]['receive_address']!=records[1]['receive_address']
        assert records[0]['change_address']!=records[1]['change_address']
        assert records[0]['spend_txid']!=records[1]['spend_txid']
    except (AssertionError,KeyError,TypeError):
        result['reason']='REQUIRED_ACCEPTANCE_EVIDENCE_INVALID';return result
    result.update(status='PASS',native_product_verdict='SCOPED_REGTEST_ACCEPTANCE_PASS')
    return result


def read_progress(path):
    if not path.is_file():return []
    return [json.loads(line)for line in path.read_text().splitlines()if line.strip()]
