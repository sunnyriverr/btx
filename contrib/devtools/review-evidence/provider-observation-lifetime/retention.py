from pathlib import Path
import sys,json,socket,subprocess,tempfile,time,hashlib,shutil,traceback
ROOT=Path(__file__).resolve().parent
from rpc_util import rpc_helper
profile=sys.argv[1];assert profile in ['baseline','candidate'];BIN=ROOT/profile/'btx-modeld'
assert hashlib.sha256(BIN.read_bytes()).hexdigest()==json.loads((ROOT/'binary-identities.json').read_text())[profile]['sha256']
scratch=Path(tempfile.mkdtemp(prefix='btx-obs-mem-',dir='/tmp'));scratch.chmod(0o700)
sp=scratch/'rpc.sock';data=scratch/'data';data.mkdir();p=None
report={'binary_sha256':hashlib.sha256(BIN.read_bytes()).hexdigest(),'query_scope':'owner-local Unix RPC, unknown valid model IDs, no peer connections','samples':[]}
def rss():return int(subprocess.check_output(['ps','-o','rss=','-p',str(p.pid)],text=True).strip())
def save(): (ROOT/(profile+'-retention.json')).write_text(json.dumps(report,indent=2))
def sample(label,**extra):
 r={'label':label,'time':time.time(),'rss_kib':rss(),**extra};report['samples'].append(r);save();print(r,flush=True)
 assert r['rss_kib']<256*1024
 assert shutil.disk_usage(ROOT).free>1.25*1024**3
 return r
def rpc(m,a=[]):return rpc_helper(sp,m,a)
def start():
 global p
 args=[str(BIN),'-modeldir='+str(data),'-modelrpcsocket='+str(sp),'-modelbind=off','-modelstorage=16MiB','-modelhost=0','-modelseed=off','-modelfollowpeers=0','-modellandiscovery=0','-modelnatpmp=0','-pwcchain=regtest']
 with (ROOT/(profile+'-retention-helper.log')).open('a') as f:p=subprocess.Popen(args,stdout=f,stderr=f,start_new_session=True)
 for _ in range(100):
  if p.poll() is not None:raise RuntimeError('helper exit')
  try:
   if rpc('getmodelnetworkinfo').get('pq1_ready'):return
  except (OSError,ValueError):pass
  time.sleep(.1)
 raise RuntimeError('not ready')
def stop():
 p.terminate()
 try:p.wait(timeout=10)
 except subprocess.TimeoutExpired:p.kill();p.wait()
def batch(label,ids):
 t=time.monotonic();n=0
 for mid in ids:
  r=rpc('getmodelproviders',[mid]);assert r['providers']==[];n+=1
  if n%1000==0:assert rss()<256*1024
 sample(label,calls=n,elapsed_s=time.monotonic()-t)
def mid(n):return hashlib.sha384(('bounded-observation-test-'+str(n)).encode()).hexdigest()
try:
 start();batch('warmup', [mid(0)]*1000)
 batch('same_id_10000_before',[mid(0)]*10000)
 batch('distinct_10000_a',(mid(n) for n in range(1,10001)))
 batch('same_id_10000_between',[mid(0)]*10000)
 batch('distinct_10000_b',(mid(n) for n in range(10001,20001)))
 time.sleep(30);sample('idle_30s')
 batch('same_20001_ids_again',(mid(n) for n in range(20001)))
 report['health']=rpc('getmodelnetworkinfo');save()
 stop();start();batch('restart_warmup',[mid(0)]*1000);sample('restart_idle');report['complete']=True
except Exception:
 report['error']=traceback.format_exc();raise
finally:
 if p is not None and p.poll() is None:stop()
 shutil.rmtree(scratch);report['cleanup']={'helper_stopped':p is None or p.poll() is not None,'scratch_removed':True};save()
