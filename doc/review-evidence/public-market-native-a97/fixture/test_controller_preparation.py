"""Offline controller checks only: mocked subprocesses, no node/RPC/wallet."""
import importlib.util
import json
from pathlib import Path
import signal
import tempfile
import unittest
from unittest.mock import patch, Mock

P = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('prepared_controller', P / 'run_prepared.py')
controller = importlib.util.module_from_spec(spec)
spec.loader.exec_module(controller)


class ControllerPreparation(unittest.TestCase):
    def exercise(self, mode):
        with tempfile.TemporaryDirectory(prefix='.controller-check-', dir=P) as scratch:
            root = Path(scratch)
            proc = Mock(pid=424242, returncode=0)
            proc.poll.side_effect = InterruptedError('injected controller cancellation') if mode == 'interrupt' else None
            proc.poll.return_value = 0
            proc.wait.return_value = 0
            def popen(*args, **kwargs):
                records = Path(kwargs['env']['BTX_PUBLIC_MARKET_RECORDS'])
                records.mkdir(parents=True)
                (records / 'result.json').write_text('{partial' if mode == 'partial' else json.dumps({'status': 'PASS', 'cleanup_errors': []}))
                return proc
            absent = Mock(side_effect=[False, True, True] if mode == 'interrupt' else None, return_value=True)
            def killed(pid, sig):
                self.assertEqual((pid, sig), (424242, signal.SIGKILL))
                proc.returncode = -9
            with patch.object(controller, 'P', root), patch.object(controller.subprocess, 'Popen', side_effect=popen), \
                 patch.object(controller.threading, 'Timer') as timer, patch.object(controller, 'group_absent', absent), \
                 patch.object(controller.os, 'killpg', side_effect=killed) as kill:
                if mode == 'healthy':
                    receipt = controller.execute_case('restart', {}, Path('/not-executed/python'))
                    self.assertEqual(receipt['exit'], 0)
                    kill.assert_not_called()
                else:
                    with self.assertRaises(AssertionError):
                        controller.execute_case('restart', {}, Path('/not-executed/python'))
                    receipt = json.loads(next(root.glob('execution/*/execution-receipt.json')).read_text())
                    if mode == 'interrupt':
                        kill.assert_called_once_with(424242, signal.SIGKILL)
                        self.assertIn('InterruptedError', receipt['error'])
                        self.assertTrue(receipt['process_group_absent'])
                    else:
                        self.assertIn('JSONDecodeError', receipt['native_result_error'])
                timer.return_value.cancel.assert_called_once()
                self.assertEqual(receipt['source'], controller.M['source'])
                return receipt

    def test_healthy_receipt_without_process_execution(self):
        self.exercise('healthy')

    def test_interruption_kills_only_owned_group_and_records_error(self):
        self.exercise('interrupt')

    def test_partial_child_json_preserves_controller_receipt(self):
        self.exercise('partial')


if __name__ == '__main__':
    unittest.main()
