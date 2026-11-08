"""Offline-only replay of saved results. Never imports or executes the native runner."""
import ast
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import unittest

from result_handling import JOURNEY, classify_case, final_result

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
RAW = ROOT / 'run-42430108849'
SAVED = json.loads((RAW / 'result.json').read_text())
OUTPUT = (RAW / 'maintained-transfer.log').read_text()
BEFORE = ast.parse((ROOT / 'ci/run.py').read_text())
AFTER = ast.parse((HERE / 'run.py').read_text())


def clean_record():
    # A local control only: remove the known wrapper exception, not native evidence.
    state = deepcopy(SAVED)
    state.pop('error')
    return state


def runner_finalization(state, output):
    """Execute the corrected runner's actual finalization/save/exit statements only."""
    main = next(node for node in AFTER.body if isinstance(node, ast.Try))
    final = main.finalbody[-2:]
    assert isinstance(final[0], ast.Expr) and ast.unparse(final[0]) == 'state.update(final_result(state, output))'
    assert ast.unparse(final[1]) == 'save()'
    assert isinstance(AFTER.body[-1], ast.Raise)
    captured = []
    scope = {'state': state, 'output': output, 'final_result': final_result,
             'save': lambda: captured.append(deepcopy(state))}
    # No source setup, download, subprocess, cleanup or native case enters this AST.
    code = compile(ast.fix_missing_locations(ast.Module(body=final + [AFTER.body[-1]], type_ignores=[])),
                   str(HERE / 'run.py') + ':offline-finalizer-only', 'exec')
    try:
        exec(code, scope)
    except SystemExit as result:
        return result.code, captured[0]
    raise AssertionError('runner did not return an explicit outcome')


