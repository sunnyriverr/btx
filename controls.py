"""Run terminal cleanup and quota controls against the exact qualified pair."""
import json
from pathlib import Path
import subprocess
import tempfile

from helpers import Helper, digest
from native_fixture import CAP, make_model, ports

BINARIES = {
    'combined-baseline': '644a661727a85332871ba3a09f4c0ea00e0f5a8f5b7eeeeb35ff28fdd8ec1b42',
    'candidate': '5ee324e1595fbebdd2d2f008a680fd212de38404819b92640f856acfe0cee98a',
}
OUT = Path('repair-records').resolve()


def insufficient(binary, output):
    output.mkdir()
    with tempfile.TemporaryDirectory(prefix='btx-quota-control-') as d:
        root = Path(d)
        model = root / 'model.safetensors'
        make_model(model)
        limit = 64 << 20
        assert model.stat().st_size > limit
        endpoint, _ = ports()
        source = Helper(binary, root/'a', output, 'source', CAP, hostport=endpoint)
        receiver = Helper(binary, root/'receiver', output, 'receiver', limit, peer=f'127.0.0.1:{endpoint}')
        try:
            source.start()
            receiver.start()
            imported = source.ok('importmodel', [str(model), {'pin': True}])
            assert imported['seeded']
            job, _ = receiver.request(imported['uri'])
            obs = receiver.settled(job, 20)
            assert obs['status'] == 'failed' and 'disk quota' in str(obs)
            assert not receiver.pieces(imported['artifact_id'])
            assert not receiver.row(imported['model_id'])
        finally:
            for h in (receiver, source):
                h.cleanup()
            assert all(not h.forced and not h.cleanup_error for h in (receiver, source))
        (output/'result.json').write_text(json.dumps({'cap': limit, 'model_bytes': model.stat().st_size,
                                  'job': obs, 'pieces_absent': True, 'clean_cleanup': True}, indent=2)+'\n')


OUT.mkdir()
for label, expected in BINARIES.items():
    binary = Path('saved-bin', label).resolve()
    assert digest(binary) == expected
    binary.chmod(0o755)
    result_dir = OUT / (label + '-cancel')
    subprocess.run(['python3', '-u', 'native_fixture.py', '--binary', str(binary),
                    '--expected-sha256', expected, '--output', str(result_dir),
                    '--permanent-control'], check=True, timeout=130)
    obs = json.loads((result_dir/'observations.json').read_text())
    assert obs['result'] == 'PERMANENT_CONTROL_PASS' and obs['removed_after_cancel']
    insufficient(binary, OUT/(label+'-insufficient'))
(OUT/'qualification.json').write_text(json.dumps({'pass': True, 'binary_sha256': BINARIES}, indent=2)+'\n')
