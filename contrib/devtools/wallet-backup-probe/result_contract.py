"""Classification, not a regression assertion that assumes the bug exists."""
def classify(s):
    gates=('funded','current_control','plain_restore_control','restored_locked','unlock_succeeded','phase_complete')
    if s.get('error') or s.get('skipped') or not all(s.get(x) is True for x in gates): return 'INCOMPLETE'
    expected=s.get('expected_outpoints')
    if not expected or len(expected)!=2 or len(set(expected))!=2:return 'INCOMPLETE'
    if s.get('after_restore_outpoints')==expected:return 'RECOVERED_AT_RESTORE'
    if s.get('after_unlock_outpoints')==expected:return 'RECOVERED_AT_UNLOCK'
    if s.get('far_ismine_after_unlock') is not True:return 'OUTSIDE_DERIVED_RANGE'
    if s.get('after_unlock_outpoints') is None or not set(s['after_unlock_outpoints']).issubset(expected):return 'INCOMPLETE'
    if (s.get('manual_scan_complete') is True and s.get('after_manual_outpoints')==expected
            and s.get('manual_balance_matches') is True and s.get('same_tip') is True):return 'UNLOCK_VISIBILITY_GAP_CONFIRMED'
    return 'INCOMPLETE'
