"""Restore checks have completed; preserve baseline and install exact PR774 files."""
from pathlib import Path
import hashlib
import json
import shutil
import subprocess

root = Path.cwd()
records = root / 'records'
proposal = root / 'proposal'
manifest = json.loads((proposal / 'manifest.json').read_text())
producer = json.loads((root / 'saved/producer.json').read_text())
assert producer['source_identity'] == manifest['base']
assert shutil.disk_usage(root).free >= 15 * 2**30
baseline = root / 'baseline/bin'
assert not baseline.exists()
baseline.mkdir(parents=True)
for name, expected in producer['binary_sha256'].items():
    path = root / 'build/bin' / name
    assert hashlib.sha256(path.read_bytes()).hexdigest() == expected
    shutil.copy2(path, baseline / name)
    assert hashlib.sha256((baseline / name).read_bytes()).hexdigest() == expected
# The retained executable has $ORIGIN/../lib RUNPATH. Its saved closure
# resolves on the host; require that again before relocating the baseline.
verification = json.loads((records / 'verification-result.json').read_text())
assert not (root / 'baseline/lib').exists()
for dep in verification['ELF_dependencies'].values():
    for provider in dep['resolved'].values():
        host = Path(provider).resolve()
        assert str(host).startswith(('/usr/lib/', '/lib/')), host
        expected = verification['ELF_dependencies'][str(host)]['sha256']
        assert hashlib.sha256(host.read_bytes()).hexdigest() == expected
# Header changes must flow through ordinary dependency handling.
for entry in manifest['changes']:
    path = proposal / 'candidate-source' / entry['path']
    assert hashlib.sha256(path.read_bytes()).hexdigest() == entry['sha256']
    shutil.copyfile(path, root / 'source' / entry['path'])
fixture = proposal / 'wallet_p2mr_aps_payment.py'
assert hashlib.sha256(fixture.read_bytes()).hexdigest() == manifest['fixture_sha256']
destination = root / 'source/test/functional' / fixture.name
assert not destination.exists()
shutil.copyfile(fixture, destination)
# Retained compiler version must match the active runner; fail rather than
# silently mixing objects from different compiler versions.
compiler_records = list((root / 'build/CMakeFiles').glob('*/CMakeCXXCompiler.cmake'))
assert len(compiler_records) == 1
import re
saved = re.search(r'set\(CMAKE_CXX_COMPILER_VERSION "([^"]+)"\)', compiler_records[0].read_text()).group(1)
active = subprocess.check_output(['c++', '-dumpfullversion'], text=True).strip()
assert active == saved, (active, saved)
plan = subprocess.check_output(['ninja', '-C', 'build', '-n', 'btxd'], text=True, timeout=120)
(records / 'candidate-dry-run.log').write_text(plan)
(records / 'preparation.json').write_text(json.dumps({
    'base': manifest['base'], 'candidate': manifest['candidate'],
    'compiler': active, 'baseline_hashes': producer['binary_sha256'],
    'changes': manifest['changes'], 'fixture_sha256': manifest['fixture_sha256'],
    'build_target': 'btxd', 'baseline_preserved': True,
}, indent=2))
print(plan)
