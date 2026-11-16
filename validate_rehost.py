import json,sys
r=json.load(open(sys.argv[1]));assert int(sys.argv[2])==0 and r['status']=='COMPLETE'
assert r['provider']=='MINIO' and r['fake'] is False and r['originals_preserved'] is True
assert set(r['attempts'])=={'same_path','relocated_copy','relocated_after_restart','materialized_checkout','original_path_restored'}
for n in ('same_path','original_path_restored'):assert r['attempts'][n]['response']['cloud_uploaded'] is True and r['attempts'][n]['remote_bytes_match'] is True
for a in r['attempts'].values():assert a['response']['uri']==r['uri'] and a['response']['artifact_id']==r['artifact']
print(r['classification'])
