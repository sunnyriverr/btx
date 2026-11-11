from pathlib import Path
import os,json,subprocess,time,shutil,tarfile,shlex,signal,hashlib
from checkpoint import sha,restore_timestamps,verify_restored
W=Path(os.environ['GITHUB_WORKSPACE']);OUT=W/'repair-records';OUT.mkdir(exist_ok=True);BIN=W/'repair-binaries';BIN.mkdir(exist_ok=True)
R={'commands':[],'pass':False,'scope':'direct compatible cached-object component build; no clean project build'}
def run(args,label,cwd=W,limit=180,allowed=(0,)):
 print('START',label,flush=True);start=time.monotonic()
 with (OUT/(label+'.log')).open('wb') as f:
  p=subprocess.Popen(list(map(str,args)),cwd=cwd,stdout=f,stderr=subprocess.STDOUT,start_new_session=True)
  try:
   while p.poll() is None:
    if time.monotonic()-start>limit or shutil.disk_usage(W).free<2*1024**3:raise RuntimeError(label+' resource bound')
    time.sleep(.5)
  except BaseException:
   os.killpg(p.pid,signal.SIGTERM)
   try:p.wait(10)
   except subprocess.TimeoutExpired:os.killpg(p.pid,signal.SIGKILL);p.wait()
   raise
 R['commands'].append({'label':label,'exit':p.returncode,'seconds':time.monotonic()-start});(OUT/'progress.json').write_text(json.dumps(R,indent=2)+'\n');print('END',label,p.returncode,flush=True)
 assert p.returncode in allowed,label
 return (OUT/(label+'.log')).read_text(errors='replace')
def main():
 try:
  assert shutil.disk_usage(W).free>8*1024**3
  m=json.loads((W/'checkpoint-input/manifest.json').read_text());a=W/'checkpoint-input/build-state.tar.gz'
  assert sha(a)==m['archive_sha256']=='c4b58e4ef14e93f8b257c18bc855a7d9e4079a4659c9e3266fd25acad50d66df'
  assert m['identity']['integration_tree']=='ed72649dc18f4eaf55c9a6d1a2b171e587b482dd' and Path(m['workspace'])==W
  with tarfile.open(a) as t:t.extractall(W,filter='data')
  restore_timestamps(W,m);verify_restored(W,m);R['restore_verified']=True
  S=W/'product';B=W/'gui-pilot-runtime/qtbuild'
  assert run(['g++','-dumpfullversion'],'compiler').strip()=='11.4.0'
  commands=run(['ninja','-C',B,'-t','commands','btx-modeld'],'cached-commands').splitlines()
  link=shlex.split(commands[-1])[2:-2];assert link[0]=='/usr/bin/g++'
  R['cached_identity']=m['identity'];R['archive_sha256']=m['archive_sha256'];R['action_budget']=8
  R['source_before']={n:sha(S/n) for n in ['src/modelnet/helper.cpp','src/modelnet/catalog.cpp','src/modelnet/catalog.h']}
  run(['git','apply','--check',W/'product.patch'],'patch-check',S);run(['git','apply',W/'product.patch'],'patch',S)
  R['patch_sha256']=sha(W/'product.patch');R['source_after']={n:sha(S/n) for n in R['source_before']}
  def compile_command(name,obj):
   rows=[shlex.split(l) for l in commands if l.rstrip().endswith('-c '+str(S/name))];assert len(rows)==1
   original=rows[0];flags=[];i=1
   while i<len(original):
    if original[i] in ('-MT','-MF','-o','-c'):i+=2;continue
    if original[i]=='-MD':i+=1;continue
    flags.append(original[i]);i+=1
   return [original[0],*flags,'-o',str(obj),'-c',str(S/name)]
  cat=BIN/'catalog.o';helper=BIN/'helper.o';unit=BIN/'unit.o'
  catcmd=compile_command('src/modelnet/catalog.cpp',cat);helpcmd=compile_command('src/modelnet/helper.cpp',helper)
  unitcmd=catcmd[:];unitcmd[unitcmd.index('-o')+1]=str(unit);unitcmd[-1]=str(W/'unit_wrapper.cpp')
  def linking(input_obj,output,include_helper):
   cmd=link[:];pos=cmd.index('src/modelnet/CMakeFiles/btx-modeld.dir/__/modeld.cpp.o')
   if input_obj:cmd[pos]=str(input_obj)
   overrides=[str(cat)]+([str(helper)] if include_helper else [])
   cmd[pos:pos]=overrides;cmd[cmd.index('-o')+1]=str(output)
   cmd=[x for x in cmd if x!='-Wl,--unresolved-symbols=ignore-in-shared-libs'];return cmd
  plan={'catalog':catcmd,'helper':helpcmd,'unit':unitcmd,'helper_link':linking(None,BIN/'candidate',True),'unit_link':linking(unit,BIN/'quota-unit',False)}
  (OUT/'admitted-plan.json').write_text(json.dumps(plan,indent=2)+'\n');assert len(plan)<=8
  # Quick component controls before spending time on the large helper TU.
  run(catcmd,'catalog-compile',B,limit=240);run(unitcmd,'unit-compile',B,limit=240);run(plan['unit_link'],'unit-link',B,limit=180)
  run(['env','QUOTA_UNIT_DIR='+str(W/'unit-runtime'),BIN/'quota-unit','--run_test=modelnet_b0_disc_store_tests','--log_level=test_suite','--report_level=detailed'],'maintained-cases',limit=90)
  R['unit_pass']=True;R['unit_sha256']=sha(BIN/'quota-unit')
  run(helpcmd,'helper-compile',B,limit=1500);run(plan['helper_link'],'helper-link',B,limit=180)
  R['candidate_sha256']=sha(BIN/'candidate');R['stock_sha256']=sha(W/'stock/base');assert R['stock_sha256']=='0412b4d3d09ecd40e954f031ba4d2487e089a078084669af9ec598b041ba1a6c'
  for label,binary,digest in [('baseline',W/'stock/base',R['stock_sha256']),('candidate',BIN/'candidate',R['candidate_sha256'])]:
   os.chmod(binary,0o755);output=OUT/label
   run(['python3','-u',W/'native_fixture.py','--binary',binary,'--expected-sha256',digest,'--output',output],label+'-native',limit=380)
   obs=json.loads((output/'observations.json').read_text());expected='CONFIRMED' if label=='baseline' else 'DISPROVED';assert obs['result']==expected,(label,obs['result'])
  run(['git','apply',W/'regression.patch'],'maintained-source-patch',S)
  syntax=catcmd[:];syntax=syntax[:syntax.index('-o')]+['-fsyntax-only',str(S/'src/test/modelnet_b0_disc_store_tests.cpp')]
  run(syntax,'maintained-full-source-syntax',B,limit=180);R['full_test_source_syntax']=True
  R['fixture_sha256']=sha(W/'native_fixture.py');R['regression_body_sha256']=sha(W/'regression.inc');R['original_archive_unchanged']=sha(a)==m['archive_sha256'];R['verdict']='FAIL_BEFORE_PASS_AFTER';R['pass']=True
 except Exception as e:R['error']=repr(e)
 finally:
  for n in ['product.patch','regression.patch','regression.inc','native_fixture.py','unit_wrapper.cpp']:
   shutil.copy2(W/n,OUT/n)
  R['retained_outputs']={x.name:sha(x) for x in BIN.iterdir() if x.is_file()};(OUT/'result.json').write_text(json.dumps(R,indent=2)+'\n')
 return 0 if R['pass'] else 1
if __name__=='__main__':raise SystemExit(main())
