"""Read-only Ninja freshness inspection after the established verified restore."""
from pathlib import Path
import os,json,subprocess,shutil,hashlib,re,collections
root=Path(os.environ['BTX_NATIVE_ROOT']);build=root/'project-build';e=root/'evidence'
sha=lambda f:hashlib.sha256(f.read_bytes()).hexdigest()
state=json.loads((e/'result.json').read_text());assert state['checkpoint_restore']['restored']
# Main manifest copy has no generator edge. The build's original bytes/rules stay
# unchanged; Ninja -n can now inspect object freshness beyond CMake's glob check.
manifest=e/'inspection.ninja';shutil.copyfile(build/'build.ninja',manifest);assert sha(manifest)==sha(build/'build.ninja')
cmd=['ninja','-C',str(build),'-f',str(manifest),'-d','explain','-n','btxd'];log=e/'object-dirty-reasons.log'
with log.open('wb') as out:code=subprocess.run(cmd,stdout=out,stderr=subprocess.STDOUT,timeout=120).returncode
text=log.read_text(errors='replace');lines=[x for x in text.splitlines() if x.startswith('ninja explain:')];counts=collections.Counter()
for line in lines:
 if 'command line changed' in line:counts['command_line_changed']+=1
 elif 'stored deps info out of date' in line:counts['stored_deps_out_of_date']+=1
 elif 'deps for ' in line and 'missing' in line:counts['missing_deps']+=1
 elif 'most recent input' in line or 'older than' in line:counts['input_newer_than_output']+=1
 elif 'output ' in line and ("doesn't exist" in line or 'does not exist' in line):counts['missing_output']+=1
 else:counts['other']+=1
j={'command':cmd,'exit':code,'diagnostic_manifest_sha256':sha(manifest),'original_manifest_sha256':sha(build/'build.ninja'),'explain_log_sha256':sha(log),'reason_counts':dict(counts),'first_reasons':lines[:40],'planned_steps':re.findall(r'^\[(\d+)/(\d+)\]',text,re.M)[-1:] ,'compiler_invoked':False,'object_timestamps_changed':False,'source_contents_changed':False,'restore':state['checkpoint_restore']}
(e/'dirty-diagnostic.json').write_text(json.dumps(j,indent=2));print(json.dumps(j,indent=2));raise SystemExit(code)
