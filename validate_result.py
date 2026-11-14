import json,sys
from pathlib import Path
def validate(r):
    assert r.get('phase')=='VALID_EOF_QUOTA_RESUME_PASS'
    for k in ['quota_checkpoint_survived_restart','restart_exact_export','restart_returned_identity_match','exact_export','restart_local']:assert r.get(k) is True,k
    assert r.get('origin_get_ops')==0
    return True
if __name__=='__main__':validate(json.loads(Path(sys.argv[1]).read_text()));print('QUOTA_BLOCKED_CHECKPOINT_AND_EXACT_RESTART_PASS')
