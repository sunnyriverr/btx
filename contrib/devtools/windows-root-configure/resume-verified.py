"""Resume ONLY the identical, byte-verified configured project. No reconfigure."""
from pathlib import Path
import os,json,hashlib,subprocess,shutil,re
import checkpoint
P=Path(__file__).resolve().parent;root=Path(os.environ['BTX_NATIVE_ROOT']);build=root/'project-build';e=root/'evidence';source=Path(os.environ['GITHUB_WORKSPACE'])/'btx'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
state=json.loads((e/'result.json').read_text());baseline=json.loads((P/'path-baseline.json').read_text());catalog=json.loads((e/'before-source.json').read_text())
assert state['base']==baseline['source'] and state['profile']['source']==baseline['source'];assert all(state['stages'].get(s)=='COMPLETE' for s in ['openssl','vcpkg','profile'])
# Validates every cached file/profile and the exact source before restoring source
# times. An absent/different checkpoint is an error, never a silent cold build.
restored=checkpoint.restore(root,source,state['profile'],catalog);assert restored['restored']
commands=json.loads((build/'compile_commands.json').read_text());hashcommands=hashlib.sha256(json.dumps(commands,sort_keys=True,separators=(',',':')).encode()).hexdigest();assert hashcommands==baseline['compile_commands_canonical_sha256']
cache=(build/'CMakeCache.txt').read_text()
for f in ['WITH_MODELNET:BOOL=ON','BUILD_TESTS:BOOL=ON','ENABLE_WALLET:BOOL=ON','WITH_ZMQ:BOOL=ON']:
 assert f in cache
manifest=e/'verified-resume.ninja';shutil.copyfile(build/'build.ninja',manifest);assert sha(manifest)==sha(build/'build.ninja')
# The frozen copy has no generated-manifest edge. All included rules are from the
# verified checkpoint. This path is valid only for this identical configuration.
cmd=['ninja','-C',str(build),'-f',str(manifest),'-d','explain','-n','btxd'];log=e/'verified-resume-dry-run.log'
with log.open('wb') as f:code=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT,timeout=120).returncode
text=log.read_text(errors='replace');changed=text.count('ninja explain: command line changed for ');stale=text.count('ninja explain: stored deps info out of date');steps=re.findall(r'^\[(\d+)/(\d+)\]',text,re.M);planned=int(steps[-1][1]) if steps else 0
for name,info in catalog['files'].items():
 if info['git_mode']!='120000':assert sha(source/name)==info['working_sha256'],name
for f in ['CMakeCache.txt','compile_commands.json','build.ninja','CMakeFiles/rules.ninja']:
 shutil.copyfile(build/f,e/('resume-'+Path(f).name))
result={'source':state['base'],'restore':restored,'command':cmd,'exit':code,'planned_steps':planned,'command_changed_objects':changed,'stale_deps':stale,'all_commands_identical_to_original':True,'commands_count':len(commands),'canonical_commands_sha256':hashcommands,'original_manifest_sha256':sha(build/'build.ninja'),'frozen_manifest_sha256':sha(manifest),'dry_log_sha256':sha(log),'source_contents_unchanged':True,'cmake_reconfigured':False,'product_compilation':False,'manual_object_timestamp_edits':False,'manual_ninja_log_edits':False,'scope':'Exact source/profile cached configuration only; mismatch refuses. Future build must use this verified frozen manifest, not trigger an unnecessary CMake regeneration.'}
(e/'verified-resume-result.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
assert code==0 and changed==0 and stale==0 and 0<planned<150
state.update(checkpoint_restore=restored,status='VERIFIED_CACHED_CONFIGURATION_READY',resume_dry_run=result);(e/'result.json').write_text(json.dumps(state,indent=2))
