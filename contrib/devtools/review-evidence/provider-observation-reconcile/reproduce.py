from pathlib import Path
import sys,json,subprocess,tempfile,time,hashlib,shutil,struct,traceback
ROOT=Path(__file__).resolve().parent
from rpc_util import rpc_helper
profile=sys.argv[1];assert profile in ['baseline','candidate']
BIN=ROOT/profile/'btx-modeld';out=ROOT/(profile+'-result.json');scratch=Path(tempfile.mkdtemp(prefix='btx-obs-fix-',dir='/tmp'));scratch.chmod(0o700)
sp=scratch/'rpc.sock';data=scratch/'data';data.mkdir();p=None
report={'profile':profile,'binary_sha256':hashlib.sha256(BIN.read_bytes()).hexdigest(),'checks':[]}
def rpc(m,a=[]):return rpc_helper(sp,m,a)
def save():out.write_text(json.dumps(report,indent=2)+'\n')
def check(label,actual,expected):
 report['checks'].append({'label':label,'actual':actual,'expected':expected,'pass':actual==expected});save();print(label,actual==expected,flush=True)
def start():
 global p
 args=[str(BIN),'-modeldir='+str(data),'-modelrpcsocket='+str(sp),'-modelbind=off','-modelstorage=16MiB','-modelhost=1','-modelseed=off','-modelfollowpeers=0','-modellandiscovery=0','-modelnatpmp=0','-pwcchain=regtest']
 with (ROOT/(profile+'-helper.log')).open('a') as f:p=subprocess.Popen(args,stdout=f,stderr=f,start_new_session=True)
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
def obs(mid):return rpc('getmodelproviders',[mid])['providers']
def local(mid):return sum(x['provider_id']=='local' and x['complete'] and x['direct'] for x in obs(mid))
def search():return rpc('searchmodels',[{'scope':'LOCAL','text':'','limit':10}])
def fixture(n):
 h=json.dumps({'weight':{'dtype':'F32','shape':[256],'data_offsets':[0,1024]}},separators=(',',':')).encode();h+=b' '*((-len(h))%8)
 f=scratch/(str(n)+'.safetensors');f.write_bytes(struct.pack('<Q',len(h))+h+bytes([n])*1024)
 return rpc('importmodel',[str(f)])['model_id']
try:
 start();a,b=fixture(1),fixture(2)
 for mid in [a,b]:rpc('seedmodel',[mid])
 search();check('seeded A visible',local(a),1);check('seeded B visible',local(b),1)
 rpc('unhostmodel',[a]);check('unhost A immediately clears local',local(a),0);check('unhost A preserves B',local(b),1)
 rpc('seedmodel',[a]);search();check('reseed A visible',local(a),1)
 rpc('unseedmodel',[a]);check('unseed A immediately clears local',local(a),0);search();check('refresh does not restore unseeded A',local(a),0)
 rpc('seedmodel',[a]);search();check('second reseed A visible',local(a),1)
 rpc('removemodel',[a]);check('remove A immediately clears local',local(a),0)
 search();check('refresh does not restore removed A',local(a),0);check('remove A preserves B',local(b),1)
 check('catalog contains only B',[x['model_id'] for x in rpc('listmodels')['models']],[b])
 check('unknown ID returns empty',obs('11'*48),[])
 av=rpc('getmodelavailability',[a]);check('availability remains UNKNOWN',av['class'],'UNKNOWN');check('not reconstructable_known',av['reconstructable_known'],False)
 c=fixture(3);rpc('seedmodel',[c]);search();check('safety model starts complete',local(c),1)
 rpc('reportmodelmalicious',[c]);check('safety report unseeds catalog',next(x['seeded'] for x in rpc('listmodels')['models'] if x['model_id']==c),False)
 check('safety report immediately clears local',local(c),0)
 check('safety report availability count',rpc('getmodelavailability',[c])['providers_complete'],0)
 check('safety report peer count',rpc('getmodelpeercount',[c])['complete'],0)
 search();check('refresh does not restore safety blocked model',local(c),0)
 for method in ['getmodeldirectoryentry','getmodeleconomyentry']:
  response=rpc(method,[c]);check(method+' no stale local complete count',response['availability']['providers_complete'],0)
 check('unrelated seeded model survives safety block',local(b),1)
 stop();start();search();check('restart A absent',local(a),0);check('restart seeded B visible',local(b),1);check('restart safety model absent',local(c),0)

 report['health']=rpc('getmodelnetworkinfo');report['complete']=True;report['verdict']='PASS' if all(c['pass'] for c in report['checks']) else 'FAIL'
except Exception:
 report['error']=traceback.format_exc();raise
finally:
 if p is not None and p.poll() is None:stop()
 shutil.rmtree(scratch);report['cleanup']={'helper_stopped':p is None or p.poll() is not None,'scratch_removed':True};save()
