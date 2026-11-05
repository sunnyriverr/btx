"""Explicit two-field hosted-image transition, for one unbuilt object only."""
from pathlib import Path
import os,json,hashlib,subprocess,shutil,re
import checkpoint
P=Path(__file__).resolve().parent;root=Path(os.environ['BTX_NATIVE_ROOT']);build=root/'project-build';e=root/'evidence';source=Path(os.environ['GITHUB_WORKSPACE'])/'btx'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
state=json.loads((e/'result.json').read_text());original=json.loads((P/'original-profile.json').read_text())
transition=json.loads((P/'profile-transition.json').read_text());baseline=json.loads((P/'path-baseline.json').read_text());catalog=json.loads((e/'before-source.json').read_text())
assert state['base']==baseline['source']==original['source']==transition['source']
assert all(state['stages'].get(s)=='COMPLETE' for s in ['openssl','vcpkg','profile'])
def differences(a,b,prefix=''):
    out={}
    for key in sorted(set(a)|set(b)):
        x,y=a.get(key),b.get(key);name=prefix+key
        if isinstance(x,dict) and isinstance(y,dict):out.update(differences(x,y,name+'.'))
        elif x!=y:out[name]=[x,y]
    return out
actual=differences(original,state['profile'])
assert actual==transition['allowed_differences'], actual
assert subprocess.check_output(['ninja','--version'],text=True).strip()=='1.13.2'
# Never spoof the current environment or modify the checkpoint's identity rules.
# Only the explicitly compared original profile is used to validate original
# cached bytes; both original and actual current profiles remain in evidence.
restored=checkpoint.restore(root,source,original,catalog);assert restored['restored']
commands=json.loads((build/'compile_commands.json').read_text())
h=hashlib.sha256(json.dumps(commands,sort_keys=True,separators=(',',':')).encode()).hexdigest()
assert h==baseline['compile_commands_canonical_sha256']
cache=(build/'CMakeCache.txt').read_text()
for f in ['WITH_MODELNET:BOOL=ON','BUILD_TESTS:BOOL=ON','ENABLE_WALLET:BOOL=ON','WITH_ZMQ:BOOL=ON']: assert f in cache
manifest=e/'verified-resume.ninja';shutil.copyfile(build/'build.ninja',manifest);assert sha(manifest)==sha(build/'build.ninja')
cmd=['ninja','-C',str(build),'-f',str(manifest),'-d','explain','-n','btxd'];log=e/'verified-resume-dry-run.log'
with log.open('wb') as f: rc=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT,timeout=120).returncode
text=log.read_text(errors='replace');changed=text.count('ninja explain: command line changed for ');stale=text.count('ninja explain: stored deps info out of date')
steps=re.findall(r'^\[(\d+)/(\d+)\]',text,re.M);planned=int(steps[-1][1]) if steps else 0
for name,info in catalog['files'].items():
    if info['git_mode']!='120000':assert sha(source/name)==info['working_sha256'],name
for f in ['CMakeCache.txt','compile_commands.json','build.ninja','CMakeFiles/rules.ninja']:shutil.copyfile(build/f,e/('resume-'+Path(f).name))
r={'source':state['base'],'restore':restored,'command':cmd,'exit':rc,'planned_steps':planned,'command_changed_objects':changed,'stale_deps':stale,'all_commands_identical_to_original':True,'commands_count':len(commands),'canonical_commands_sha256':h,'original_manifest_sha256':sha(build/'build.ninja'),'frozen_manifest_sha256':sha(manifest),'dry_log_sha256':sha(log),'source_contents_unchanged':True,'cmake_reconfigured':False,'product_compilation':False,'profile_transition':actual,'original_profile':original,'actual_current_profile':state['profile'],'scope':transition['scope'],'manual_object_timestamp_edits':False,'manual_ninja_log_edits':False}
(e/'verified-resume-result.json').write_text(json.dumps(r,indent=2))
assert rc==0 and changed==0 and stale==0 and 0<planned<150
state.update(checkpoint_restore=restored,status='SCOPED_CACHED_SINGLE_OBJECT_READY',resume_dry_run=r)
(e/'result.json').write_text(json.dumps(state,indent=2))
print(json.dumps({'scope':r['scope'],'differences':actual,'files_verified':restored['files_verified'],'planned_steps':planned},indent=2))
