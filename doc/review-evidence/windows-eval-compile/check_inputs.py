from pathlib import Path
import ast,hashlib,json
P=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
m=json.loads((P/'PACKAGE-MANIFEST.json').read_text())
for name,row in m['files'].items():assert sha(P/name)==row['sha256'] and (P/name).stat().st_size==row['bytes'],name
source=json.loads((P/'source-manifest.json').read_text())
assert sha(P/'baseline.cpp')==source['baseline_sha256'] and sha(P/'candidate.cpp')==source['candidate_sha256']
b=json.loads((P/'branch-receipt.json').read_text());assert b['base']==source['base'] and b['candidate_sha256']==source['candidate_sha256']
r=json.loads((P/'native/result.json').read_text());assert r['status']=='PAIRED_EVAL_COMPILER_AND_STATE_CONTROLS_PASS' and r['source_restored'] and r['compile_database_unchanged']
commands={x['label']:x for x in r['commands']}
for name,row in commands.items():assert sha(P/'native'/(name+'.log'))==row['log_sha256'],name
assert commands['baseline-eval-object']['exit']!=0 and commands['candidate-eval-object']['exit']==0 and commands['baseline-eval-object']['command']==commands['candidate-eval-object']['command']
for variant in ['candidate-cl','candidate-clang-cl','mutant-clang-cl']:
 d=P/'native'/variant;c=json.loads((d/'receipt.json').read_text());assert c['build_exit']==0 and c['scratch_empty'] and c['parent_environment_unchanged']
 for name,h in c['logs'].items():assert sha(d/name)==h
 text=(d/'run.log').read_text();failed=[x for x in text.splitlines() if x.startswith('FAIL ')]
 assert failed==(['FAIL Windows caller-shaped job terminal FAILED'] if variant.startswith('mutant') else [])
 assert c['run_exit']==(1 if variant.startswith('mutant') else 0)
for variant in ['baseline','candidate']:
 d=P/'mac'/variant;c=json.loads((d/'receipt.json').read_text());assert c['status']=='PASS' and c['run_exit']==0
 assert 'RESULT checks=24 failures=0' in (d/'run.log').read_text()
for name in ['runner.py','component.py']:ast.parse((P/name).read_text())
print('PASS: packaged source, command/control logs and manifest verified; no compiler or platform test executed')
