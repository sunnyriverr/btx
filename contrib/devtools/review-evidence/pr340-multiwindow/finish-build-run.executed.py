from pathlib import Path
import os,subprocess,json,time,shutil,signal,hashlib,re,sys
r=Path(__file__).resolve().parent.parent;o=Path(__file__).resolve().parent;src=o/'source';build=o/'build'
start=time.monotonic()
while not ((o/'build-result.json').exists() and (o/'fixture-launch.json').exists()):
 assert time.monotonic()-start<2100,'setup deadline'
 time.sleep(2)
assert json.loads((o/'build-result.json').read_text())['returncode']==0
assert json.loads((o/'fixture-launch.json').read_text())['returncode']==0
f=json.loads((o/'fixture.json').read_text());a=f['snapshot'];assert a['base_height']==4196
old=json.loads((r/'pr340-pinned-metal/fixture.json').read_text())['snapshot']
patch=(r/'pr340-pinned-metal/exact-regtest1124-fixture.patch').read_text().replace('.height = 1124,','.height = 4196,').replace('.m_chain_tx_count = 1125,','.m_chain_tx_count = '+str(a['nchaintx'])+',').replace('1024 historical RC bodies.','4096 historical RC bodies.')
for key in ['base_hash','txoutset_hash','shielded_state_pin']:patch=patch.replace(old[key],a[key])
(o/'exact-regtest4196.patch').write_text(patch)
subprocess.run(['git','-C',str(src),'apply','--check',str(o/'exact-regtest4196.patch')],check=True);subprocess.run(['git','-C',str(src),'apply',str(o/'exact-regtest4196.patch')],check=True)
assert subprocess.check_output(['git','-C',str(src),'diff','--name-only'],text=True).splitlines()==['src/kernel/chainparams.cpp']
with (o/'pin-build.log').open('w') as log:subprocess.run(['/opt/homebrew/bin/cmake','--build',str(build),'--target','btxd','btx-cli','-j','2'],stdout=log,stderr=log,check=True,timeout=240)
# Select a genuinely free port set before launch.
sys.path.insert(0,str(r/'toolchain-2026-10-31/source/test/functional'))
from test_framework.util import PortSeed,p2p_port,rpc_port,tor_port
import socket
for seed in range(551,581):
 PortSeed.n=seed;held=[]
 try:
  for port in [fn(i) for fn in [p2p_port,rpc_port,tor_port] for i in range(2)]:
   sk=socket.socket();sk.bind(('127.0.0.1',port));held.append(sk)
  break
 except OSError:continue
 finally:
  for sk in held:sk.close()
else:raise RuntimeError('no unused port set')
run=o/'run';run.mkdir(exist_ok=False)
env={k:v for k,v in os.environ.items() if not k.startswith('BTX_')};env.update(BTXD=str(build/'bin/btxd'),BTXCLI=str(build/'bin/btx-cli'),BTX_MATMUL_BACKEND='metal',BTX_MATMUL_V4_BACKEND='metal',BTX_MATMUL_REQUIRE_BACKEND='metal',PINNED_VARIANT='folded-four-window')
cmd=['python3',str(o/'pinned_snapshot.py'),'--configfile='+str(build/'test/config.ini'),'--tmpdir='+str(run/'nodes'),'--nocleanup','--portseed='+str(seed)]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
record={'command':cmd,'source_head':subprocess.check_output(['git','-C',str(src),'rev-parse','HEAD'],text=True).strip(),'private_pin_sha256':sha(o/'exact-regtest4196.patch'),'harness_sha256':sha(o/'pinned_snapshot.py'),'binaries':{n:sha(build/'bin'/n) for n in ['btxd','btx-cli']},'snapshot_sha256':f['snapshot_file_sha256'],'clean_build':True,'header_batch_limit':2000,'historical_bodies':4096,'real_download_window':1024}
(run/'invocation.json').write_text(json.dumps(record,indent=2));start=time.monotonic();stop=None
with (run/'console.log').open('w') as log:
 p=subprocess.Popen(cmd,env=env,stdout=log,stderr=log,start_new_session=True)
 while p.poll() is None:
  if time.monotonic()-start>1500:stop='1500s_runner_deadline'
  if shutil.disk_usage(o).free<1.5*1024**3:stop='disk_floor'
  if sum(q.stat().st_size for q in run.rglob('debug.log'))>600*1024**2:stop='600MiB_log_limit'
  if stop:os.killpg(p.pid,signal.SIGTERM);break
  time.sleep(1)
 try:rc=p.wait(timeout=10)
 except subprocess.TimeoutExpired:os.killpg(p.pid,signal.SIGKILL);rc=p.wait()
record.update(returncode=rc,elapsed_s=time.monotonic()-start,stop=stop);(run/'result.json').write_text(json.dumps(record,indent=2));print((run/'console.log').read_text()[-3500:]);print(json.dumps(record,indent=2))
