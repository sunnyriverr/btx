"""Execute the exact maintained progress cases on retained/rebuilt real helpers."""
from pathlib import Path
import argparse,hashlib,importlib.util,json,logging,os,signal,socket,sys,tempfile,time,traceback,types,shutil

class NativeDeadline(BaseException):
 pass

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def validate(r,phase):
 assert r.get('complete') and r.get('clean_cleanup') and r.get('binary_verified'),'incomplete execution or cleanup'
 assert set(r['cases'])=={'progress','progress_multi'},'case missing'
 for name,c in r['cases'].items():
  o=c['observation'];assert o['b_exact'] and o['a_unchanged'] and o['restart_preserved_pieces'],'integrity/resume control failed'
  assert o['stream_attempted'] and 0<o['actual']<o['total'],'not an incomplete-stream observation'
  assert o['file_count']==(2 if name=='progress_multi'else 1),'wrong file setup'
  if phase=='baseline':
   assert c['assertion_failure'] and not c.get('unexpected_error'),'baseline not intended assertion failure'
   assert o['a_bytes']<=o['reported']<=o['actual']+o['a_bytes'] and o['percent']==100 and o['final_reported']==o['total']+o['a_bytes'],'baseline wrong failure'
  else:
   assert phase=='candidate' and not c['assertion_failure'] and not c.get('unexpected_error'),'candidate failed'
   assert o['reported']==o['actual'] and o['percent']==o['actual']*100//o['total'] and o['eta_present'] and o['final_reported']==o['total'],'candidate scope wrong'
  if name=='progress':
   resumed=o['resumed'];assert resumed['inflight']>0 and 0<resumed['actual']<o['total'],'no live resumed observation'
   if phase=='baseline':assert o['a_bytes']<=resumed['reported']<=o['a_bytes']+resumed['actual'] and resumed['percent']==100,'wrong resumed baseline failure'
   else:assert resumed['reported']==resumed['actual'] and resumed['percent']==resumed['actual']*100//o['total'],'wrong resumed candidate accounting'
 return True

def run(binary,out,phase,expected):
 out.mkdir(parents=True,exist_ok=False);w=Path(os.environ['GITHUB_WORKSPACE']);src=w/'product';sys.path.insert(0,str(src/'test/functional'))
 spec=importlib.util.spec_from_file_location('maintained_retrieve_cases',src/'test/functional/feature_modelnet_retrieve_regressions.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
 root=Path(tempfile.mkdtemp(prefix='s2-progress-repair-'));r={'complete':False,'clean_cleanup':False,'binary_sha256':sha(binary),'binary_verified':sha(binary)==expected,'cases':{}};processes=[];t=None;calls=[];start=time.monotonic()
 def save():r['seconds']=time.monotonic()-start;(out/'result.json').write_text(json.dumps(r,indent=2)+'\n');(out/'rpc.json').write_text(json.dumps(calls,indent=2)+'\n')
 def alarm(*_):raise NativeDeadline('15minute native bound')
 signal.signal(signal.SIGALRM,alarm);signal.alarm(900)
 try:
  assert r['binary_verified'],'helper binary identity'
  for name in ('progress','progress_multi'):
   print('CASE',phase,name,flush=True);case_root=root/name;case_root.mkdir();t=object.__new__(module.ModelNetRetrieveRegressionsTest);t.helpers={};t.sock_scratch=None;t.options=types.SimpleNamespace(tmpdir=str(case_root),timeout_factor=1);t.config={'environment':{'BUILDDIR':str(binary.parent.parent),'EXEEXT':''}};t.log=logging.getLogger(name)
   ports={}
   def port(i):
    if i not in ports:
     with socket.socket()as sock:sock.bind(('127.0.0.1',0));ports[i]=sock.getsockname()[1]
    return ports[i]
   module.p2p_port=port
   original_rpc=t._rpc;original_start=t._start_helper;original_stop=t._stop_helper
   def rpc(label,method,params=None):
    result=original_rpc(label,method,params);calls.append({'case':name,'helper':label,'method':method,'params':params,'result':result});return result
   t._rpc=rpc
   def launch(label,args,env=None,storage='512MiB'):
    home=case_root/('home-'+label);home.mkdir(exist_ok=True)
    try:info=original_start(label,args,env=dict(os.environ,HOME=str(home),XDG_DATA_HOME=str(home/'data')),storage=storage)
    finally:
     if label in t.helpers:processes.append({'case':name,'label':label,'proc':t.helpers[label]['proc']})
    proc=t.helpers[label]['proc'];assert Path('/proc/'+str(proc.pid)+'/exe').resolve()==binary
    if any(x.startswith('-modeluploadlimit=')for x in args):assert info['upload_limit']==512*1024,'pacing not applied'
    return info
   t._start_helper=launch
   def stop(label):
    h=t.helpers.get(label);original_stop(label)
    if h:
     log=h['dir']/'modeld.log';idx=len(list(out.glob(name+'-'+label+'-*.log')));shutil.copy2(log,out/(name+'-'+label+'-'+str(idx)+'.log'))
   t._stop_helper=stop
   c={'assertion_failure':False};r['cases'][name]=c
   try:getattr(t,'case_'+name)()
   except AssertionError as e:c['assertion_failure']=True;c['assertion_text']=str(e)
   except Exception:c['unexpected_error']=traceback.format_exc()
   c['observation']=getattr(t,'progress_observation',{});save()
   for label in list(t.helpers):t._stop_helper(label)
   if t.sock_scratch is not None:shutil.rmtree(t.sock_scratch)
  r['complete']=True
 except NativeDeadline:r['error']='15minute native deadline exceeded; no further case executed'
 except Exception:r['error']=traceback.format_exc()
 finally:
  signal.alarm(0);errors=[]
  if t is not None:
   for label in list(t.helpers):
    try:t._stop_helper(label)
    except Exception as e:errors.append(str(e))
  r['processes']=[{'case':x['case'],'label':x['label'],'exit':x['proc'].poll()}for x in processes];r['clean_cleanup']=bool(processes)and not errors and all(x['exit']==0 for x in r['processes']);r['cleanup_errors']=errors
  if all(x['proc'].poll()is not None for x in processes):shutil.rmtree(root);r['runtime_removed']=True
  save()
 validate(r,phase);return r
if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--helper',type=Path,required=True);ap.add_argument('--sha256',required=True);ap.add_argument('--out',type=Path,required=True);ap.add_argument('--expect',choices=('baseline','candidate'),required=True);a=ap.parse_args();run(a.helper.resolve(),a.out,a.expect,a.sha256)
