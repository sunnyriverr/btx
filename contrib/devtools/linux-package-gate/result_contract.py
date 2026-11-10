"""Strict classification of individually selected unittest cases."""
import re

def classify(case, phase, code, output, stop=None):
    if stop or code not in (0, 1) or not re.search(r'Ran 1 test(?:\s|$)', output):
        return 'INCOMPLETE'
    if case['method'] not in output or re.search(r'\b(?:skipped|ERROR)\b', output):
        return 'INCOMPLETE'
    if phase == 'baseline' and case.get('failure'):
        return 'EXPECTED_BASELINE_FAILURE' if (code == 1 and 'FAILED (failures=1)' in output
            and 'FAIL: ' + case['method'] in output and case['failure'] in output) else 'INCOMPLETE'
    return 'PASS' if code == 0 and re.search(r'^OK\s*$', output, re.M) else 'INCOMPLETE'
