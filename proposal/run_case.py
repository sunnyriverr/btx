"""Run one unchanged script with documented shared profile/progress observers."""
import json
import os
from pathlib import Path
import runpy
import sys
import time

root = Path.cwd()
sys.path.insert(0, str(root / 'source/test/functional'))
label = os.environ['CASE_LABEL']
proposal = root / 'proposal'
manifest = json.loads((proposal / 'manifest.json').read_text())
module = runpy.run_path(str(proposal / (label + '-wallet_create_tx.py')), run_name='wallet_create_tx_fixture')
case = module['CreateTxWalletTest']
original_params = case.set_test_params

def shared_params(self):
    original_params(self)
    assert self.num_nodes == 1
    current = list((getattr(self, 'extra_args', None) or [[]])[0])
    keys = {arg.split('=', 1)[0] for arg in manifest['shared_args']}
    self.extra_args = [[arg for arg in current if arg.split('=', 1)[0] not in keys] + manifest['shared_args']]

case.set_test_params = shared_params
progress = []
progress_file = root / 'records' / (label + '-methods.json')
progress_file.write_text('[]\n')

def observe(name, method):
    def wrapper(self, *args, **kwargs):
        start = time.monotonic()
        row = {'method': name, 'status': 'started'}
        progress.append(row)
        progress_file.write_text(json.dumps(progress, indent=2))
        try:
            result = method(self, *args, **kwargs)
            row['status'] = 'passed'
            return result
        except BaseException as error:
            row['status'] = 'failed'
            row['error_type'] = type(error).__name__
            # The fixture uses ordinary disposable wallet calls only; no secret-returning methods.
            row['error'] = getattr(error, 'error', str(error))
            raise
        finally:
            row['elapsed_s'] = round(time.monotonic() - start, 3)
            progress_file.write_text(json.dumps(progress, default=str, indent=2))
    return wrapper

for name in manifest['methods']:
    setattr(case, name, observe(name, getattr(case, name)))
# Normal framework parser/setup/main/cleanup; no product RPC is substituted.
case(__file__).main()
