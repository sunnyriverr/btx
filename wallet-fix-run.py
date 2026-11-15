"""Bounded, hash-pinned normal-runner qualification; public summaries only."""
from pathlib import Path
import csv,hashlib,json,os,re,shutil,signal,subprocess,sys,time
root=Path.cwd();records=root/'records';inputs=json.loads((records/'candidate-inputs.json').read_text());producer=json.loads((records/'build-result.json').read_text());assert producer['status']=='BUILD_PASS'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def exists(pid):
 try:os.killpg(pid,0);return True
 except ProcessLookupError:return False
def stop(p):
 assert p.pid!=os.getpgrp()
 for sig,seconds in [(signal.SIGTERM,10),(signal.SIGKILL,5)]:
  if not exists(p.pid):break
  os.killpg(p.pid,sig);end=time.monotonic()+seconds
  while exists(p.pid) and time.monotonic()<end:p.poll();time.sleep(.1)
 p.wait(timeout=5);return not exists(p.pid)
def size(path):return sum(p.stat().st_size for p in path.rglob('*') if p.is_file() and not p.is_symlink())
fixture=root/'source/test/functional/wallet_seed_pruned_recovery.py'
results={}
for case in ['repaired']:
 private=root/('suite-private-'+case);assert not private.exists();private.mkdir(mode=0o700)
 binpath=root/'build/bin'
 hashes=producer['binary_sha256']
 for n,h in hashes.items():assert sha(binpath/n)==h
 for n,h in inputs['files_sha256'].items():assert sha(root/'source'/n)==h
 env=dict(os.environ,BTXD=str(binpath/'btxd'),BITCOIND=str(binpath/'btxd'),BTXCLI=str(binpath/'btx-cli'),BITCOINCLI=str(binpath/'btx-cli'),BTX_TEST_WALLET_RECOVERY_RECORDS=str(private/'events.json'),PYTHONPATH=str(root/'source/test/functional'),XDG_RUNTIME_DIR=str(private/'rt'))
 (private/'rt').mkdir();env.pop('BITCOIN_TESTS_LOGGING',None)
 cmd=[sys.executable,str(root/'source/test/functional/test_runner.py'),'wallet_seed_pruned_recovery.py','wallet_importbundle_shielded.py','--configfile='+str(root/'build/test/config.ini'),'-j1','--tmpdirprefix='+str(private),'--resultsfile='+str(private/'results.csv'),'--nocleanup']
 started=time.monotonic();p=None;reason=None;peak=0
 receipt={'case':case,'binary_sha256':hashes,'suite_inputs':inputs['files_sha256'],'normal_runner':True,'budget_s':1800,'scratch_limit_bytes':512*2**20}
 try:
  with (private/'private.log').open('w') as log:
   p=subprocess.Popen(cmd,env=env,cwd=root,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
   while p.poll() is None:
    peak=max(peak,size(private))
    if time.monotonic()-started>1800:reason='DEADLINE'
    elif peak>512*2**20:reason='SCRATCH_LIMIT'
    elif shutil.disk_usage(root).free<1.25*2**30:reason='DISK_RESERVE'
    if reason:break
    time.sleep(2)
  clean=stop(p);raw=(private/'private.log').read_text(errors='replace')
  frames=[{'file':f.replace(str(root),'WORKSPACE'),'line':int(n),'function':fn} for f,n,fn in re.findall(r'File "([^"\n]+)", line (\d+), in ([^\n]+)',raw)]
  observations=json.loads((private/'events.json').read_text()) if (private/'events.json').exists() else {'status':'NO_RESULT'}
  rows=list(csv.DictReader((private/'results.csv').open())) if (private/'results.csv').exists() else []
  stages=[e['stage'] for e in observations.get('events',[])]
  wanted={'wallet_seed_pruned_recovery.py --descriptors','wallet_importbundle_shielded.py --descriptors','ALL'}
  csv_pass=len(rows)==3 and {x['test'] for x in rows}==wanted and all(x['status']=='Passed' for x in rows)
  passed=csv_pass and not reason and clean and p.returncode==0 and observations.get('status')=='PASS' and stages==['HEALTHY_CONTROL','PRUNE_ADMITTED','INCOMPLETE_RECOVERY','DURABLE_DATABASE','CONFIRMED_CONTINUED_USE']
  receipt.update(exit=p.returncode,stop_reason=reason,cleanup_group_absent=clean,observations=observations,results_csv=rows,source_frames=frames[-20:],exception_classes=re.findall(r'(?m)^([A-Za-z_]\w*(?:Error|Exception))(?=:|$)',raw)[-5:],result='PASS' if passed else 'UNEXPECTED_FAILURE',seed_guard_message_observed='this wallet already has shielded keys or notes; importing a bundle would replace its PQ seed' in raw,rpc_minus4_observed='(-4)' in raw)
 finally:
  if p is not None and exists(p.pid):receipt['cleanup_group_absent']=stop(p)
  if receipt.get('cleanup_group_absent',p is None):shutil.rmtree(private)
  receipt.update(elapsed_s=round(time.monotonic()-started,2),maximum_sampled_private_bytes=peak,private_data_removed=not private.exists(),raw_logs_uploaded=False)
  (records/(case+'-suite-result.json')).write_text(json.dumps(receipt,indent=2)+'\n');results[case]=receipt
  print(json.dumps({'case':case,'result':receipt.get('result'),'elapsed_s':receipt['elapsed_s'],'private_data_removed':receipt['private_data_removed']}),flush=True)
status='PASS' if results.get('repaired',{}).get('result')=='PASS' else 'FAIL'
(records/'suite-summary.json').write_text(json.dumps({'status':status,'source':inputs['source'],'cases':{k:v.get('result') for k,v in results.items()},'current_base_negative_reused':'43769085141, same recovery fixture hash','only_two_registered_tests_selected':True},indent=2)+'\n')
raise SystemExit(0 if status=='PASS' else 1)
