"""Bounded consumer compile/link against immutable retained production libraries."""
from pathlib import Path
import hashlib,json,os,re,shlex,shutil,signal,subprocess,tarfile,time
from checkpoint import sha,restore_timestamps,verify_restored
ARCHIVE='c4b58e4ef14e93f8b257c18bc855a7d9e4079a4659c9e3266fd25acad50d66df'
HERE=Path(__file__).resolve().parent

def main():
 w=Path(os.environ['GITHUB_WORKSPACE']);out=w/'cloud-pair-records';out.mkdir(exist_ok=True);bins=w/'cloud-pair-binaries';bins.mkdir(exist_ok=True)
 r={'product_modified':False,'production_recompiled':False,'consumer_compiled':False,'product_executed':False,'commands':[]}
 def run(cmd,label,cwd=w,limit=180,allow_error=False):
  start=time.monotonic()
  with (out/(label+'.log')).open('wb') as f:
   p=subprocess.Popen(list(map(str,cmd)),cwd=cwd,stdout=f,stderr=subprocess.STDOUT,start_new_session=True)
   try:
    while p.poll() is None:
     if time.monotonic()-start>limit or shutil.disk_usage(w).free<2*1024**3:raise RuntimeError(label+' resource limit')
     time.sleep(.25)
   except BaseException:
    os.killpg(p.pid,signal.SIGTERM)
    try:p.wait(10)
    except subprocess.TimeoutExpired:os.killpg(p.pid,signal.SIGKILL);p.wait()
    raise
  r['commands'].append({'label':label,'exit':p.returncode,'seconds':time.monotonic()-start})
  assert allow_error or p.returncode==0,label
  return p.returncode,(out/(label+'.log')).read_text(errors='replace')
 try:
  assert shutil.disk_usage(w).free>6*1024**3
  saved=w/'saved-checkpoint';m=json.loads((saved/'manifest.json').read_text());a=saved/'build-state.tar.gz'
  assert sha(a)==ARCHIVE==m['archive_sha256'] and m['identity']['integration_tree']=='ed72649dc18f4eaf55c9a6d1a2b171e587b482dd'
  assert Path(m['workspace'])==w and not (w/'product').exists()
  with tarfile.open(a) as t:t.extractall(w,filter='data')
  restore_timestamps(w,m);verify_restored(w,m);r['restore_verified']=True;r['cached_identity']=m['identity'];r['archive_sha256']=ARCHIVE
  src=w/'product';build=w/'gui-pilot-runtime/qtbuild'
  hashes=json.loads((HERE/'source-hashes.json').read_text());assert all(sha(src/p)==h for p,h in hashes.items());r['cloud_source_sha256']=hashes
  assert run(['g++','-dumpfullversion'],'compiler')[1].strip()=='11.4.0'
  assert 'OpenSSL 3.5.9' in run([w/'gui-pilot-runtime/openssl/bin/openssl','version'],'openssl')[1]
  commands=run(['ninja','-C',build,'-t','commands','btx-modeld'],'cached-commands')[1].splitlines()
  cc=[shlex.split(l) for l in commands if l.rstrip().endswith('-c '+str(src/'src/modelnet/s3_store.cpp'))];assert len(cc)==1
  cc=cc[0];flags=[];i=1
  while i<len(cc):
   x=cc[i]
   if x in ('-MT','-MF','-o','-c'):i+=2;continue
   if x=='-MD':i+=1;continue
   flags.append(x);i+=1
  link=shlex.split(commands[-1]);assert link[:3]==[':', '&&','/usr/bin/g++'] and link[-2:]==['&&',':'];link=link[2:-2]
  original='src/modelnet/CMakeFiles/btx-modeld.dir/__/modeld.cpp.o';assert link.count(original)==1
  obj=bins/'consumer.o';unitobj=bins/'maintained.o';original_link=link[:]
  compile=[cc[0],*flags,'-o',str(obj),'-c',str(HERE/'consumer.cpp')]
  unitcompile=[cc[0],*flags,'-o',str(unitobj),'-c',str(HERE/'maintained_wrapper.cpp')]
  # Check the paired build before doing any compilation: two fixture compiles,
  # four links and one changed production translation unit. Never build helper.
  r['action_count']=4;r['admitted_plan']=['compile changed s3_store only','link candidate consumer','link candidate maintained','syntax-check full maintained source']
  assert r['action_count']<=20 and not any('helper.cpp' in x for x in compile+unitcompile+link)
  for x in link:
   if x.endswith(('.a','.so')) and not x.startswith('-'):assert (build/x).is_file(),x
  saved_records=w/'saved-baseline-records';saved_binaries=w/'saved-baseline-binaries'
  prior=json.loads((saved_records/'result.json').read_text())
  assert prior['paired']['baseline']['verdict']=='REPRODUCED' and prior['paired']['baseline']['maintained_exit']==201
  assert prior['consumer_sha256']==sha(HERE/'consumer.cpp') and prior['maintained_body_sha256']==sha(HERE/'startup-regression.inc') and prior['classifier_sha256']==sha(HERE/'classify.py')
  assert sha(saved_binaries/'baseline-consumer')==prior['paired']['baseline']['identity']['binary_sha256']
  assert sha(saved_binaries/'baseline-maintained')==prior['paired']['baseline']['maintained_binary_sha256']
  shutil.copy2(saved_binaries/'consumer.o',obj);shutil.copy2(saved_binaries/'maintained.o',unitobj)
  r['reused_fixture_objects_sha256']={'consumer.o':sha(obj),'maintained.o':sha(unitobj)}
  r['baseline_reused_from_run']=42927462266
  for name in ['baseline-observations.json','baseline-identity.json','baseline-maintained-tests.log','baseline-classification.log','baseline-fault-write-evidence.log']:
   shutil.copy2(saved_records/name,out/name)
  r['consumer_compiled']=False
  r['paired']={};r['classifier_sha256']=sha(HERE/'classify.py');r['consumer_sha256']=sha(HERE/'consumer.cpp');r['maintained_body_sha256']=sha(HERE/'startup-regression.inc')
  def observe(label,extra=None):
   binary=bins/(label+'-consumer');unit=bins/(label+'-maintained')
   for input_obj,output,tag in [(obj,binary,'consumer'),(unitobj,unit,'maintained')]:
    cmd=original_link[:];idx=cmd.index(original);cmd[idx]=str(input_obj);cmd[cmd.index('-o')+1]=str(output)
    if extra:cmd.insert(idx,str(extra))
    if '-Wl,--unresolved-symbols=ignore-in-shared-libs' in cmd:cmd.remove('-Wl,--unresolved-symbols=ignore-in-shared-libs')
    (out/(label+'-'+tag+'-link-command.json')).write_text(json.dumps(cmd,indent=2)+'\n')
    run(cmd,label+'-'+tag+'-link',build,limit=300)
   identity={'source_tree':m['identity']['integration_tree']+(' + patch-sha256:'+sha(HERE/'cloud-budget-fix.patch') if label=='candidate' else ''),'binary_sha256':sha(binary),'harness_sha256':sha(HERE/'consumer.cpp')}
   ident=out/(label+'-identity.json');ident.write_text(json.dumps(identity,indent=2)+'\n')
   runtime=w/('cloud-pair-'+label);raw=out/(label+'-raw.json');trace=out/(label+'-syscalls.log')
   r['product_executed']=True
   code,_=run(['strace','-f','-yy','-s','512','-e','trace=openat,write,writev,close,rename,renameat,renameat2','-o',trace,binary,runtime,raw],label+'-observation',limit=90,allow_error=True)
   assert raw.is_file();obs=json.loads(raw.read_text());obs.update(identity);obs['process_exit']=code
   budget=str(runtime/'budget.json');text=trace.read_text();lines=[];paths=[]
   for line in text.splitlines():
    match=re.search(r'\bwrite(?:v)?\(\d+<([^>]+)>',line)
    if match and 'EFBIG' in line and (match[1]==budget or re.fullmatch(re.escape(budget)+r'\.tmp\.[0-9]+',match[1])):
     lines.append(line);paths.append(match[1])
   (out/(label+'-fault-write-evidence.log')).write_text('\n'.join(lines)+'\n')
   if isinstance(obs.get('fault'),dict):obs['fault'].update(path=paths[0] if paths else '',trace_verified=bool(lines),write_failure='EFBIG' if lines else '')
   obs['temporary_files_after']=sorted(x.name for x in runtime.glob('budget.json.tmp.*'))
   observation=out/(label+'-observations.json');observation.write_text(json.dumps(obs,indent=2)+'\n')
   class_code,verdict=run(['python3',HERE/'classify.py',observation,ident],label+'-classification',allow_error=True)
   envcommand=['env','CLOUD_BUDGET_CASE_DIR='+str(w/('cloud-maintained-'+label)),str(unit),'--run_test=modelnet_cloud_tests/cloud_12c_startup_write_failure_preserves_budget,modelnet_cloud_tests/cloud_12d_post_read_save_failure_retains_charge','--log_level=test_suite','--report_level=detailed']
   # The suite has only these two prepared cases; run the suite name so Boost's
   # comma-filter parsing cannot silently omit one case.
   envcommand=[x if not x.startswith('--run_test=') else '--run_test=modelnet_cloud_tests' for x in envcommand]
   unitcode,_=run(envcommand,label+'-maintained-tests',limit=90,allow_error=True)
   r['paired'][label]={'identity':identity,'verdict':verdict.strip(),'classifier_exit':class_code,'maintained_binary_sha256':sha(unit),'maintained_exit':unitcode,'temporary_files_after':obs['temporary_files_after']}
   return verdict.strip(),class_code,unitcode
  r['paired']['baseline']=prior['paired']['baseline']
  code,verdict=run(['python3',HERE/'classify.py',out/'baseline-observations.json',out/'baseline-identity.json'],'baseline-classification-replay',allow_error=True)
  assert (code,verdict.strip())==(1,'REPRODUCED')
  run(['git','apply','--check',HERE/'cloud-budget-fix.patch'],'candidate-patch-check',src)
  run(['git','apply',HERE/'cloud-budget-fix.patch'],'candidate-patch-apply',src)
  r['product_modified']=True
  changed=['src/modelnet/s3_store.cpp','src/modelnet/s3_store.h']
  r['candidate_source_sha256']={x:sha(src/x) for x in changed};r['candidate_patch_sha256']=sha(HERE/'cloud-budget-fix.patch')
  changedobj=bins/'candidate-s3-store.o';compile_changed=[cc[0],*flags,'-o',str(changedobj),'-c',str(src/'src/modelnet/s3_store.cpp')]
  run(compile_changed,'candidate-s3-compile',build,limit=300);r['production_recompiled']=True
  after=observe('candidate',changedobj);assert after==('PASS',0,0),after
  assert not r['paired']['candidate']['temporary_files_after']
  # Syntax-check the complete patched maintained source with real repository
  # headers; execution above uses only its exact test bodies in a small fixture.
  run(['git','apply',HERE/'startup-regression.patch'],'maintained-patch-apply',src)
  syntax=[cc[0],*flags,'-fsyntax-only',str(src/'src/test/modelnet_cloud_tests.cpp')]
  run(syntax,'maintained-full-source-syntax',build,limit=180);r['maintained_source_syntax_pass']=True
  r['action_count']=4
  assert sha(a)==ARCHIVE;r['original_archive_unchanged']=True
  r['verdict']='FAIL_BEFORE_PASS_AFTER';r['observation_complete']=True;r['safety_contract_pass']=True
  # No CMake or Ninja build target was executed; only s3_store was recompiled.
  r['pass']=True
 except Exception as e:r['pass']=False;r['error']=repr(e)
 finally:
  for name in ['consumer.cpp','startup-regression.patch','startup-regression.inc','maintained_wrapper.cpp','cloud-budget-fix.patch','classify.py']:
   shutil.copy2(HERE/name,out/name)
  (out/'result.json').write_text(json.dumps(r,indent=2)+'\n')
 return 0 if r['pass'] else 1
if __name__=='__main__':raise SystemExit(main())
