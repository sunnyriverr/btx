from pathlib import Path
import os,sys,json,base64,subprocess,shutil,stat,re
import checkpoint
import integration_support as s
P=Path(__file__).resolve().parent;s.STATE=s.E/'maintained.json';s.R=json.loads(s.STATE.read_text());R=s.R;C=json.loads((P/'candidate.json').read_text());I=json.loads((P/'maintained-inputs.json').read_text());sha=checkpoint.digest
try:
 assert R['status']=='RESTORED_VERIFIED'
 cp=json.loads((s.BUILD/'btx-checkpoint.json').read_text())
 baseline=sha(s.BUILD/'bin/test_btx.exe');assert baseline==I['retained_binary_sha256']
 bundle=s.E/'mock-candidate.bundle';bundle.write_bytes(base64.b64decode((P/'candidate.bundle.base64').read_text()));assert sha(bundle)==C['bundle_sha256']
 s.need('mock-bundle-fetch',['git','fetch',str(bundle),C['ref']],60)
 s.need('mock-checkout',['git','checkout','--detach',C['target']],60)
 cat=s.catalog(C['target'],'mock-before')
 assert [n for n in cat['files'] if cat['files'][n]!=R['source_catalog']['files'].get(n)]==['src/test/pq_phase4_tests.cpp']
 plan=['ninja','-C',str(s.BUILD),'-n','-d','explain','test_btx'];s.need('mock-build-plan',plan,120)
 text=(s.E/'mock-build-plan.log').read_text(errors='replace');actions=re.findall(r'^\[\d+/\d+\] (.*)',text,re.M);assert 0<len(actions)<=15,actions
 objects=[a for a in actions if a.startswith('Building CXX object')];assert len(objects)<=3,objects
 assert all('pq_phase4_tests.cpp' in a or 'clientversion.cpp' in a for a in objects),objects
 R['mock_build_plan']=actions;s.save()
 s.need('mock-focused-build',['ninja','-C',str(s.BUILD),'-j','2','test_btx'],600)
 current=sha(s.BUILD/'bin/test_btx.exe');assert current!=baseline
 R.update(source=C['target'],source_catalog=cat,baseline_binary_sha256=baseline,unit_binary_sha256=current,status='RESTORED_BINARY_READY')
 m=json.loads((P/'completion-manifest.json').read_text());m['binary_sha256']=current;(P/'completion-manifest.json').write_text(json.dumps(m));shutil.copyfile(P/'completion-manifest.json',s.E/'completion-manifest.json');s.save()
 import batches
 batches.run()
 assert len(R['batch_results'])==24
finally:
 survivors=s.owned_processes();R['owned_processes_before_cleanup']=survivors;s.quiesce()
 if R.get('unit_data'):
  data=Path(R['unit_data']);assert data.parent==Path('D:/') and data.name=='bc'+os.environ['GITHUB_RUN_ID']
  if data.exists():shutil.rmtree(data)
  R['runtime_data_removed']=not data.exists()
 if 'cp' in globals():
  changed=[];missing=[]
  for n,item in cp['files'].items():
   f=s.ROOT/n
   if not f.is_file():missing.append(n)
   elif sha(f)!=item['sha256']:changed.append(n)
  R['mock_cached_files_changed']=changed;R['mock_cached_files_missing']=missing
  changed_objects=[n for n in changed if n.endswith('.obj')];R['mock_changed_objects']=changed_objects
  assert not missing
  assert len(changed_objects)<=3 and all('pq_phase4_tests.cpp' in n or 'clientversion.cpp' in n for n in changed_objects),changed_objects
  assert all(not n.startswith('vcpkg-installed/') for n in changed)
  assert not any(n.endswith(x) for n in changed for x in ['CMakeCache.txt','compile_commands.json'])
  assert all(not n.endswith('.exe') or n.endswith('test_btx.exe') for n in changed)
 if 'cat' in globals():assert s.catalog(C['target'],'mock-after')==cat
 R['mock_cleanup_verified']=not survivors and R.get('runtime_data_removed',False) and R.get('short_drive_removed',False)
 R['mock_repair_pass']=R['mock_cleanup_verified'] and len(R.get('batch_results',[]))==24 and all(j['state']=='passed' for j in R['batch_results'])
 R['full_unit_acceptance']=False;s.save()
assert R['mock_repair_pass'],[(j['suite'],j['state'])for j in R.get('batch_results',[])]
