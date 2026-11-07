"""Observe unchanged maintained help checks; reuse the earlier help-only fixture."""
from pathlib import Path
import functools
import importlib.util
import json
import os
import sys
import time

W = Path(os.environ['GITHUB_WORKSPACE'])
P = W / 'product'
O = W / 'release-rpc-results'
sys.path.insert(0, str(P / 'test/functional'))
spec = importlib.util.spec_from_file_location('release_help', P / 'test/functional/rpc_help.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
cls = m.HelpRpcTest
params = cls.set_test_params
def help_only(self):
    params(self)
    self.setup_clean_chain = True
    self.extra_args = [[]]
    self.bind_to_localhost_only = True
cls.set_test_params = help_only
original_add_nodes = cls.add_nodes
POLICY = ['-modelnet=0', '-connect=0', '-dnsseed=0', '-discover=0']
def scoped_nodes(self, *args, **kwargs):
    result = original_add_nodes(self, *args, **kwargs)
    for node in self.nodes:
        node.args.extend(POLICY)
        assert node.has_explicit_bind
    return result
cls.add_nodes = scoped_nodes
def live_policy(node):
    args = Path('/proc/' + str(node.process.pid) + '/cmdline').read_bytes().decode().split('\0')
    result = {name: [a for a in args if a.startswith(name + '=')][-1]
              for name in ['-modelnet', '-connect', '-dnsseed', '-discover']}
    assert all(result[p.split('=')[0]] == p for p in POLICY)
    assert node.getblockcount() == 0 and node.getconnectioncount() == 0
    return result
events = []
for name in ['test_client_conversion_table', 'test_argument_names', 'test_categories', 'dump_help', 'wallet_help']:
    original = getattr(cls, name)
    @functools.wraps(original)
    def observe(self, original=original, name=name):
        event = {'name': name, 'start': time.time()}
        events.append(event)
        try:
            event['live_policy_before'] = live_policy(self.nodes[0])
            if name == 'test_client_conversion_table':
                (O / 'server-map.json').write_text(json.dumps(self.nodes[0].help('dump_all_command_conversions')))
            result = original(self)
            event['live_policy_after'] = live_policy(self.nodes[0])
            event['result'] = 'pass'
            return result
        except Exception as error:
            event.update(result='fail', error=str(error))
            raise
        finally:
            event['end'] = time.time()
            (O / 'stages.json').write_text(json.dumps(events, indent=2))
    setattr(cls, name, observe)
cls(str(P / 'test/functional/rpc_help.py')).main()