class SavedResultTests(unittest.TestCase):
    def test_original_failure_reproduced_without_native_execution(self):
        main = next(node for node in BEFORE.body if isinstance(node, ast.Try))
        original = [node for node in main.body if isinstance(node, ast.Assign)
                    and isinstance(node.targets[0], ast.Subscript)
                    and ast.unparse(node.targets[0]) in ("state['skipped']", "state['test_pass']", "state['observation_complete']")]
        scope = {'state': clean_record(), 'output': OUTPUT}
        with self.assertRaisesRegex(NameError, 'observed'):
            exec(compile(ast.fix_missing_locations(ast.Module(body=original, type_ignores=[])),
                         'original-bookkeeping-only', 'exec'), scope)
        self.assertFalse(scope['state']['test_pass'])

    def test_saved_native_pass_original_wrapper_failure_preserved(self):
        result = final_result(SAVED, OUTPUT)
        self.assertEqual(result['case_result'], 'PASS')
        self.assertEqual(result['wrapper_result'], 'FAIL')
        self.assertFalse(result['observation_complete'])
        code, record = runner_finalization(deepcopy(SAVED), OUTPUT)
        self.assertEqual(code, 1)
        self.assertEqual(record['error'], SAVED['error'])

    def test_corrected_finalizer_replays_clean_pass(self):
        code, result = runner_finalization(clean_record(), OUTPUT)
        self.assertEqual((code, result['case_result'], result['wrapper_result']), (0, 'PASS', 'PASS'))
        self.assertTrue(result['observation_complete'])
        self.assertTrue(result['test_pass'])
        self.assertFalse(result['skipped'])

    def test_failure_exit_overrides_success_text(self):
        for exit_code in (1, 2, -15):
            with self.subTest(exit_code=exit_code):
                state = clean_record()
                state['framework_exit'] = exit_code
                code, result = runner_finalization(state, OUTPUT)
                self.assertEqual((code, result['case_result']), (1, 'FAIL'))
                self.assertFalse(result['test_pass'])

    def test_failure_text_overrides_zero_exit(self):
        for marker in ('Test failed', 'Traceback (most recent call last):', 'AssertionError: failed'):
            with self.subTest(marker=marker):
                self.assertEqual(classify_case(0, OUTPUT + '\n' + marker), 'FAIL')

    def test_skip_is_explicit_and_never_passes(self):
        for exit_code, output in ((77, OUTPUT), (0, 'Test skipped: multicast unavailable'), (0, 'SKIPPED')):
            with self.subTest(exit_code=exit_code, output=output[:30]):
                state = clean_record()
                state['framework_exit'] = exit_code
                code, result = runner_finalization(state, output)
                self.assertEqual((code, result['case_result'], result['wrapper_result']), (77, 'SKIP', 'SKIP'))
                self.assertTrue(result['skipped'])
                self.assertFalse(result['test_pass'])
                self.assertFalse(result['observation_complete'])

    def test_fail_not_hidden_by_skip_marker(self):
        self.assertEqual(classify_case(1, 'Test skipped\nTest failed'), 'FAIL')
        self.assertEqual(classify_case(77, 'AssertionError: failed'), 'FAIL')

    def test_missing_or_malformed_exit_is_incomplete(self):
        for value in (None, True, '0'):
            with self.subTest(value=value):
                self.assertEqual(classify_case(value, OUTPUT), 'INCOMPLETE')
        self.assertEqual(classify_case(0, None), 'INCOMPLETE')
        state = clean_record()
        state.pop('framework_exit')
        code, result = runner_finalization(state, OUTPUT)
        self.assertEqual((code, result['case_result']), (1, 'INCOMPLETE'))

    def test_truncated_or_out_of_order_evidence_is_incomplete(self):
        journey_line = next(line for line in OUTPUT.splitlines() if line.endswith(JOURNEY))
        completion_line = next(line for line in OUTPUT.splitlines() if line.endswith('Tests successful'))
        for output in ('', journey_line, completion_line, completion_line + '\n' + journey_line,
                       OUTPUT.replace('Tests successful', 'Test successful'), OUTPUT.replace(JOURNEY, 'PASS: shortened')):
            with self.subTest(output=output[:30]):
                code, result = runner_finalization(clean_record(), output)
                self.assertEqual((code, result['case_result']), (1, 'INCOMPLETE'))
                self.assertFalse(result['observation_complete'])

    def test_ansi_format_does_not_reject_saved_pass(self):
        self.assertEqual(classify_case(0, '\x1b[32m' + OUTPUT + '\x1b[0m'), 'PASS')

    def test_source_and_package_failures_block_wrapper(self):
        for field, value in (('source_before', {}), ('source_after', {}), ('package_files_unchanged', False)):
            with self.subTest(field=field):
                state = clean_record()
                state[field] = value
                code, result = runner_finalization(state, OUTPUT)
                self.assertEqual((code, result['case_result'], result['wrapper_result']), (1, 'PASS', 'FAIL'))
                self.assertFalse(result['integrity_ok'])
                self.assertFalse(result['observation_complete'])

    def test_unclean_runtime_blocks_wrapper_even_after_native_pass(self):
        for field, value in (('cleanup_before', [{'pid': 1}]), ('cleanup_remaining', [{'pid': 1}]),
                             ('cleanup_signals', [{'pid': 1}]), ('runtime_removed', False)):
            with self.subTest(field=field):
                state = clean_record()
                state[field] = value
                code, result = runner_finalization(state, OUTPUT)
                self.assertEqual((code, result['wrapper_result']), (1, 'FAIL'))
                self.assertFalse(result['cleanup_ok'])

    def test_skip_does_not_hide_wrapper_error(self):
        state = deepcopy(SAVED)
        state['framework_exit'] = 77
        code, result = runner_finalization(state, 'Test skipped')
        self.assertEqual((code, result['case_result'], result['wrapper_result']), (1, 'SKIP', 'FAIL'))

    def test_stale_pass_flags_do_not_override_missing_completion(self):
        state = clean_record()
        state.update(test_pass=True, observation_complete=True, wrapper_result='PASS')
        code, result = runner_finalization(state, '')
        self.assertEqual(code, 1)
        self.assertFalse(result['test_pass'])
        self.assertFalse(result['observation_complete'])

    def test_driver_wiring_source_pin_and_syntax(self):
        source = (HERE / 'run.py').read_text()
        compile(source, str(HERE / 'run.py'), 'exec')
        self.assertNotIn('observed[', source)
        imports = [ast.unparse(node) for node in AFTER.body if isinstance(node, ast.ImportFrom)]
        self.assertIn('from result_handling import final_result', imports)
        self.assertIn("'source_mapping': 'Published replacement mapped to source 2f3b574867c11ab79eba829123689b76e6137a38", source)
        self.assertNotIn('0ac06fd2', source)
        # The runner's native command/profile and its source/package assertions remain identical.
        def command_node(tree):
            return next(node for node in ast.walk(tree) if isinstance(node, ast.Assign)
                        and ast.unparse(node.targets[0]) == 'output'
                        and isinstance(node.value, ast.Call) and ast.unparse(node.value.func) == 'command')
        self.assertEqual(ast.dump(command_node(BEFORE)), ast.dump(command_node(AFTER)))
        self.assertEqual([ast.dump(n) for n in ast.walk(BEFORE) if isinstance(n, ast.Assert) and n is not BEFORE.body[-1]],
                         [ast.dump(n) for n in ast.walk(AFTER) if isinstance(n, ast.Assert)])

    def test_all_original_evidence_bytes_unchanged(self):
        hashes = json.loads((HERE / 'original-evidence-hashes.json').read_text())
        self.assertEqual(len(hashes), 17)
        for name, expected in hashes.items():
            with self.subTest(path=name):
                self.assertEqual(hashlib.sha256((ROOT / name).read_bytes()).hexdigest(), expected)


if __name__ == '__main__':
    unittest.main(verbosity=2)
