import copy,json,sys
KEYS=['healthy_control','catalog_missing_not_local','committed_pieces_survived','catalog_missing_remote_bytes_survived','checkout_reimport_identity_match','checkout_reimport_bytes_match','checkout_reimport_restart_pass','cloud_only_not_local','cloud_only_remote_bytes_survived','normal_reimport_restart_pass']
def validate(r):
    assert r.get('phase')=='QUALIFIED_METADATA_BOUNDARY',r
    for key in KEYS:assert r.get(key) is True,key
    assert r['catalog_missing_response']['status']=='not_local'
    assert r['cloud_only_response']['status']=='not_local'
    return True
if __name__=='__main__':
    if sys.argv[1]=='--selftest':
        good={'phase':'QUALIFIED_METADATA_BOUNDARY',**{k:True for k in KEYS},'catalog_missing_response':{'status':'not_local'},'cloud_only_response':{'status':'not_local'}}
        validate(good)
        for k in KEYS+['phase']:
            bad=copy.deepcopy(good);bad.pop(k)
            try:validate(bad)
            except AssertionError:pass
            else:raise AssertionError('missing result accepted: '+k)
        print('VALIDATOR: complete passes; 11 missing-result controls fail')
    else:validate(json.load(open(sys.argv[1])));print('QUALIFIED_METADATA_BOUNDARY')
