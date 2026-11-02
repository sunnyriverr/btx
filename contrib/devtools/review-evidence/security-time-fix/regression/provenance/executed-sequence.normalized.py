# Fixed final sequence: every selected case runs once; no result-driven retries.
from pathlib import Path
import subprocess,time,json,hashlib,os
r=Path('<RECORDED_WORK_ROOT>');probe=r/'build/security-probe'
binaries={v:r/'build'/('time-'+v) for v in ['baseline','candidate','combined']}
(r/'tested-identities.json').write_text(json.dumps({str(p.relative_to(r)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [*binaries.values(),probe,r/'build/CMakeFiles/harness.dir/harness/security_tests.cpp.o']},indent=2))
cases=[('controlled','time-fix-ordered-valid-work'),('rollback','time-fix-rollback-contract'),('challenge-expiry','time-fix-held-challenge-expiry'),('pause','time-fix-held-pause'),('revoke','time-fix-held-worker-revocation'),('local-deny','time-fix-held-local-permission'),('record-expiry','time-fix-held-record-expiry')]
requests=[(v,m,t) for v in ['baseline','candidate'] for m,t in cases]+[('combined','natural','scheduler-valid-work-and-two-per-tick')]
rows=[]
for variant,mode,test in requests:
 out=r/'results'/variant/mode;out.mkdir(parents=True,exist_ok=True,mode=0o700);out.chmod(0o700)
 env=dict(os.environ,BTX_DIAG_MODE=mode,BTX_DIAG_SNAPSHOT=str(out/'snapshot.json'))
 start=time.monotonic();timeout=False
 with (out/'run.log').open('w') as log:
  try:p=subprocess.run([str(binaries[variant]),str(probe),str(out/'summary.json'),test],stdout=log,stderr=subprocess.STDOUT,env=env,timeout=25);code=p.returncode
  except subprocess.TimeoutExpired:timeout=True;code='timeout'
 summary=json.loads((out/'summary.json').read_text()) if (out/'summary.json').exists() else {}
 events=[json.loads(line[5:]) for line in (out/'run.log').read_text().splitlines() if line.startswith('DIAG ')]
 errors=[e for e in events if e.get('stage','').startswith('worker-error')]
 row={'variant':variant,'mode':mode,'test':test,'exit':code,'timeout':timeout,'seconds':time.monotonic()-start,'passed':summary.get('passed'),'failed':summary.get('failed'),'tests':summary.get('tests'),'worker_errors':errors,'prestop_snapshot':(out/'snapshot.json.prestop.json').exists(),'postjoin_snapshot':(out/'snapshot.json').exists()};rows.append(row)
 print(json.dumps({'variant':variant,'mode':mode,'exit':code,'passed':row['passed'],'failed':row['failed'],'errors':[e.get('error') for e in errors],'tests':row['tests']}),flush=True)
(r/'final-sequence.json').write_text(json.dumps(rows,indent=2))
