"""Same immutable unit case, ordinary versus short mapped temporary path."""
from pathlib import Path
import json, os, subprocess, sys
import checkpoint
import integration_support as s
from batch_results import classify
from job_tree import ProcessTree

P = Path(__file__).resolve().parent
M = json.loads((P / 'completion-manifest.json').read_text())
s.STATE = s.E / 'maintained.json'
s.R = json.loads(s.STATE.read_text())
R = s.R
tree = ProcessTree()
assert R['status'] == 'RESTORED_VERIFIED' and not s.owned_processes()
exe = s.BUILD / 'bin/test_btx.exe'
assert checkpoint.digest(exe) == M['binary_sha256']
data = Path('D:/bc' + os.environ['GITHUB_RUN_ID'])
assert not data.exists() and not Path('S:/').exists()
data.mkdir(); (data / 'tmp').mkdir(); (data / 'short').mkdir()
R.update(unit_data=str(data), batch_results=[], status='PATH_CONTROL_RUNNING')
os.environ['TMP'] = os.environ['TEMP'] = str(data / 'tmp')
selector = 'modelnet_b0_disc_store_tests/store_05_disk_exhaustion_preserves'
mapped = False
try:
    s.need('map-short-root', ['subst', 'S:', str(data / 'short')], 15)
    mapped = True
    for label, root in [('path-ordinary', data / 'suite-0053'), ('path-short', Path('S:/s'))]:
        report = s.E / (label + '.xml')
        code = s.run(label, [str(exe), '--run_test=' + selector, '--log_level=test_suite',
                     '--report_level=detailed', '--report_format=XML', '--report_sink=' + str(report),
                     '--catch_system_errors=yes', '--', '-testdatadir=' + str(root)], 30)
        outcome = classify([selector], (s.E / (label + '.log')).read_text(errors='replace'),
                           report.read_text() if report.exists() else '', code)
        outcome.update(label=label, data_root=str(root), job_active_processes=tree.active())
        R['batch_results'].append(outcome); s.save()
        assert tree.active() == 1 and not s.owned_processes()
    R['status'] = 'PATH_CONTROL_RECORDED'
finally:
    if mapped:
        s.need('unmap-short-root', ['subst', 'S:', '/D'], 15)
    R['short_drive_removed'] = not Path('S:/').exists()
    s.save()
assert R['short_drive_removed'] and checkpoint.digest(exe) == M['binary_sha256']
print(json.dumps(R['batch_results'], indent=2))
assert [x['state'] for x in R['batch_results']] == ['failed', 'passed'], 'Path-only explanation not confirmed'
