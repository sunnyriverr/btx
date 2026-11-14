"""Ensure supplemental tests detect three specific broken implementations.

Edits exist in memory only. Expected test failures demonstrate test sensitivity,
not failures of the unchanged candidate.
"""
import contextlib
import importlib.util
import io
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('contracts', HERE / 'release_signer_recovery_test.py')
contracts = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = contracts
spec.loader.exec_module(contracts)


def changed_module(name, filename, old, new):
    path = contracts.SOURCE / 'scripts/release' / filename
    source = path.read_text()
    if source.count(old) != 1:
        raise AssertionError('Control source anchor changed')
    module = types.ModuleType(name)
    module.__file__ = str(path)
    sys.modules[name] = module
    exec(compile(source.replace(old, new), str(path), 'exec'), module.__dict__)
    return module


class BrokenControlTest(unittest.TestCase):
    def check_detected(self, fixture, module, test):
        with patch.object(fixture, 'load_module', return_value=module), \
                contextlib.redirect_stdout(io.StringIO()):
            result = unittest.TestResult()
            test.run(result)
        self.assertEqual(result.testsRun, 1)
        self.assertEqual(len(result.errors), 0, 'must fail the intended assertion, not fixture setup')
        self.assertEqual(len(result.failures), 1)

    def test_wrong_signer_guard_removal_is_detected(self):
        module = changed_module('mutant_pin', 'publish_github_release.py',
                                'if expected not in fingerprints:', 'if False:')
        self.check_detected(contracts.publisher_fixture, module,
            contracts.SignerValidationTest('test_public_dry_run_accepts_primary_pin_rejects_different_signer'))

    def test_keyboard_interrupt_cleanup_removal_is_detected(self):
        module = changed_module('mutant_cleanup', 'sign_release_bundle.py',
                                'except BaseException:', 'except Exception:')
        self.check_detected(contracts.signer_fixture, module,
            contracts.SigningRecoveryTest('test_verify_interruption_restores_then_retries'))

    def test_publishing_before_draft_staging_is_detected(self):
        module = changed_module('mutant_draft', 'publish_github_release.py',
                                'staging_payload["draft"] = True', 'staging_payload["draft"] = False')
        self.check_detected(contracts.publisher_fixture, module,
            contracts.PublishingRecoveryTest('test_upload_interrupt_leaves_draft_then_retry_completes'))


if __name__ == '__main__':
    unittest.main()
