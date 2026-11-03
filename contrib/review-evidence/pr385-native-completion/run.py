from pathlib import Path
import argparse,hashlib,json,subprocess,time
p=argparse.ArgumentParser();p.add_argument('--work',required=True,type=Path);a=p.parse_args();work=a.work.resolve();package=Path(__file__).resolve().parent
m=json.loads((package/'manifest.json').read_text());sha=lambda f:hashlib.sha256(f.read_bytes()).hexdigest()
expected_names=['mesh-native-completion-direct-worker-and-denials','mesh-native-completion-scan-and-restart'];rows=[]
for variant in ['baseline','candidate']:
 out=work/('result-'+variant);out.mkdir(mode=0o700);start=time.monotonic()
 with (out/'run.log').open('w') as log:r=subprocess.run([str(work/'build'/variant),str(work/'build/security-probe'),str(out/'summary.json'),'mesh-native-completion-'],stdout=log,stderr=subprocess.STDOUT,timeout=45)
 j=json.loads((out/'summary.json').read_text());e=m['expected'][variant]
 names=[v['name'] for v in j['tests']];statuses=[v['status'] for v in j['tests']]
 checks={'exact_selected_names':names==expected_names,'exact_count':len(names)==2,'passed':j['passed']==e['passed'],'failed':j['failed']==e['failed'],'endpoint_count':len(j['completion_evidence'])==e['endpoints'],'exit':r.returncode==(1 if variant=='baseline' else 0),'statuses':statuses==(['PASS','FAIL'] if variant=='baseline' else ['PASS','PASS'])}
 if variant=='baseline':checks['failure_signature']=j['tests'][1].get('error')==e['scan_failure']
 else:
  wrap=j['scan_evidence'];checks['wrap_boundary']=len(wrap)==1 and wrap[0]['lower_work']<wrap[0]['cursor_before']
 row={'variant':variant,'exit':r.returncode,'seconds':time.monotonic()-start,'checks':checks,'tests':j['tests'],'endpoint_count':len(j['completion_evidence'])};rows.append(row);print(json.dumps(row),flush=True)
(work/'results.json').write_text(json.dumps(rows,indent=2)+'\n')
ident={str(f.relative_to(work)):sha(f) for f in work.rglob('*') if f.is_file() and ('CMakeFiles/harness.dir/security_tests.cpp.o' in str(f) or f.name in ['baseline','candidate','security-probe','security_tests.cpp'])};(work/'tested-identities.json').write_text(json.dumps(ident,indent=2)+'\n')
if not all(all(r['checks'].values()) for r in rows):raise SystemExit('ACCEPTANCE FAIL; inspect preserved results before any rerun')
print('ACCEPTANCE PASS')
