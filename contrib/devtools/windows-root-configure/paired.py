"""Single cached generated target before/after; never configures or saves cache."""
from pathlib import Path
import os,sys,json,hashlib,subprocess,time,shutil,re
P=Path(__file__).resolve().parent
root=Path(os.environ['BTX_NATIVE_ROOT']);build=root/'project-build';e=root/'evidence'
source=Path(os.environ['GITHUB_WORKSPACE'])/'btx'
unit=source/'src/modelnet/capability_runtime.cpp'
target='src/modelnet/CMakeFiles/bitcoin_modelnet.dir/capability_runtime.cpp.obj'
obj=build/target;manifest=e/'verified-resume.ninja'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
config=json.loads((P/'repair-inputs.json').read_text())
resume=json.loads((e/'verified-resume-result.json').read_text())
assert resume['source']==config['source'] and resume['all_commands_identical_to_original']
assert resume['command_changed_objects']==0 and resume['stale_deps']==0
assert not obj.exists(), 'Baseline cache unexpectedly already contains failed target'
assert sha(unit)==config['baseline_sha256'] and sha(P/'candidate.cpp')==config['candidate_sha256']
for name,digest in config['controls'].items(): assert sha(P/name)==digest, name
catalog=json.loads((e/'before-source.json').read_text())
original=unit.read_bytes();st=unit.stat()
commands=json.loads((build/'compile_commands.json').read_text())
row=[r for r in commands if r['file'].replace('\\','/').endswith('/src/modelnet/capability_runtime.cpp')]
assert len(row)==1
(e/'capability-runtime-generated-command.json').write_text(json.dumps(row[0],indent=2))
result={'source':config['source'],'inputs':config,'target':target,'generated_command':row[0],
        'same_invocation_before_after':True,'cmake_reconfigured':False,'cache_saved':False,
        'compile_commands_sha256':sha(build/'compile_commands.json'),'stages':[]}
invocation=['ninja','-C',str(build),'-f',str(manifest),'-j','1',target]
def run(label,command,timeout=180):
    log=e/(label+'.log');t=time.monotonic()
    with log.open('wb') as f: rc=subprocess.run(command,stdout=f,stderr=subprocess.STDOUT,timeout=timeout).returncode
    r={'label':label,'command':command,'exit':rc,'seconds':round(time.monotonic()-t,3),'log_sha256':sha(log)}
    result['stages'].append(r)
    (e/'capability-runtime-pair.json').write_text(json.dumps(result,indent=2))
    return rc,log.read_text(errors='replace')
def changed_source():
    return [name for name,info in catalog['files'].items() if info['git_mode']!='120000' and sha(source/name)!=info['working_sha256']]
try:
    assert changed_source()==[]
    rc,text=run('capability-runtime-target-plan',invocation[:-1]+['-n',target])
    steps=re.findall(r'^\[(\d+)/(\d+)\]',text,re.M)
    assert rc==0 and steps and all(b=='1' for a,b in steps), text
    rc,text=run('capability-runtime-before',invocation)
    assert rc!=0 and all(s in text for s in ['pid_t','popen','pclose','STDOUT_FILENO'])
    assert not obj.exists()
    unit.write_bytes((P/'candidate.cpp').read_bytes())
    assert changed_source()==['src/modelnet/capability_runtime.cpp']
    result['candidate_source_delta']=['src/modelnet/capability_runtime.cpp']
    rc,text=run('capability-runtime-after',invocation)
    assert rc==0 and obj.is_file()
    result['candidate_object_sha256']=sha(obj)
    result['candidate_warnings']=[s for s in text.splitlines() if 'warning:' in s.lower()]
    # Supported CPU lifecycle/refusal controls use actual runtime, smoke, types,
    # digest and JSON implementation. Only lease randomness is a test fixture.
    for compiler in ['clang-cl','cl']:
        out=e/('runtime-component-'+compiler)
        rc,text=run('runtime-component-'+compiler,[sys.executable,str(P/'component.py'),str(source),str(out),'candidate',compiler],240)
        assert rc==0
        receipt=json.loads((out/'receipt.json').read_text());assert receipt['status']=='PASS'
        # Keep logs/receipts, not hosted executable/object files.
        for f in out.iterdir():
            if f.suffix.lower() in ['.obj','.exe','.pdb','.ilk']: f.unlink()
    result['status']='PASS'
finally:
    unit.write_bytes(original);os.utime(unit,ns=(st.st_atime_ns,st.st_mtime_ns))
    if obj.exists():obj.unlink()
    result['source_restored']=changed_source()==[]
    result['baseline_target_absent_restored']=not obj.exists()
    result['project_cache_saved']=False
    result['local_ninja_logs_may_contain_candidate']='Hosted scratch only; original immutable cache not overwritten'
    (e/'capability-runtime-pair.json').write_text(json.dumps(result,indent=2))
    assert result['source_restored'] and result['baseline_target_absent_restored']
print(json.dumps(result,indent=2))
