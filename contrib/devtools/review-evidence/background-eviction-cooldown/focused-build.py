from pathlib import Path
import subprocess,os,signal,time,json,shutil,shlex,hashlib
r=Path('<workspace>/work/btx-review-tools');out=r/'pr340-churn-fix'/'candidate';b=r/'pr340-fold-rerun/build'
commands=[['<homebrew>/bin/cmake','--build',str(b),'--target','bitcoin_node','bitcoin_common','bitcoin_wallet','bitcoin_modelnet','test_util','-j','2'],['/usr/bin/make','-C',str(b),'-f','src/test/CMakeFiles/test_btx.dir/build.make','src/test/CMakeFiles/test_btx.dir/main.cpp.o','src/test/CMakeFiles/test_btx.dir/peerman_tests.cpp.o','src/test/CMakeFiles/test_btx.dir/matmul_block_lifecycle_tests.cpp.o','-j1']]
results=[]
for n,cmd in enumerate(commands):
 start=time.monotonic();reason=None
 with (out/f'build-{n}.log').open('wb') as log:
  p=subprocess.Popen(cmd,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
  while p.poll() is None:
   if shutil.disk_usage(out).free<1536*1024**2:reason='diskfloor1.5GiB'
   if time.monotonic()-start>1200:reason='stage20minlimit'
   if reason:os.killpg(p.pid,signal.SIGTERM);break
   time.sleep(1)
  try:code=p.wait(timeout=10)
  except subprocess.TimeoutExpired:os.killpg(p.pid,signal.SIGKILL);code=p.wait()
 result={'command':cmd,'exit_code':code,'elapsed_s':time.monotonic()-start,'stop_reason':reason};results.append(result)
 (out/'build-result.json').write_text(json.dumps(results,indent=2)+'\n')
 print(json.dumps(result),flush=True)
 if code:print((out/f'build-{n}.log').read_text()[-3000:],flush=True);raise SystemExit(code)
args=shlex.split((b/'src/test/CMakeFiles/test_btx.dir/link.txt').read_text());keep=['CMakeFiles/test_btx.dir/main.cpp.o','CMakeFiles/test_btx.dir/peerman_tests.cpp.o','CMakeFiles/test_btx.dir/matmul_block_lifecycle_tests.cpp.o'];args=[a for a in args if not a.endswith('.o') or a in keep];args[args.index('-o')+1]=str(out/'focused-test-btx')
(out/'link-command.json').write_text(json.dumps(args,indent=2)+'\n')
with (out/'link.log').open('wb') as log:p=subprocess.run(args,cwd=b/'src/test',stdout=log,stderr=subprocess.STDOUT)
print('link',p.returncode,flush=True)
if p.returncode:print((out/'link.log').read_text()[-3000:],flush=True);raise SystemExit(p.returncode)
(out/'binary-identity.json').write_text(json.dumps({'sha256':hashlib.sha256((out/'focused-test-btx').read_bytes()).hexdigest(),'scope':'NormalCMake3testobjects plusnormalrebuiltlibraries; notfulltest_btx'},indent=2)+'\n')
