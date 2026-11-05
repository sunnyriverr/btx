"""Keep cached compiler identity stable; paired metadata-only qualification."""
from pathlib import Path
import os,json,subprocess,hashlib,shutil,re,time
root=Path(os.environ['BTX_NATIVE_ROOT']);build=root/'project-build';e=root/'evidence';P=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def tablehash(x):return hashlib.sha256(json.dumps(x,sort_keys=True,separators=(',',':')).encode()).hexdigest()
state=json.loads((e/'result.json').read_text());baseline=json.loads((P/'path-baseline.json').read_text());assert state['checkpoint_restore']['restored'];assert state['base']==baseline['source']
for key,value in baseline['compilers'].items():
 path=Path(value);assert path.is_absolute() and sha(path)==state['profile']['tools']['clang-cl']['sha256']
def dry(label):
 copy=e/(label+'.ninja');shutil.copyfile(build/'build.ninja',copy);assert sha(copy)==sha(build/'build.ninja');log=e/(label+'.log');cmd=['ninja','-C',str(build),'-f',str(copy),'-d','explain','-n','btxd']
 with log.open('wb') as f:r=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT,timeout=120)
 assert r.returncode==0;text=log.read_text(errors='replace');steps=re.findall(r'^\[(\d+)/(\d+)\]',text,re.M)
 return {'command_changed':text.count('ninja explain: command line changed for '),'stale_deps':text.count('ninja explain: stored deps info out of date'),'steps':int(steps[-1][1]) if steps else 0,'log_sha256':sha(log)}
A=json.loads((build/'compile_commands.json').read_text());before=dry('path-before');assert before['command_changed']>3000
shutil.copyfile(build/'CMakeCache.txt',e/'path-before-CMakeCache.txt');shutil.copyfile(build/'compile_commands.json',e/'path-before-compile_commands.json')
# The preset sets compiler basenames. Final overrides retain the exact detected
# compiler paths, types and file identities from the original compiled project.
args=state['profile']['args']+[f'-D{k}:STRING={v}' for k,v in baseline['compilers'].items()]
os.environ.update(VCPKG_ROOT=str(root/'vcpkg'),VCPKG_DISABLE_METRICS='1',VCPKG_MAX_CONCURRENCY='2',VCPKG_BINARY_SOURCES='clear;files,'+str(root/'binary-cache')+',readwrite')
start=time.monotonic()
with (e/'path-fix-configure.log').open('wb') as f:code=subprocess.run(args,cwd=Path(os.environ['GITHUB_WORKSPACE'])/'btx',stdout=f,stderr=subprocess.STDOUT,timeout=180).returncode
assert code==0
shutil.copyfile(build/'CMakeCache.txt',e/'path-after-CMakeCache.txt');shutil.copyfile(build/'compile_commands.json',e/'path-after-compile_commands.json');B=json.loads((build/'compile_commands.json').read_text());after=dry('path-after')
out={'before':before,'after':after,'configure_args':args,'configure_exit':code,'configure_seconds':round(time.monotonic()-start,2),'configure_log_sha256':sha(e/'path-fix-configure.log'),'commands_count':len(B),'commands_identical_to_original_compiled_project':tablehash(B)==baseline['compile_commands_canonical_sha256'],'command_tables_before_sha256':tablehash(A),'command_tables_after_sha256':tablehash(B),'baseline':baseline,'product_compilation':False,'object_timestamp_edits':False,'ninja_log_edits':False}
(e/'path-fix-result.json').write_text(json.dumps(out,indent=2))
assert out['commands_identical_to_original_compiled_project'];assert after['command_changed']==0 and after['stale_deps']==0;assert after['steps']<150
print(json.dumps(out,indent=2))
