"""Strict saved-observation classifier; no UI/node execution on import."""
REQUIRED = ('connected','panel_repeat_password','loss_warning','panel_mismatch_no_wallet',
 'operation_repeat_password','operation_mismatch_no_wallet','secret_json_disabled',
 'native_cancel_no_wallet','native_approved','web_creation_result','encrypted_locked','intended_passphrase_control',
 'existing_secret_single_field','nonsecret_json_control','send_composer','app_clean_exit')
def classify(s):
    before=s.get('baseline',{});after=s.get('candidate',{})
    intended_before=(before.get('connected') is True and before.get('panel_reached') is True
                     and before.get('panel_repeat_password') is False
                     and before.get('wallets_unchanged') is True and before.get('app_clean_exit') is True)
    gaps=[k for k in REQUIRED if after.get(k) is not True]
    cleanup=(s.get('protected_files_unchanged') is True and s.get('node_clean_exit') is True
             and s.get('runtime_removed') is True and s.get('cleanup_remaining')==[]
             and s.get('cleanup_signals')==[])
    return {'overall':'PASS' if intended_before and not gaps and cleanup and not s.get('error') else 'INCOMPLETE',
            'baseline_expected_failure':intended_before,'missing_candidate_observations':gaps,'cleanup_pass':cleanup}

def offline_checks():
    import copy
    s={'baseline':dict(connected=True,panel_reached=True,panel_repeat_password=False,wallets_unchanged=True,app_clean_exit=True),
       'candidate':dict.fromkeys(REQUIRED,True),'protected_files_unchanged':True,'node_clean_exit':True,
       'runtime_removed':True,'cleanup_remaining':[],'cleanup_signals':[]}
    assert classify(s)['overall']=='PASS'
    for key in REQUIRED:
        for bad in (False,None,'true'):
            x=copy.deepcopy(s);x['candidate'][key]=bad;assert classify(x)['overall']!='PASS'
    for key in ('connected','panel_reached','wallets_unchanged','app_clean_exit'):
        x=copy.deepcopy(s);x['baseline'][key]=False;assert not classify(x)['baseline_expected_failure']
    for key,bad in [('protected_files_unchanged',False),('node_clean_exit',False),('runtime_removed',False),('cleanup_remaining',[1]),('cleanup_signals',[1]),('error','fixture failure')]:
        x=copy.deepcopy(s);x[key]=bad;assert classify(x)['overall']!='PASS'
    return {'valid':1,'negative_controls':len(REQUIRED)*3+10,'pass':True}
if __name__=='__main__':
    import json
    print(json.dumps(offline_checks()))
