"""Fail closed on test failures, missing/filtered regressions or wrong suite."""
import xml.etree.ElementTree as ET
from read_suite import normalize
REGRESSION='cancelmodeljob_save_failure_preserves_stop_and_retries'
CONTROLS={'cancelmodeljob_reports_only_a_real_cancel','retrieve_jobs_persist_reload_without_worker','retrieve_jobs_reload_progress_index_not_wrapped','retrieve_jobs_reload_counters_do_not_throw'}
def validate_suite(raw,exit_code,phase):
 normalized,repairs=normalize(raw);root=ET.fromstring(normalized)
 assert root.tag=='testsuite' and int(root.attrib['errors'])==0,'suite framing/errors'
 cases=list(root.iter('testcase'));active=[c for c in cases if c.find('skipped') is None]
 assert active and all(c.attrib.get('classname')=='modelnet_first_run_tests' for c in active),'wrong active suite'
 assert len(active)==int(root.attrib['tests']),'test count mismatch'
 assert len(cases)-len(active)==int(root.attrib['skipped']),'skip count mismatch'
 names={c.attrib['name']for c in active};assert CONTROLS|{REGRESSION}<=names,'required regression/control missing'
 selected=[c for c in cases if c.attrib.get('classname')=='modelnet_first_run_tests']
 assert len(selected)==len(active) and not any(c.find('skipped')is not None for c in selected),'selected suite case skipped'
 assert not list(root.iter('error')),'case error'
 failed={c.attrib['name'] for c in active if c.find('failure')is not None}
 if phase=='baseline':
  assert exit_code!=0 and failed=={REGRESSION} and int(root.attrib['failures'])>0,'baseline failed wrong case or unexpectedly passed'
 else:
  assert phase=='candidate' and exit_code==0 and not failed and int(root.attrib['failures'])==0,'candidate suite failed'
 return {'executed':len(active),'failed_cases':sorted(failed),'failure_count':int(root.attrib['failures']),'filtered':len(cases)-len(active),'cdata_repairs':repairs,'exit_code':exit_code}
