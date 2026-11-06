import configparser
import importlib.util
import json
import logging
import subprocess
import sys
import tempfile
import types
from pathlib import Path

sys.dont_write_bytecode = True
logging.getLogger('quiet').addHandler(logging.NullHandler())
logging.getLogger('quiet').propagate = False
ROOT = Path(__file__).resolve().parent
BASE = ROOT.parents[1]
sys.path.insert(0, str(BASE / 'source/test/functional'))
from test_framework.authproxy import JSONRPCException


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def observe(module):
    cls = module.HelpRpcTest
    names = ['test_client_conversion_table', 'test_argument_names', 'test_categories', 'dump_help', 'wallet_help']
    result = []
    for wallet, broken in [(True, []), (False, [])] + [(True, [x]) for x in names] + [(True, names[:2])]:
        obj = object.__new__(cls)
        obj.is_wallet_compiled = lambda: wallet
        obj.log = logging.getLogger('quiet')
        seen = []
        for name in names:
            def call(name=name):
                seen.append(name)
                if name in broken:
                    raise AssertionError('injected ' + name)
            setattr(obj, name, call)
        error = None
        try:
            obj.run_test()
        except AssertionError as e:
            error = str(e)
        expected = names if wallet else names[:-1]
        ok = seen == expected and bool(error) == bool(broken)
        if broken:
            ok = ok and all(x in error for x in broken)
        result.append(dict(wallet=wallet, injected=broken, visited=seen, error=error, acceptance=ok))
    return result


baseline = load('baseline', BASE / 'baseline/rpc_help.py')
candidate = load('candidate', ROOT / 'source/test/functional/rpc_help.py')
results = {'baseline': observe(baseline), 'candidate': observe(candidate), 'controls': []}


def check(name, fn, raises=False):
    error = None
    try:
        fn()
    except AssertionError as e:
        error = str(e)
    assert (error is not None) == raises, (name, error)
    results['controls'].append({'name': name, 'pass': True, 'expected_failure_observed': raises, 'error': error})


class Node:
    def __init__(self, titles, signature=True):
        self.titles = titles
        self.signature = signature
    def help(self, *args):
        if len(args) > 1:
            raise JSONRPCException({'code': -1, 'message': 'help'})
        if args == (0,):
            raise JSONRPCException({'code': -3, 'message': 'JSON value of type number is not of expected type string'})
        if args == ('foo',):
            return 'help: unknown command: foo'
        if args == ('getnewaddress',):
            return 'getnewaddress ( "label" "address_type" )' if self.signature else 'wrong signature'
        if args == ('dump_all_command_conversions',):
            return [['searchmodels', 0, 'query', True], ['resolveresource', 0, 'query', False]]
        if not args:
            return '\n'.join('== ' + name + ' ==\ngetblockcount' for name in sorted(self.titles))
        return 'getblockcount help'


def instance(modelnet, titles):
    obj = object.__new__(candidate.HelpRpcTest)
    obj.config = configparser.ConfigParser()
    obj.config.read_dict({'components': {'ENABLE_MODELNET': str(modelnet)}, 'environment': {'SRCDIR': str(ROOT / 'fixture')}})
    obj.is_wallet_compiled = lambda: True
    obj.is_external_signer_compiled = lambda: False
    obj.is_zmq_compiled = lambda: False
    obj.nodes = [Node(titles)]
    return obj


titles = ['Blockchain', 'Control', 'Mining', 'Network', 'Rawtransactions', 'Stats', 'Util', 'Bridge', 'Shielded', 'Wallet']
for on in [True, False]:
    obj = instance(on, titles + (['Modelnet'] if on else []))
    check('exact categories Modelnet=' + str(on), obj.test_categories)
    obj.nodes[0].titles = titles + ([] if on else ['Modelnet'])
    check('wrong categories rejected Modelnet=' + str(on), obj.test_categories, raises=True)
obj = instance(True, titles + ['Modelnet'])
check('argument-name mismatch retained', obj.test_argument_names, raises=True)
client = ROOT / 'fixture/src/rpc/client.cpp'
client.parent.mkdir(parents=True, exist_ok=True)
client.write_bytes(subprocess.check_output(['git', '-C', str(BASE.parents[2] / 'btx-contributions'), 'show', '666673a3:src/rpc/client.cpp']))
check('client/server mismatch retained', obj.test_client_conversion_table, raises=True)
restarts = []
obj.restart_node = lambda index, extra_args: restarts.append((index, extra_args))
check('wallet help across restart', obj.wallet_help)
assert restarts == [(0, ['-nowallet=1'])]
obj.restart_node = lambda index, extra_args: setattr(obj.nodes[0], 'signature', False)
check('wallet signature regression after restart rejected', obj.wallet_help, raises=True)
with tempfile.TemporaryDirectory(dir=ROOT) as tmp:
    obj.options = types.SimpleNamespace(tmpdir=tmp)
    check('real help-dump method writes help', obj.dump_help)
    assert (Path(tmp) / 'rpc_help_dump/getblockcount').read_text() == 'getblockcount help'
for missing in ['Bridge', 'Shielded']:
    obj = instance(True, [x for x in titles + ['Modelnet'] if x != missing])
    check('missing wallet category rejected: ' + missing, obj.test_categories, raises=True)
for modelnet in [True, False]:
    obj = instance(modelnet, [x for x in titles if x not in ['Bridge', 'Shielded', 'Wallet']] + (['Modelnet'] if modelnet else []))
    obj.is_wallet_compiled = lambda: False
    check('walletOFF categories Modelnet=' + str(modelnet), obj.test_categories)
# Do not aggregate interpreter interruption into an ordinary check failure.
obj = instance(True, titles + ['Modelnet'])
obj.log = logging.getLogger('quiet')
def interrupt():
    raise KeyboardInterrupt
obj.test_client_conversion_table = interrupt
try:
    obj.run_test()
except KeyboardInterrupt:
    results['controls'].append({'name': 'KeyboardInterrupt propagates', 'pass': True})
else:
    raise AssertionError('KeyboardInterrupt hidden')
assert all(x['acceptance'] for x in results['candidate'])
assert not any(x['acceptance'] for x in results['baseline'])
(ROOT / 'verification.json').write_text(json.dumps(results, indent=2))
print('Same orchestration oracle: baseline 0/8, candidate 8/8. Actual check controls:', len(results['controls']))
