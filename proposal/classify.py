"""Classify observations, never fixture assumptions, as a product finding."""
def classify(report):
    if not all(report.get(k) is True for k in ('complete','binary_verified','source_verified','origin_verified','clean_cleanup','completion_exact')):
        return 'INCONCLUSIVE'
    cases = report.get('cases', {})
    if set(cases) != {'healthy','recovered_before_stop','fault_through_stop'}:
        return 'INCONCLUSIVE'
    for name, c in cases.items():
        if not all(c.get(k) is True for k in ('persisted_active','partial_verified','origin_still_alive','clean_stop','reopen_ready','pieces_preserved')):
            return 'INCONCLUSIVE'
        if c.get('rpc_error') is not None and c.get('persistence_error') is not True:
            return 'INCONCLUSIVE'
        if name != 'healthy' and not all(c.get(k) is True for k in ('fault_present_at_cancel','probe_is_directory','old_file_preserved_on_cancel')):
            return 'INCONCLUSIVE'
        if name == 'fault_through_stop' and not all(c.get(k) is True for k in ('fault_present_through_stop','old_file_preserved_on_stop','fault_cleared_before_reopen')):
            return 'INCONCLUSIVE'
        if name != 'fault_through_stop':
            if not (c.get('cancelled_live') is True and c.get('saved_job_removed') is True and c.get('resumed') is False and c.get('quiet_window_complete') is True):
                return 'INCONCLUSIVE'
    c = cases['fault_through_stop']
    if c.get('resumed') is True:
        if c.get('new_verified_piece') is not True:
            return 'INCONCLUSIVE'
        if c.get('persistence_error') or c.get('persistence_warning'):
            return 'RESUMED_WITH_DIAGNOSTIC'
        if c.get('cancelled_live') is True and c.get('rpc_error') is None and c.get('persistence_error') is False and c.get('persistence_warning') is False:
            return 'ACKNOWLEDGED_CANCEL_RESUMED_WITHOUT_DIAGNOSTIC'
        return 'INCONCLUSIVE'
    if c.get('resumed') is False and c.get('saved_job_removed') is True and c.get('quiet_window_complete') is True:
        return 'CANCELLATION_RETAINED'
    return 'INCONCLUSIVE'
