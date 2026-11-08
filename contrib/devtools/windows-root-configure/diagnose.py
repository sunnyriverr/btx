from pathlib import Path
import os,sys,json,hashlib,shutil
import checkpoint
import integration_support as s
P=Path(__file__).resolve().parent;s.STATE=s.E/'maintained.json';s.R=json.loads(s.STATE.read_text());R=s.R;sha=checkpoint.digest
I=json.loads((P/'maintained-inputs.json').read_text());owned=s.ROOT/('proc08-diagnostic-'+os.environ['GITHUB_RUN_ID'])
try:
 assert R['status']=='RESTORED_VERIFIED'
 assert sha(s.BUILD/'bin/test_btx.exe')==I['retained_binary_sha256']
 cp=json.loads((s.BUILD/'btx-checkpoint.json').read_text())
 names=[n for n in cp['files']if n.replace('\\','/').endswith('/proc08.cpp.obj')];assert len(names)==1
 name=names[0];obj=s.ROOT/name;assert sha(obj)==cp['files'][name]['sha256']
 entries=json.loads((s.BUILD/'compile_commands.json').read_text());commands=[c for c in entries if c['file'].replace('\\','/').endswith('/modelnet/proc08/proc08.cpp')];assert len(commands)==1
 command=commands[0].get('command',str(commands[0].get('arguments')))
 assert 'clang-cl'in command and ('-MT'in command or '/MT'in command)and 'DNDEBUG'in command
 assert '/MD'not in command and '-MD'not in command and 'flto'not in command and '/GL'not in command
 assert not owned.exists();owned.mkdir();(owned/'runtime').mkdir()
 target=owned/'probe.exe'
 compile=['clang-cl','/nologo','/std:c++20','/EHsc','/MT','/O2','/DNDEBUG','/DWIN32','/I'+str(s.SOURCE/'src'),str(P/'probe.cpp'),str(obj),'/Fe'+str(target),'/Fo'+str(owned/'probe.obj')]
 R['diagnostic_inputs']=dict(original_object=name,object_sha256=sha(obj),original_compile_entry=commands[0],probe_source_sha256=sha(P/'probe.cpp'),kind='Unmodified cached Proc08 object plus real original headers; standalone diagnostic driver only; no product source or generated target rebuild');s.save()
 s.need('proc08-probe-compile',compile,90)
 R['diagnostic_binary_sha256']=sha(target);s.need('proc08-probe-run',[str(target),str(owned/'runtime')],60)
 records=[json.loads(line)for line in(s.E/'proc08-probe-run.log').read_text().splitlines()];assert len(records)==15;assert records[0]==dict(same_file_mixed=True,same_file_forward=True)
 cases={x['case']:x for x in records[1:]};assert len(cases)==14
 for key in ['inside_file_native','inside_dir_native']:
  assert cases[key]['accepted']and cases[key]['error']=='' and cases[key]['research_outside']
 for key in ['root_self','inside_file_mixed','inside_file_forward','inside_dir_mixed','inside_missing_forward']:
  assert not cases[key]['accepted']and cases[key]['error']=='INSIDE'and not cases[key]['research_outside']
 for key in ['inside_missing_native','missing_outside']:
  assert not cases[key]['accepted']and cases[key]['error']=='ABSENT'
 for key in ['outside_native','outside_forward','prefix_sibling_native','prefix_sibling_forward']:
  assert cases[key]['accepted']and cases[key]['research_outside']and cases[key]['error']==''
 assert not cases['empty']['accepted']and cases['empty']['error']=='FIELD'
 for item in cases.values():assert not item['release_qualified']and not item['gpu_passed']and not item['windows_passed']
 f=cases['inside_file_native'];mixed=cases['inside_file_mixed'];assert f['root']==mixed['root']and f['path'].replace('\\','/')==mixed['path'].replace('\\','/')
 offset=len(f['root']);assert f['path'][offset]=='\\'and mixed['path'][offset]=='/'
 (s.E/'proc08-observations.json').write_text(json.dumps(records,indent=2)+'\n');R['diagnostic_cause_proved']=True;R['full_unit_acceptance']=False;s.save()
finally:
 s.quiesce()
 if owned.exists():shutil.rmtree(owned)
 R['diagnostic_runtime_removed']=not owned.exists();assert R['diagnostic_runtime_removed']
 if 'cp'in globals():
  for n,v in cp['files'].items():assert sha(s.ROOT/n)==v['sha256'],n
  R['diagnostic_cached_files_unchanged']=len(cp['files']);R['diagnostic_cached_objects_unchanged']=sum(n.endswith('.obj')for n in cp['files']);R['diagnostic_cache_unchanged']=True
 assert s.catalog(I['source'],'after-proc08-probe')==R['source_catalog']
 R['diagnostic_cleanup_verified']=not s.owned_processes()and R['diagnostic_runtime_removed'];s.save()
assert R.get('diagnostic_cause_proved')and R['diagnostic_cleanup_verified']
