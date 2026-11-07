"""Coupling controls for the selected consumer, using actual native records.

Record mutations below are local unit fault injection, not new node, peer or
converter-mutant executions. Existing adapter and converter campaigns are reused.
"""
import argparse
import ast
import copy
import json
from pathlib import Path
import re
import sys
import unittest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / 'rpc_help_comparison'))
from consumer import consume, parse_conversion_rows
from comparison import Probe, compare


class ConsumerIntegration(unittest.TestCase):
    def setUp(self):
        self.document = copy.deepcopy(NATIVE)
        self.contracts = copy.deepcopy(CONTRACTS)
        self.rows = list(ROWS)

    def findings(self):
        return consume(self.document, self.contracts, self.rows)

    def registration(self, method):
        return next(r for r in self.document['registrations'] if r['method'] == method)

    def conversion(self, method, form, selector, raw):
        return next(r for r in self.document['conversions'] if
                    (r['method'], r['form'], r['selector'], r['raw']) == (method, form, selector, raw))

    def test_current_records_keep_real_failures_and_unknowns(self):
        findings = self.findings()
        # Reuse the already-qualified comparator as the conversion oracle.
        # Do not require a product defect to remain present after it is fixed.
        probes = [Probe(**{k: row[k] for k in Probe.__dataclass_fields__})
                  for row in self.contracts['probes']]
        observations = {(r['method'], r['form'], r['selector'], r['raw']): r['result']
                        for r in self.document['conversions']}
        self.assertTrue(set(compare(probes, observations)).issubset(set(findings)))
        self.assertFalse(any(f.kind in ['invalid_metadata', 'invalid_observation',
                                       'binding_mismatch', 'declaration_mismatch',
                                       'invalid_contract'] for f in findings))
        positive_methods = {r['method'] for r in self.contracts['probes']
                            if r['group'] != 'known_bad_literal'}
        self.assertFalse([f for f in findings if f.binding.split('/')[0] in positive_methods])
        self.assertTrue(any(f.kind == 'unresolved' and f.binding.startswith('getmodelevents/') for f in findings))
        has_stale_row = any(r[0] == 'listmodelidentities' for r in self.rows)
        self.assertEqual(any(f.kind == 'unexpected_conversion' and
                             f.binding.startswith('listmodelidentities/') for f in findings), has_stale_row)

    def test_named_sign_routes_to_options_and_positional_sign_stays_legacy(self):
        legacy = [r for r in self.contracts['probes'] if r['group'] == 'legacy']
        self.assertEqual({r['form']: r['destination'] for r in legacy},
                         {'positional': 'params[1]', 'named': 'params[1].sign'})
        self.assertFalse(any(f.binding.startswith('walletprocesspsbt/') for f in self.findings()))
        next(r for r in legacy if r['form'] == 'named')['destination'] = 'params[1]'
        self.assertTrue(any(f.kind == 'binding_mismatch' and 'named/sign' in f.binding for f in self.findings()))

    def test_boolean_fault_survives_missing_metadata(self):
        record = self.conversion('walletprocesspsbt', 'named', 'adjust_timelocks', 'true')
        record['result'] = {'value': 1, 'type': 4}
        entry = self.registration('walletprocesspsbt')
        entry.update(status='MISSING', arguments=None)
        findings = self.findings()
        self.assertTrue(any(f.kind == 'conversion_mismatch' and 'walletprocesspsbt/' in f.binding for f in findings))
        self.assertTrue(any(f.kind == 'unresolved' and 'walletprocesspsbt/' in f.binding for f in findings))

    def test_object_only_search_cannot_become_general_json_or_string(self):
        for record in self.document['conversions']:
            if record['method'] == 'searchmodels' and record['raw'] == 'true':
                record['result'] = {'value': True, 'type': 5}
        self.rows = [(m, i, n, 'json_or_string' if m == 'searchmodels' else mode)
                     for m, i, n, mode in self.rows]
        findings = self.findings()
        self.assertTrue(any(f.kind == 'conversion_mismatch' and f.binding.startswith('searchmodels/') for f in findings))
        self.assertTrue(any(f.kind == 'conversion_mode_mismatch' and f.binding.startswith('searchmodels/') for f in findings))

    def test_invoked_alias_is_not_replaced_by_its_canonical_name(self):
        self.document['registrations'] = [r for r in self.document['registrations']
                                          if r['method'] != 'importmatmulattestations']
        findings = self.findings()
        self.assertTrue(any(f.kind == 'unresolved' and f.binding.startswith('importmatmulattestations/') for f in findings))
        self.assertFalse(any(f.binding.startswith('submitmatmulattestations/') for f in findings))

    def test_every_handler_slot_is_checked_even_with_same_canonical_name(self):
        entry = copy.deepcopy(self.registration('help'))
        count = sum(r['method'] == 'help' for r in self.document['registrations'])
        entry['handler_index'] = count
        entry['arguments'][0].update(type='BOOL', per_name_types=[])
        self.document['registrations'].append(entry)
        self.assertTrue(any(f.kind == 'declaration_mismatch' and
                            f'/handler[{count}]' in f.binding for f in self.findings()))

    def test_unavailable_metadata_does_not_mean_zero_arguments(self):
        entry = self.registration('listmodelidentities')
        entry.update(status='MISSING', arguments=None)
        findings = self.findings()
        self.assertTrue(any(f.kind == 'unresolved' and f.binding.startswith('listmodelidentities/') for f in findings))
        self.assertFalse(any(f.kind == 'unexpected_conversion' and f.binding.startswith('listmodelidentities/') for f in findings))
        entry['arguments'] = []
        self.assertTrue(any(f.kind == 'invalid_metadata' for f in self.findings()))

    def test_unresolved_handler_slots_remain_separate(self):
        entry = self.registration('getmodelevents')
        entry.update(status='FACTORY_ERROR', arguments=None)
        extra = copy.deepcopy(entry)
        extra['handler_index'] = 1
        self.document['registrations'].append(extra)
        bindings = {f.binding for f in self.findings() if f.kind == 'unresolved' and
                    f.binding.startswith('getmodelevents/')}
        self.assertEqual(bindings, {'getmodelevents/handler[0]', 'getmodelevents/handler[1]'})

    def test_ordinary_nested_fields_are_not_promoted(self):
        entry = self.registration('help')
        child = copy.deepcopy(entry['arguments'][0])
        child.update(names='deep', type='BOOL', optional=False)
        entry['arguments'][0].update(type='OBJ', inner=[child])
        row = copy.deepcopy(self.contracts['probes'][0])
        row.update(method='help', form='named', selector='deep', raw='true',
                   destination='params[0].deep', expected={'value': True, 'type': 5})
        self.contracts['probes'].append(row)
        self.document['conversions'].append({'method': 'help', 'form': 'named', 'selector': 'deep',
                                             'raw': 'true', 'result': {'value': True, 'type': 5}})
        self.rows.append(('help', 0, 'deep', 'json'))
        self.assertTrue(any(f.kind == 'binding_mismatch' and '/named/deep' in f.binding for f in self.findings()))

    def test_runtime_union_types_are_not_restricted_to_the_selected_alias(self):
        row = copy.deepcopy(next(r for r in self.contracts['probes'] if
                                 r['method'] == 'walletprocesspsbt' and r['selector'] == 'options'))
        row.update(raw='false', expected={'value': False, 'type': 5})
        self.contracts['probes'].append(row)
        self.document['conversions'].append({'method': 'walletprocesspsbt', 'form': 'named',
                                             'selector': 'options', 'raw': 'false',
                                             'result': {'value': False, 'type': 5}})
        self.assertFalse(any(f.binding.startswith('walletprocesspsbt/') for f in self.findings()))

    def test_empty_or_uncovered_contract_cannot_pass(self):
        self.contracts.update(probes=[], metadata_rules=[])
        self.assertTrue(any(f.kind == 'invalid_contract' for f in self.findings()))
        self.contracts['selected_methods'] = []
        self.assertTrue(any(f.kind == 'invalid_contract' for f in self.findings()))
        self.contracts = copy.deepcopy(CONTRACTS)
        self.contracts['selected_methods'].append('unexamined_method')
        self.assertTrue(any(f.kind == 'invalid_contract' for f in self.findings()))

    def test_missing_or_malformed_observations_do_not_pass(self):
        self.document['conversions'] = [r for r in self.document['conversions'] if not
                                       (r['method'] == 'help' and r['form'] == 'named')]
        self.assertTrue(any(f.kind == 'unresolved' and f.binding.startswith('help/') for f in self.findings()))
        self.document['conversions'][0]['result'] = {'value': True, 'type': 4}
        self.assertTrue(any(f.kind == 'invalid_observation' for f in self.findings()))

    def test_mode_parser_preserves_the_maintained_row_inventory(self):
        tree = ast.parse(HELP_SOURCE.read_text())
        nodes = [n for n in tree.body if isinstance(n, ast.FunctionDef) and
                 n.name in ['parse_string', 'process_mapping']]
        namespace = {'re': re}
        exec(compile(ast.Module(body=nodes, type_ignores=[]), 'maintained-parser', 'exec'), namespace)
        original = namespace['process_mapping'](CLIENT_SOURCE)
        self.assertEqual([r[:3] for r in ROWS], original)
        for broken in ['', 'static const CRPCConvertParam vRPCConvertParams[] =\n{\n']:
            with self.assertRaises(ValueError):
                parse_conversion_rows(broken)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--records', type=Path, required=True)
    parser.add_argument('--client-source', type=Path, required=True)
    parser.add_argument('--result', type=Path)
    args, remaining = parser.parse_known_args()
    NATIVE = json.loads(args.records.read_text())
    CONTRACTS = json.loads((HERE / 'rpc_help_comparison/contracts.json').read_text())
    CLIENT_SOURCE = args.client_source
    HELP_SOURCE = CLIENT_SOURCE.parents[2] / 'test/functional/rpc_help.py'
    ROWS = parse_conversion_rows(CLIENT_SOURCE.read_text())
    program = unittest.main(argv=[sys.argv[0]] + remaining, exit=False)
    if args.result:
        args.result.write_text(json.dumps({'tests_run': program.result.testsRun,
                                           'failures': len(program.result.failures),
                                           'errors': len(program.result.errors),
                                           'skips': len(program.result.skipped),
                                           'successful': program.result.wasSuccessful()}, indent=2) + '\n')
    raise SystemExit(int(not program.result.wasSuccessful()))
