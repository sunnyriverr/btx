from pathlib import Path
import ast,hashlib,json,subprocess,sys
P=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
m=json.loads((P/'PACKAGE-MANIFEST.json').read_text())
for name,row in m['files'].items():assert sha(P/name)==row['sha256'] and (P/name).stat().st_size==row['bytes'],name
s=json.loads((P/'source-manifest.json').read_text())
assert sha(P/'baseline.cpp')==s['baseline_sha256'] and sha(P/'candidate.cpp')==s['candidate_sha256']
r=json.loads((P/'native/compiler/pair.json').read_text());st={x['label']:x for x in r['stages']}
a,b=st['capability-runtime-before'],st['capability-runtime-after']
assert a['exit']==1 and b['exit']==0 and a['command']==b['command']==r['generated_command']['command']
assert a['cwd']==b['cwd'] and r['candidate_source_delta']==['src/modelnet/capability_runtime.cpp']
assert r['generated_headers_and_build_metadata_unchanged'] and r['source_restored'] and not r['project_cache_saved']
for label in ['capability-runtime-before','capability-runtime-after','capability-runtime-target-plan']:
    assert sha(P/'native/compiler'/(label+'.log'))==st[label]['log_sha256']
for compiler in ['clang-cl','cl']:
    d=P/'native'/compiler;rec=json.loads((d/'receipt.json').read_text())
    assert rec['status']=='PASS' and rec['build_exit']==0 and rec['run_exit']==0 and rec['runtime_sha256']==s['candidate_sha256']
    for name,h in rec['logs'].items():assert sha(d/name)==h
    assert (d/'run.log').read_text().splitlines()[-1]=='checks=37 failures=0'
for variant in ['baseline','candidate']:
    d=P/'mac'/variant;rec=json.loads((d/'receipt.json').read_text());assert rec['status']=='PASS' and rec['run_exit']==0
    # Published Mac records have personal paths redacted; logs themselves are empty
    # or path-free, and their original hashes must still match.
    for name,h in rec['logs'].items():assert sha(d/name)==h
    assert (d/'run.log').read_text().splitlines()[-1]=='checks=29 failures=0'
assert (P/'mac/baseline/run.log').read_bytes()==(P/'mac/candidate/run.log').read_bytes()
inputs=json.loads((P/'component-inputs.json').read_text())
for name,h in inputs['controls'].items():assert sha(P/name)==h
for name in ['component.py','component-only.py']:ast.parse((P/name).read_text())
if len(sys.argv)>1:
    source=Path(sys.argv[1]).resolve();assert sha(source/'src/modelnet/capability_runtime.cpp')==s['candidate_sha256']
    assert subprocess.check_output(['git','-C',str(source),'rev-parse','HEAD'],text=True).strip()==s['code']
    subprocess.run(['git','-C',str(source),'diff','--exit-code','HEAD'],check=True,capture_output=True)
print('PASS: packaged source, command/control logs and hashes verified; no compiler or platform test executed')
