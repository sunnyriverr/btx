from pathlib import Path
import subprocess,os,json,socket,time,hashlib,shutil,signal,re,sys
r=Path('/BTX_REVIEW_ROOT');out=r/'pr340-fold-rerun';old=r/'pr340-pinned-metal';src=out/'source';build=out/'build';run=out/'run';run.mkdir(exist_ok=False)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
harness=old/'pinned_snapshot.py';assert sha(harness)=='838d2454c6e65fbc709c1e8469297ad5ea1c2492f90978121a001af17ad51678'
fixture=json.loads((old/'fixture.json').read_text());assert sha(old/'fixture-run/node0/regtest/pinned-window1124.dat')==fixture['snapshot_file_sha256']
sys.path.insert(0,str(r/'toolchain-2026-10-31/source/test/functional'))
from test_framework.util import PortSeed,p2p_port,rpc_port,tor_port
for seed in range(401,431):
 PortSeed.n=seed;ports=[f(i) for f in (p2p_port,rpc_port,tor_port) for i in range(2)];held=[]
 try:
  for port in ports:
   s=socket.socket();s.bind(('127.0.0.1',port));held.append(s)
  break
 except OSError:continue
 finally:
  for s in held:s.close()
else:raise RuntimeError('No unused test port set')
env={k:v for k,v in os.environ.items() if not k.startswith('BTX_')};env.update(BTXD=str(build/'bin/btxd'),BTXCLI=str(build/'bin/btx-cli'),BTX_MATMUL_BACKEND='metal',BTX_MATMUL_V4_BACKEND='metal',BTX_MATMUL_REQUIRE_BACKEND='metal',PINNED_VARIANT='candidate')
cmd=[sys.executable,str(harness),'--configfile='+str(build/'test/config.ini'),'--tmpdir='+str(run/'nodes'),'--nocleanup','--timeout-factor=1','--portseed='+str(seed)]
record={'source_head':subprocess.check_output(['git','-C',str(src),'rev-parse','HEAD']).decode().strip(),'source_diff_sha256':hashlib.sha256(subprocess.check_output(['git','-C',str(src),'diff','--binary'])).hexdigest(),'harness_sha256':sha(harness),'harness_unchanged':True,'binaries':{n:sha(build/'bin'/n) for n in ('btxd','btx-cli')},'snapshot_sha256':fixture['snapshot_file_sha256'],'snapshot_patch_sha256':sha(old/'exact-regtest1124-fixture.patch'),'command':cmd,'ports':ports,'transport_tests_run':False,'runtime_scope':'Strict-Metal toy-regtest, exact private1124 snapshot pin, normal loader, originalassertions. Not productionProfile1admission.'}
(run/'invocation.json').write_text(json.dumps(record,indent=2)+'\n')
def swap():
 t=subprocess.check_output(['/usr/sbin/sysctl','-n','vm.swapusage']).decode();return float(re.search(r'used = ([0-9.]+)M',t).group(1))
initialswap=swap();start=time.monotonic();stop=None
with (run/'console.log').open('wb') as log:
 p=subprocess.Popen(cmd,env=env,cwd=src,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
 record['runner_pid']=p.pid
 while p.poll() is None:
  if time.monotonic()-start>1500:stop='launcher1500s_deadline'
  if shutil.disk_usage(out).free<1536*1024**2:stop='disk_floor1.5GiB'
  if sum(f.stat().st_size for f in run.rglob('debug.log'))>600*1024**2:stop='owned_logs600MiB'
  if swap()-initialswap>256:stop='host_swap_growth256MiB'
  if stop:
   os.killpg(p.pid,signal.SIGTERM)
   try:p.wait(timeout=10)
   except subprocess.TimeoutExpired:os.killpg(p.pid,signal.SIGKILL);p.wait()
   break
  time.sleep(1)
 ret=p.wait()
record.update(exit_code=ret,elapsed_s=time.monotonic()-start,external_stop_reason=stop,initial_swap_MiB=initialswap,final_swap_MiB=swap(),free_bytes=shutil.disk_usage(out).free)
assert sha(harness)==record['harness_sha256']
(run/'result.json').write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(record,indent=2),flush=True);print((run/'console.log').read_text()[-3000:],flush=True)
