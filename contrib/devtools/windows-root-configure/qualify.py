"""Private same-test repair qualification; no broad unit campaign or cache save."""
from pathlib import Path
import os,sys,json,base64,subprocess,shutil
import checkpoint
import integration_support as s
P=Path(__file__).resolve().parent;s.STATE=s.E/'maintained.json';s.R=json.loads(s.STATE.read_text());R=s.R;sha=checkpoint.digest
C=json.loads((P/'candidate.json').read_text());I=json.loads((P/'maintained-inputs.json').read_text());results=[]
allowed=['proc08.cpp','proc08_tests.cpp','clientversion.cpp','matmul_v4_rc_production_canary.cpp','matmul_v4_rc_production_golden_manifest.cpp']
try:
 assert R['status']=='RESTORED_VERIFIED'
 assert sha(s.BUILD/'bin/test_btx.exe')==I['retained_binary_sha256']
 cp=json.loads((s.BUILD/'btx-checkpoint.json').read_text())
 bundle=s.E/'candidate.bundle';bundle.write_bytes(base64.b64decode((P/'candidate.bundle.base64').read_text()));assert sha(bundle)==C['bundle_sha256']
 for n,ref in enumerate(C['refs']):s.need('qualification-fetch-'+str(n),['git','fetch',str(bundle),ref],60)
 os.environ.update(VCPKG_ROOT=str(s.ROOT/'vcpkg'),VCPKG_DISABLE_METRICS='1',VCPKG_BINARY_SOURCES='clear;files,'+str(s.ROOT/'binary-cache')+',read')
 commands=sha(s.BUILD/'compile_commands.json')
 for label,source in [('before',C['before']),('after',C['target'])]:
  s.need(label+'-checkout',['git','checkout','--detach',source],60)
  catalog=s.catalog(source,label+'-source')
  assert sha(s.SOURCE/'src/test/proc08_tests.cpp')==C['test_sha256']
  s.need(label+'-regenerate',['ninja','-C',str(s.BUILD),'build.ninja'],180)
  assert sha(s.BUILD/'compile_commands.json')==commands
  s.need(label+'-plan',['ninja','-C',str(s.BUILD),'-n','-d','explain','test_btx'],120)
  plan=(s.E/(label+'-plan.log')).read_text(errors='replace')
  # Regeneration may still appear in the dry run; refuse a demonstrated broad C++ plan.
  lines=[x for x in plan.splitlines()if 'Building CXX object' in x]
  assert len(lines)<=5 and all(any(x in line for x in allowed)for line in lines),lines
  s.need(label+'-build',['ninja','-C',str(s.BUILD),'-j','2','test_btx'],600)
  binary=sha(s.BUILD/'bin/test_btx.exe')
  R.update(source=source,source_catalog=catalog,unit_binary_sha256=binary,status='RESTORED_BINARY_READY');s.save()
  m=json.loads((P/'completion-manifest.json').read_text());m.update(source=source,binary_sha256=binary);(P/'completion-manifest.json').write_text(json.dumps(m));(P/'current-inputs.json').write_text(json.dumps(dict(target=source)))
  proc=subprocess.run([sys.executable,str(P/'batches.py'),'run'],timeout=550);s.R=json.loads(s.STATE.read_text());R=s.R;assert proc.returncode==0
  rows=R['batch_results'];assert len(rows)==2
  for n in range(2):
   for ext in ['xml','log']:shutil.copyfile(s.E/('suite-'+str(n).zfill(4)+'.'+ext),s.E/(label+'-suite-'+str(n)+'.'+ext))
  assert sha(s.BUILD/'compile_commands.json')==commands and s.catalog(source,label+'-after-tests')==catalog
  survivors=s.owned_processes();assert not survivors;s.quiesce()
  data=Path(R['unit_data']);assert data.parent==Path('D:/')and data.name=='bc'+os.environ['GITHUB_RUN_ID'];shutil.rmtree(data);assert not data.exists() and R['short_drive_removed']
  results.append(dict(stage=label,source=source,test_sha256=C['test_sha256'],binary_sha256=binary,results=rows,cleanup=True))
  (s.E/'qualification-results.json').write_text(json.dumps(results,indent=2)+'\n')
  expected='failed' if label=='before' else 'passed';assert all(x['state']==expected for x in rows),[(x['state'],x['cases'])for x in rows]
  s.save()
 changed=[]
 for name,v in cp['files'].items():
  f=s.ROOT/name;assert f.is_file()
  if sha(f)!=v['sha256']:changed.append(name)
 objects=[n for n in changed if n.endswith('.obj')];assert len(objects)<=5 and all(any(x in n for x in allowed)for n in objects)
 assert not any(n.startswith('vcpkg-installed/')for n in changed)
 assert sha(s.BUILD/'btx-checkpoint.json')==I['checkpoint_sha256']
 R.update(qualification_complete=True,qualification_cases=2,qualification_results=results,qualification_changed_objects=objects,preserved_objects=I['objects']-len(objects),changed_cache_files=changed,full_unit_acceptance=False,input_cache_saved=False,runtime_data_removed=True);s.save()
finally:
 s.R=json.loads(s.STATE.read_text());R=s.R;s.quiesce();s.save()
assert R.get('qualification_complete')
