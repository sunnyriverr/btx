from pathlib import Path
import hashlib,json,shutil,subprocess
root=Path.cwd();r=root/'records'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
prod=json.loads((root/'saved/producer.json').read_text());assert prod['source_identity']=='1e2f8b5f12295002334d3390c12cac0bb4ae2aff' and prod['status']=='BUILD_PASS'
shutil.copytree(root/'reference-source/.git',root/'source/.git')
files=['src/wallet/rpc/backup.cpp','test/functional/test_runner.py','test/functional/wallet_seed_pruned_recovery.py'];hashes={}
for name in files:
 p=root/'candidate-inputs'/name;dst=root/'source'/name;dst.parent.mkdir(parents=True,exist_ok=True);dst.write_bytes(p.read_bytes());hashes[name]=sha(dst)
actual=subprocess.check_output(['git','-C','source','diff','--name-only'],text=True).splitlines();new=subprocess.check_output(['git','-C','source','ls-files','--others','--exclude-standard'],text=True).splitlines();assert set(actual+new)==set(files),(actual,new)
with (r/'candidate-configure.log').open('w') as log:subprocess.run(['cmake','-S','source','-B','build'],stdout=log,stderr=subprocess.STDOUT,check=True,timeout=240)
for n,h in prod['binary_sha256'].items():assert sha(root/'build/bin'/n)==h
plan=subprocess.check_output(['ninja','-C','build','-n','btxd','btx-cli'],text=True);(r/'candidate-plan.log').write_text(plan)
(r/'candidate-inputs.json').write_text(json.dumps({'source':prod['source_identity'],'files_sha256':hashes,'base_binary_sha256':prod['binary_sha256'],'base_checkpoint':14183311941,'retained_objects':sum(1 for p in (root/'build').rglob('*.o')),'pending_steps':sum(l.startswith('[') for l in plan.splitlines()),'test_scope':['wallet_seed_pruned_recovery.py --descriptors','wallet_importbundle_shielded.py --descriptors']},indent=2)+'\n')
print('Candidate verified and configured. Pending steps:',sum(l.startswith('[') for l in plan.splitlines()),flush=True)
