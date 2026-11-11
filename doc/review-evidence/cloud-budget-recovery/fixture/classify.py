"""Offline observation contract; PASS requires every safety/progress/recovery gate.
No native observation exists yet. The later runner must supply these observations
from the test, syscall trace and pinned binary, never from expected values.
"""
import json,sys,re
from pathlib import Path
COUNTERS={'day_gets':1,'month_gets':1,'used_gets':1,'day_bytes':6,'month_bytes':6,'used_bytes':6}
def classify(r, identity):
 try:
  assert r['schema']==1 and r['complete'] is True and r['skipped'] is False
  assert r['source_tree']==identity['source_tree'] and r['binary_sha256']==identity['binary_sha256']
  assert r['harness_sha256']==identity['harness_sha256']
  assert r['process_exit']==0 and r['fault_scope_restored'] is True
  assert r['day_before']==r['day_after']==20000 and r['month_before']==r['month_after']
  assert r['seed']['counters']==COUNTERS and r['seed']['valid_json'] is True
  assert r['seed']['payload']=='daycap'
  assert r['clean_rollover_control'] is True
  h=r['healthy_reopen'];assert h['put_ok'] is True and h['get_ok'] is False and 'budget' in h['error']
  f=r['fault'];assert f['no_origin_get'] is True and f['write_failure']=='EFBIG'
  assert (f['path']==r['budget_path'] or re.fullmatch(re.escape(r['budget_path'])+r'\.tmp\.[0-9]+',f['path'])) and f['trace_verified'] is True
  assert f['limit_bytes']>0 and f['limit_bytes']==r['seed']['file_bytes']//2
  a=r['recovered'];assert a['init_ok'] is True and a['put_ok'] is True
  roll=r['rollover'];assert roll['day']==20001 and roll['month']==r['month_before']
  assert roll['put_ok'] is True and roll['first_get_ok'] is True and roll['payload']=='daycap'
  assert roll['second_get_ok'] is False and 'budget' in roll['error']
  assert r['in_memory_control'] is True
 except (AssertionError,KeyError,TypeError):return 'INCOMPLETE'
 safe=(not f['init_ok'] and not f['ready'] and bool(f['error']) and f['committed_bytes_preserved']
       and a['counters_before_get']==COUNTERS and not a['get_ok'] and 'budget' in a['error']
       and roll['counters']=={'day_gets':1,'month_gets':2,'used_gets':2,'day_bytes':6,'month_bytes':12,'used_bytes':12})
 if safe:return 'PASS'
 reproduced=(f['init_ok'] and f['ready'] and not f['committed_bytes_preserved'] and f['invalid_json_after']
             and a['counters_before_get']==dict.fromkeys(COUNTERS,0) and a['get_ok'] and a['payload']=='daycap')
 return 'REPRODUCED' if reproduced else 'FAIL'
if __name__=='__main__':
 try:v=classify(json.loads(Path(sys.argv[1]).read_text()),json.loads(Path(sys.argv[2]).read_text()))
 except Exception:v='INCOMPLETE'
 print(v);raise SystemExit(0 if v=='PASS' else 1 if v in ('REPRODUCED','FAIL') else 2)
