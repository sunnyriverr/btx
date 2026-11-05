from pathlib import Path
import os,json,subprocess,shutil
root=Path(os.environ['BTX_NATIVE_ROOT']);build=root/'project-build';e=root/'evidence'
with (e/'ninja-explain-dry-run.log').open('wb') as f:code=subprocess.run(['ninja','-C',str(build),'-d','explain','-n','btxd'],stdout=f,stderr=subprocess.STDOUT,timeout=120).returncode
j=json.loads((build/'btx-checkpoint.json').read_text());sample={}
for name,info in j['files'].items():
 p=root/name
 if len(sample)<15 and (name.endswith('.obj') or name.endswith('.ninja_deps') or name.endswith('.ninja_log')):sample[name]={'mtime_ns':p.stat().st_mtime_ns,'bytes':p.stat().st_size}
for f in ['.ninja_log','.ninja_deps']:
 p=build/f
 if p.exists() and p.stat().st_size<50*1024**2:shutil.copyfile(p,e/('checkpoint-'+f.removeprefix('.')))
(e/'checkpoint-debug.json').write_text(json.dumps({'exit':code,'sample':sample,'cwd':str(build)},indent=2))
raise SystemExit(code)
