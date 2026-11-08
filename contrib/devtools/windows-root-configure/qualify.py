from pathlib import Path
import os,sys,json,base64,subprocess,shutil,re
import checkpoint
import integration_support as s
from overlay import strengthen,CHECKS
P=Path(__file__).resolve().parent;s.STATE=s.E/'maintained.json';s.R=json.loads(s.STATE.read_text());R=s.R;sha=checkpoint.digest
C=json.loads((P/'candidate.json').read_text());I=json.loads((P/'maintained-inputs.json').read_text());results=[];target_file=s.SOURCE/'src/test/pq_phase4_tests.cpp'
try:
 assert R['status']=='RESTORED_VERIFIED'
 assert sha(s.BUILD/'bin/test_btx.exe')==I['retained_binary_sha256']
 cp=json.loads((s.BUILD/'btx-checkpoint.json').read_text())
 bundle=s.E/'candidate.bundle';bundle.write_bytes(base64.b64decode((P/'candidate.bundle.base64').read_text()));assert sha(bundle)==C['bundle_sha256'];s.need('qualification-fetch',['git','fetch',str(bundle),C['ref']],60)
 os.environ.update(VCPKG_ROOT=str(s.ROOT/'vcpkg'),VCPKG_DISABLE_METRICS='1',VCPKG_BINARY_SOURCES='clear;files,'+str(s.ROOT/'binary-cache')+',read')
 for label,source in [('before',C['base']),('after',C['target'])]:
  s.need(label+'-checkout',['git','checkout','--detach',source],60)
  original=s.catalog(source,label+'-original');plain=target_file.read_bytes().decode();modified=strengthen(plain);target_file.write_bytes(modified.encode());overlay_sha=sha(target_file)
  (s.E/(label+'-qualified-pq_phase4_tests.cpp')).write_bytes(target_file.read_bytes())
  assert subprocess.check_output(['git','diff','--name-only'],cwd=s.SOURCE,text=True).splitlines()==['src/test/pq_phase4_tests.cpp']
  commands=sha(s.BUILD/'compile_commands.json')
  s.need(label+'-regenerate',['ninja','-C',str(s.BUILD),'build.ninja'],180)
  assert sha(s.BUILD/'compile_commands.json')==commands
  s.need(label+'-plan',['ninja','-C',str(s.BUILD),'-n','-d','explain','test_btx'],120)
  s.need(label+'-build',['ninja','-C',str(s.BUILD),'-j','2','test_btx'],600)
  binary=sha(s.BUILD/'bin/test_btx.exe')
  R.update(source=source,source_catalog=original,unit_binary_sha256=binary,status='RESTORED_BINARY_READY');s.save()
  m=json.loads((P/'completion-manifest.json').read_text());m.update(source=source,binary_sha256=binary);(P/'completion-manifest.json').write_text(json.dumps(m));inputs=json.loads((P/'current-inputs.json').read_text());inputs['target']=source;(P/'current-inputs.json').write_text(json.dumps(inputs))
  proc=subprocess.run([sys.executable,str(P/'batches.py'),'run'],timeout=600);s.R=json.loads(s.STATE.read_text());R=s.R;assert proc.returncode==0
  rows=R['batch_results'];assert len(rows)==3
  for n in range(3):
   for ext in ['xml','log']:
    shutil.copyfile(s.E/('suite-'+str(n).zfill(4)+'.'+ext),s.E/(label+'-suite-'+str(n)+'.'+ext))
  assert sha(target_file)==overlay_sha and sha(s.BUILD/'compile_commands.json')==commands
  survivors=s.owned_processes();assert not survivors;s.quiesce()
  data=Path(R['unit_data']);assert data.parent==Path('D:/')and data.name=='bc'+os.environ['GITHUB_RUN_ID'];shutil.rmtree(data);assert not data.exists() and R['short_drive_removed']
  results.append(dict(stage=label,source=source,overlay_sha256=overlay_sha,binary_sha256=binary,results=rows,cleanup=True))
  (s.E/'qualification-results.json').write_text(json.dumps(results,indent=2)+'\n')
  s.need(label+'-restore-owned-fixture',['git','restore','--source=HEAD','--','src/test/pq_phase4_tests.cpp'],60)
  assert s.catalog(source,label+'-restored')==original
  if label=='before':assert all(x['state']=='failed' for x in rows),[(x['state'],x['cases'])for x in rows]
  else:assert all(x['state']=='passed' for x in rows),[(x['state'],x['cases'])for x in rows]
  s.save()
 changed=[]
 for name,v in cp['files'].items():
  f=s.ROOT/name;assert f.is_file()
  if sha(f)!=v['sha256']:changed.append(name)
 objects=[n for n in changed if n.endswith('.obj')];assert len(objects)<=4 and all(any(x in n for x in ['pq_phase4_tests.cpp','clientversion.cpp','matmul_v4_rc_production_canary.cpp','matmul_v4_rc_production_golden_manifest.cpp'])for n in objects)
 assert not any(n.startswith('vcpkg-installed/')for n in changed)
 R.update(qualification_complete=True,qualification_cases=3,qualification_results=results,qualification_changed_objects=objects,full_unit_acceptance=False,input_cache_saved=False);s.save()
finally:
 s.R=json.loads(s.STATE.read_text());R=s.R;s.quiesce();s.save()
assert R.get('qualification_complete')
