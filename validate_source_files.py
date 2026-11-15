"""Strict consumer. Native runner must separately record framework exit status."""
import json, sys
from pathlib import Path

def need(condition, reason):
    if not condition: raise ValueError(reason)
def same_result(case):
    a,b=case['restored'],case['restart']
    need(a==b,'restart differs')
    need(set(a['ids'])=={'model_id','artifact_id'},'missing identities')
    for v in a['ids'].values():need(isinstance(v,str) and len(v)==96 and all(x in '0123456789abcdef' for x in v),'bad identity')
    need(set(a['files'])=={'assets/config.json','model.safetensors'},'missing fixture branch')
    for v in a['files'].values():need(isinstance(v,str) and len(v)==96 and all(x in '0123456789abcdef' for x in v),'bad file digest')
def validate(data):
    need(data.get('schema')==1 and data.get('backend')=='real-MinIO' and data.get('layout')=='SOURCE_FILES','wrong profile/fallback')
    need(data.get('cleanup') is True and data.get('native_body_completed') is True and not data.get('failure'),'incomplete/unclean/error')
    need(set(data.get('cases',{}))=={'B1','B2'},'missing or extra cases')
    for case in data['cases'].values():
        need(case.get('status')=='PASS' and case.get('direct_seed_flags_used') is False,'case failed/skipped/wrong caller')
        same_result(case)
    one,two=data['cases']['B1'],data['cases']['B2']
    need(one['restored']==two['restored']==data.get('expected'),'paired fixture identity or original expected hashes changed')
    need(isinstance(one['catalog_hash_unchanged'],str) and len(one['catalog_hash_unchanged'])==96,'catalog precondition missing')
    for pair in ((one['before'],one['after']),(two['baseline'],two['charged']),(two['charged'],two['after'])):
        need(pair[0]['budget_day_utc']==pair[1]['budget_day_utc'],'day rollover')
        need(type(pair[0]['budget_used_gets_day']) is int and type(pair[1]['budget_used_gets_day']) is int,'noninteger counters')
        need(pair[1]['budget_used_gets_day']>pair[0]['budget_used_gets_day'],'counter mismatch')
    need(two['charged']['budget_used_gets_day']==two['cap'],'cap not reached')
    need(type(two['resume_offset']) is int and two['resume_offset']>=4<<20,'verified prefix missing')
    need(type(two['resume_gets']) is int and 0<two['resume_gets']<two['full_large_reads'],'resume did not save reads')
    need(two['after']['budget_used_gets_day']-two['charged']['budget_used_gets_day']==two['resume_gets'],'resume accounting mismatch')
    need(two.get('persistent_refusal') is True and two.get('healthy_control') is True,'refusal/control missing')
    exits=data.get('helper_exits',[]);need(len(exits)>=5 and all(type(x) is int and x==0 for x in exits),'helper cleanup evidence missing')
    return True
if __name__=='__main__':
    directory=Path(sys.argv[1]);need((directory/'native-exit.txt').read_text().strip()=='0','native/framework exit nonzero')
    validate(json.loads((directory/'source-files-results.json').read_text()));print('SOURCE_FILES_TWO_CASES_PASS')
