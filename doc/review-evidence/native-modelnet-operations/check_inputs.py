"""Check retained source/fixture identities; does not build or execute BTX."""
from pathlib import Path
import json,hashlib,ast
P=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
m=json.loads((P/'source-manifest.json').read_text())
for path,row in m['files'].items():
    for variant in ['baseline','candidate']:
        data=(P/row[variant]['input']).read_bytes()
        assert sha(P/row[variant]['input'])==row[variant]['sha256']
        assert hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()==row[variant]['git_blob']
for name in ['runner.py','fixtures/generate.py','fixtures/build.py','fixtures/run.py','fixtures/native.py']:
    ast.parse((P/name).read_text())
assert (P/'candidate-helper.cpp').read_text().count('CloseWorkerDescriptors();')==4
assert 'CloseWorkerDescriptors();' not in (P/'candidate-helper-standalone.cpp').read_text()
fixtures=json.loads((P/'fixtures/input-manifest.json').read_text())
for variant in ['baseline','candidate']:
    file=P/'fixtures'/(variant+'-controls.cpp')
    build=json.loads((P/'mac'/('mac-'+variant+'-build')/'build.json').read_text())
    assert sha(file)==build['source_sha256']
    result=json.loads((P/'mac'/('mac-'+variant)/'results.json').read_text())
    assert result['pass'] and result['temporary_root_removed'] and result['parent_environment_unchanged']
native=json.loads((P/'native/result.json').read_text())
assert native['same_generated_targets_pass'] and native['compile_database_unchanged']
assert native['status']=='BLOCKED_INTEGRATION' and not native['unit_test_execution']
for command in native['commands']:
    assert sha(P/'native'/(command['label']+'.log'))==command['log_sha256']
print('Retained inputs, Python syntax, three-target result and command hashes verified; no build/tests executed')
