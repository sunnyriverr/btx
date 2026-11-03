#!/usr/bin/env python3
"""Local YAML/Actions and unchanged guard checks; requires PyYAML + actionlint."""
import argparse, difflib, hashlib, json, pathlib, subprocess, tempfile
import yaml
p = pathlib.Path(__file__).resolve().parent
parser = argparse.ArgumentParser()
parser.add_argument('--actionlint', default=str(p/'tools/actionlint'))
args = parser.parse_args()
results = {}
before = (p/'before.yml').read_text()
after = (p/'after.yml').read_text()
try:
    yaml.load(before, Loader=yaml.BaseLoader)
except yaml.YAMLError as e:
    results['before_yaml'] = {'failed_as_expected': True, 'error': str(e)}
else:
    raise AssertionError('Baseline unexpectedly parses')
original_line = next(x for x in before.splitlines() if 'Native qualification blocked:' in x)
command = original_line.split('run: ', 1)[1]
quoted_reference = before.replace(original_line, '        run: ' + json.dumps(command+'\n'))
assert yaml.load(quoted_reference, Loader=yaml.BaseLoader) == yaml.load(after, Loader=yaml.BaseLoader)
parsed = yaml.load(after, Loader=yaml.BaseLoader)
assert parsed['jobs']['native']['steps'][1]['run'] == command+'\n'
assert after == before.replace(original_line, '        run: |\n          '+command)
results['after_yaml'] = {'passed': True, 'semantic_equivalence': 'Full object equals original with only offending scalar quoted; command plus block trailing newline'}
for name, expected in [('before', 1), ('after', 0)]:
    r = subprocess.run([args.actionlint, '-no-color', '-shellcheck=', '-pyflakes=', str(p/(name+'.yml'))], capture_output=True, text=True)
    (p/(name+'-actionlint.log')).write_text(r.stdout+r.stderr)
    assert r.returncode == expected, (name, r.returncode, r.stdout, r.stderr)
    results[name+'_actionlint'] = {'exit': r.returncode, 'log': name+'-actionlint.log'}
r = subprocess.run(['bash', '-n'], input=command, capture_output=True, text=True)
assert r.returncode == 0
results['guard_syntax'] = 'bash -n PASS'
with tempfile.TemporaryDirectory(prefix='atlas-workflow-guard-') as tmp:
    root = pathlib.Path(tmp)
    for present, expected in [(False, 1), (True, 0)]:
        if present:
            (root/'gui/atlas').mkdir(parents=True)
            (root/'gui/atlas/Cargo.lock').touch()
        runs = []
        for label, cmd in [('original', command), ('candidate', parsed['jobs']['native']['steps'][1]['run'])]:
            r = subprocess.run(['bash', '-e', '-o', 'pipefail', '-c', cmd], cwd=root, capture_output=True, text=True)
            assert r.returncode == expected
            assert r.stdout == ('' if present else 'Native qualification blocked: resolve, audit and commit Cargo.lock first\n')
            assert r.stderr == ''
            runs.append({'variant': label, 'exit': r.returncode, 'stdout': r.stdout})
        assert runs[0]['stdout'] == runs[1]['stdout']
        results['guard_'+('present' if present else 'absent')] = runs
results['identities'] = {f: hashlib.sha256((p/f).read_bytes()).hexdigest() for f in ['before.yml', 'after.yml', 'validate.py']}
(p/'validation.json').write_text(json.dumps(results, indent=2)+'\n')
print(json.dumps(results, indent=2))
