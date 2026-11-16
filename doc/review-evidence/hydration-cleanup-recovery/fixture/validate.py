from pathlib import Path
import json,hashlib,sys
p=Path(sys.argv[1]);source=Path(__file__).resolve().parent
b=json.loads((p/'build-result.json').read_text());base=json.loads((p/'native-baseline-host/result.json').read_text());fixed=json.loads((p/'native-candidate-host/result.json').read_text())
assert b['status']=='BUILDS_AND_COMPONENTS_PASS_HOST_RUNTIME_PENDING'
assert fixed['helper_sha256']==b['candidate_helper_sha256'] and fixed['status']=='PASS' and not fixed['failures']
assert base['status']=='FAIL' and set(base['failures'])=={'interrupted_restart_not_local','legacy_restart_not_local'}
assert base['helper_sha256']=='cb783882585291c6ab7d5f0796129336d36dc3963be3db2310bbd25fe6737eae'
for r in [base,fixed]:
 assert r['owned_helpers_exited'] and r['scratch_removed']
 for name in ['normal','interrupted','legacy']:
  c=r['cases'][name];assert c['exact_live_bytes_preserved'] and c['healthy_control']['status']=='local'
  if name!='normal':assert c['boundary']['job_exists'] and c['boundary']['live_bytes_match'] and c['independent_origin_read_matches']
  for got in c['first_restart_attempts']+[c['second_restart']]:
   assert got['automatic_spend_atoms']==0 and got['paid_atoms']==0
   if r is fixed or name=='normal':assert got['status']=='local'
   else:assert got['status']=='not_local' and got['plan']=='WAIT_FREE' and got['cloud_hydrate_error']=='missing piece'
  if r is fixed:assert c['remaining_jobs']==[]
 assert r['cases']['partial']['prefix_not_downloaded_again'] and r['cases']['partial']['healthy_restart']['status']=='local'
 assert r['cases']['integrity']['corrupt_checkpoint_refused'] and r['cases']['integrity']['resumed']['cloud_hydrate_error']=='file SHA-384 mismatch'
 assert r['cases']['integrity']['corrected_retry']['status']=='local' and r['cases']['integrity']['healthy_restart']['status']=='local'
assert not base['cases']['interrupted']['boundary']['quarantine_exists'] and not base['cases']['legacy']['boundary']['quarantine_exists']
assert fixed['cases']['interrupted']['boundary']['quarantine_exists'] and not fixed['cases']['legacy']['boundary']['quarantine_exists']
for name in ['normal','interrupted','legacy']:
 c=fixed['cases'][name];entry=c['entry']
 for got in c['first_restart_attempts']+[c['second_restart']]:assert got['model_id']==entry['model_id'] and got['artifact_id']==entry['artifact_id']
assert fixed['cases']['interrupted']['first_restart_attempts'][0]['origin_get_ops']==0
assert fixed['cases']['legacy']['first_restart_attempts'][0]['origin_get_ops']==1
cases=['job_cleanup_failure_preserves_valid_eof_checkpoint','missing_eof_quarantine_does_not_advance_resume_cursor','short_final_checkpoint_survives_publication_quota_failure','only_complete_file_integrity_mismatches_mark_rejection','finished_hydration_releases_its_quarantine_copy']
for phase in ['baseline','candidate']:
 for index,name in enumerate(cases):
  item=next(x for x in b['commands'] if x['label']==phase+'-'+name);assert item['exit']==(1 if phase=='baseline' and index<2 else 0)
assert 'FAIL q.HasPiece(artifact, 0, 0)' in (p/('baseline-'+cases[0]+'.log')).read_text()
assert 'FAIL !resumed.ApplyRecord(rec, err)' in (p/('baseline-'+cases[1]+'.log')).read_text()
for line in (p/'source-fixture-hashes.txt').read_text().splitlines():
 digest,name=line.split();assert hashlib.sha256((source/name).read_bytes()).hexdigest()==digest,name
assert 'PermissionError' in (p/'wrapper-failure-excerpt.txt').read_text()
print(json.dumps({'qualification':'PASS_SCOPED_LINUX','baseline_native':'two intended interruption failures; normal/partial/integrity controls pass','candidate_native':'all five scenario rows pass','component_cases':'baseline2FAIL3PASS;candidate5PASS','new_interruption_origin_reads':0,'legacy_state_origin_reads':1,'candidate_helper_sha256':fixed['helper_sha256'],'workflow_conclusion':'failure: final summary write permission, after native success','native_rerun':False,'source_identity_verified':True},indent=2))
