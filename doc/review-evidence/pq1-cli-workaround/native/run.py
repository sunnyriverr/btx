from pathlib import Path
import subprocess,json,hashlib,tempfile,os,shutil
p=Path(__file__).resolve().parent;binary=p/'pq1-test';clean={k:v for k,v in os.environ.items() if k not in ['BTX_OPENSSL','OPENSSL_CONF','OPENSSL_MODULES','OPENSSL_ENGINES','OPENSSL_CONF_INCLUDE']};result={'binary_sha256':hashlib.sha256(binary.read_bytes()).hexdigest(),'platform':'macOS arm64 component adapter','cases':[]}
result['libraries']=subprocess.check_output(['otool','-L',str(binary)],text=True)
for label,cli in [('old-cli','/usr/bin/openssl'),('compatible-cli','/opt/homebrew/opt/openssl@3/bin/openssl'),('invalid-cli','/nonexistent-pq1-openssl'),('default-selection',None)]:
 root=Path(tempfile.mkdtemp(prefix='pq1-prerequisite-'));env=dict(clean,PQ1_TEST_ROOT=str(root))
 if cli:env['BTX_OPENSSL']=cli
 args=[str(binary),'--run_test=pq1_handshake_mlkem768' if label in ['old-cli','invalid-cli'] else '--run_test=pq1_handshake_mlkem768,pq1_rejects_hybrid_peer','--log_level=all','--report_level=detailed']
 try:
  run=subprocess.run(args,env=env,capture_output=True,text=True,timeout=30);output=run.stdout+run.stderr;(p/(label+'.log')).write_text(output)
  expected=run.returncode!=0 and 'openssl mldsa44 cert failed' in output if label in ['old-cli','invalid-cli'] else run.returncode==0 and 'PQ1 group=MLKEM768' in output and 'TLS_AES_256_GCM_SHA384' in output
  result['cases'].append({'label':label,'override':cli,'exit':run.returncode,'expected_signature':expected,'args':args,'version':subprocess.check_output([cli,'version'],text=True).strip() if cli and Path(cli).exists() else None})
 finally:shutil.rmtree(root)
result['runtime_removed']=True;result['all_expected']=all(x['expected_signature'] for x in result['cases']);(p/'result.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2));raise SystemExit(0 if result['all_expected'] else 1)
