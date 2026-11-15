import json,sys,copy
from pathlib import Path
def validate(root):
    def read(n):return json.loads((root/n).read_text())
    normal=read('normal-current-result.json');assert normal.get('phase')=='NORMAL_RECOVERY_PASS' and normal.get('exact_export') is True and normal.get('restart_local') is True
    partial=read('partial-valid-result.json');assert partial.get('phase')=='RECOVERED_BYTES_AND_RESTART'
    corrected=read('corrected-origin-result.json');assert corrected.get('phase')=='RECOVERED_CORRECTED_ORIGIN'
    for r,keys in [(partial,['retry_bytes_match','retry_materialized_match','restart_bytes_match','restart_materialized_match']),(corrected,['corrected_bytes_match','corrected_materialized_match','corrected_restart_bytes_match','corrected_restart_materialized_match'])]:
        for k in keys:assert r.get(k) is True,k
    controls=read('cloud-controls.json');assert {x['case'] for x in controls}=={'corrupt-origin','budget-refusal'}
    for x in controls:assert x.get('healthy_model_passed') is True and x.get('live_pieces')==0
    quota=read('quota-eof-result.json');assert quota.get('phase')=='VALID_EOF_QUOTA_RESUME_PASS' and quota.get('origin_get_ops')==0 and quota.get('exact_export') is True and quota.get('restart_local') is True
    return True
if __name__=='__main__':validate(Path(sys.argv[1]));print('CURRENT_HELPER_RECOVERY_QUALIFIED')
