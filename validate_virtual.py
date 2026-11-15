"""Strict baseline observation contract, NOT a claim the product is fixed."""
import json
C=8<<20;B=C*10000
# ok, parts, begins, aborts, completes, direct, consumed, sent bytes
EXPECTED={
 'known_over':(False,10000,1,1,0,0,B,B),
 'known_exact':(True,10000,1,0,1,0,B,B),
 'unknown_exact':(False,10000,1,1,0,0,B,B),
 'unknown_over':(False,10000,1,1,0,0,B,B),
 'normal_two_parts':(True,2,1,0,1,0,2*C,2*C),
 'short_read':(False,1,1,1,0,0,C,C),
 'backend_failure':(False,2,1,1,0,0,2*C,2*C),
 'normal_direct':(True,0,0,0,0,1,1024,1024),
}
def validate(rows):
 assert len(rows)==len(EXPECTED)
 names=[r['case'] for r in rows];assert len(set(names))==len(names) and set(names)==set(EXPECTED)
 for r in rows:
  assert r['branch']=='live-adapted' and r['fake'] is False
  assert type(r['ok']) is bool
  assert tuple(r[k] for k in ('ok','parts','begins','aborts','completes','direct','consumed','bytes'))==EXPECTED[r['case']],r
  assert r['max_buffer']==(1024 if r['case']=='normal_direct' else C)
  if r['case'] in ('known_over','unknown_exact','unknown_over'):assert r['error']=='s3 https too many multipart parts'
  elif r['ok']:assert r['error']==''
  else:assert r['error']
 return True
if __name__=='__main__':
 import sys
 validate([json.loads(line) for line in open(sys.argv[1])]);print('EXPECTED_BASELINE_OBSERVATIONS_VERIFIED (not repaired)')
