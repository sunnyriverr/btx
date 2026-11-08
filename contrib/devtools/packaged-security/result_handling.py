"""Pure result classification, shared by the corrected runner and offline replay."""
import re

def classify_case(exit_code, output):
    if type(exit_code) is not int or not isinstance(output, str):
        return 'INCOMPLETE'
    text = re.sub(r'\x1b\[[0-9;]*m', '', output)
    if exit_code not in (0, 77) or re.search(r'Test failed|Traceback \(most recent call last\)|AssertionError', text):
        return 'FAIL'
    if exit_code == 77 or re.search(r'\b(?:Test skipped|SKIPPED)\b', text, re.I):
        return 'SKIP'
    lines = text.splitlines()
    if any(line.endswith('TestFramework (INFO): Tests successful') for line in lines):
        return 'PASS'
    return 'INCOMPLETE'


def final_result(state, output):
    """Do not conflate a native-case verdict with wrapper/integrity failure."""
    case = classify_case(state.get('framework_exit'), output)
    integrity = (bool(state.get('source_before'))
                 and state.get('source_before') == state.get('source_after')
                 and state.get('package_files_unchanged') is True)
    cleanup = (state.get('cleanup_before') == [] and state.get('cleanup_remaining') == []
               and state.get('cleanup_signals') == [] and state.get('runtime_removed') is True)
    sound = integrity and cleanup and not state.get('error')
    accepted = case == 'PASS' and sound
    wrapper = case if sound and case in ('PASS', 'SKIP') else 'FAIL'
    return {'case_result': case, 'test_pass': case == 'PASS', 'skipped': case == 'SKIP',
            'integrity_ok': integrity, 'cleanup_ok': cleanup,
            'wrapper_result': wrapper, 'observation_complete': accepted}
