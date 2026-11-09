from pathlib import Path
import json,sys,shutil
import checkpoint
import integration_support as s
P=Path(__file__).resolve().parent;I=json.loads((P/'maintained-inputs.json').read_text());s.STATE=s.E/'maintained.json';s.R=json.loads(s.STATE.read_text());R=s.R;M=json.loads((P/'completion-manifest.json').read_text())
if sys.argv[1]=='ready':
 assert R['status']=='RESTORED_VERIFIED';assert checkpoint.digest(s.BUILD/'bin/test_btx.exe')==I['retained_binary_sha256']==M['binary_sha256'];assert len(M['jobs'])==8;assert not s.owned_processes();R['unit_binary_sha256']=M['binary_sha256'];R['status']='RESTORED_BINARY_READY';shutil.copyfile(P/'completion-manifest.json',s.E/'completion-manifest.json');s.save()
else:
 assert R.get('cache_unchanged_verified')and R.get('runtime_data_removed')and R.get('short_drive_removed');assert len(R.get('batch_results',[]))==8;R['selected_batch_pass']=all(x['state']=='passed'for x in R['batch_results']);R['full_unit_acceptance']=False;s.save()
