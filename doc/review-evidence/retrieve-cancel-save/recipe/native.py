"""Same bounded real-helper cancellation/retry and restart test for both trees."""
import argparse,json,os,signal,socket,tempfile,time,traceback
from pathlib import Path
from helpers import Helper,require,digest,completion
from observe import make_model,saved,verify_pieces,wait_for,cleanup_helpers,remove_stopped_runtime

def cancellation_error(reply):
 e=reply.get('error')
 return isinstance(e,dict) and e.get('code')=='IO_ERROR' and 'retry cancelmodeljob' in str(e.get('message',''))

def validate(r,expect):
 require(r.get('complete') is True and r.get('clean_cleanup') is True,'execution or cleanup incomplete')
 require(r['binary_verified'] and r['native_cases']==3,'binary or case gate')
 for name in ('save_failure_retry','healthy_cancel'):
  c=r['cases'][name]
  for key in ('persisted_active','partial_verified','live_stopped','pieces_preserved','clean_stop','restart_quiet','no_saved_job'):
   require(c.get(key) is True,name+': '+key)
 require(r['cases']['normal_restart']['completion_exact'] and r['cases']['normal_restart']['same_job'] and r['cases']['normal_restart']['pieces_preserved'],'normal restart control')
 expected=[] if expect=='candidate' else ['failed_cancel_error','repeat_cancel_error','retry_saved_snapshot']
 require(r['contract_failures']==expected,'unexpected contract result: '+str(r['contract_failures']))
 return True

def execute(binary,out,expect,expected_sha):
 out.mkdir(parents=True,exist_ok=False);helpers=[];faults=[];root=None
 r={'complete':False,'clean_cleanup':False,'expect':expect,'binary_sha256':digest(binary),'binary_verified':digest(binary)==expected_sha,'cases':{},'contract_failures':[],'native_cases':0};start=time.monotonic()
 def record():
  r['seconds']=time.monotonic()-start;(out/'result.json').write_text(json.dumps(r,indent=2)+'\n')
 def contract(key,value):
  if not value:r['contract_failures'].append(key)
 def alarm(*_):raise TimeoutError('native qualification 12 minute bound')
 signal.signal(signal.SIGALRM,alarm);signal.alarm(720)
 try:
  require(r['binary_verified'],'binary SHA-256 mismatch');root=Path(tempfile.mkdtemp(prefix='s2-cancel-save-'));model=root/'model.safetensors';make_model(model);identity=digest(model,'sha384')
  for name in ('save_failure_retry','healthy_cancel','normal_restart'):
   print('CASE '+expect+' '+name,flush=True);c={};r['cases'][name]=c
   with socket.socket() as sock:sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
   provider=Helper(binary,root/('provider-'+name),out,'provider-'+name,64<<20,hostport=port);helpers.append(provider);provider.start()
   imported=provider.ok('importmodel',[str(model),{'pin':True}]);require(imported.get('seeded') is True,'source not serving')
   recv=Helper(binary,root/name,out,name,64<<20,peer='127.0.0.1:'+str(port));helpers.append(recv);recv.start();job,answer=recv.request(imported['uri']);require(bool(job),'missing job ID');c['job_id']=job;c['request']=answer
   state=recv.store/'retrieve_jobs.json';wait_for(lambda:saved(state,job),10,'active job not saved');c['persisted_active']=True
   def partial():
    row=recv.job(job);require(row.get('status') in ('queued','running'),'premature job termination '+str(row));return recv.pieces(imported['artifact_id'])
   pieces=wait_for(partial,75,'no verified partial piece');verify_pieces(model,pieces);require(len(pieces)<5,'transfer already complete');c['partial_verified']=True;c['initial_pieces']=pieces;record()
   if name=='normal_restart':
    recv.stop();stopped=recv.pieces(imported['artifact_id']);verify_pieces(model,stopped);require(saved(state,job),'normal stop did not retain active job');recv.start();row=recv.job(job);require(row.get('job_id')==job,'normal restart changed job');c['same_job']=True
    final=recv.settled(job,180);require(final.get('status')=='done','normal restart failed '+str(final));c['completion']=completion(recv,imported['uri'],identity);c['completion_exact']=True
    current=recv.pieces(imported['artifact_id']);c['pieces_preserved']=all(k in current and current[k]['sha256']==v['sha256'] for k,v in pieces.items());require(c['pieces_preserved'],'normal restart discarded valid piece');recv.stop()
   else:
    fault=recv.store/'retrieve_jobs.json.tmp';before=state.read_bytes()
    if name=='save_failure_retry':require(not fault.exists(),'existing temporary path');fault.mkdir();faults.append(fault)
    reply=recv.rpc('cancelmodeljob',[job]);c['cancel_reply']=reply
    if name=='save_failure_retry':
     contract('failed_cancel_error',cancellation_error(reply));require(state.read_bytes()==before,'failed save changed previous file')
    else:require(not reply.get('error') and reply.get('result',{}).get('cancelled') is True,'healthy cancel did not change live job')
    # Real workers finish cancellation via failed("cancelled"). No test hook.
    terminal=wait_for(lambda:(x if (x:=recv.job(job)).get('status')=='failed' else None),35,'cancelled worker did not finish');c['worker_terminal']=terminal
    require('cancel' in str(terminal).lower() or 'stopped' in str(terminal).lower(),'worker failed for unrelated reason')
    stopped=recv.pieces(imported['artifact_id']);verify_pieces(model,stopped);time.sleep(3);require(recv.pieces(imported['artifact_id'])==stopped,'cancelled worker kept writing pieces');c['live_stopped']=True
    c['pieces_preserved']=all(k in stopped and stopped[k]['sha256']==v['sha256'] for k,v in pieces.items());require(c['pieces_preserved'],'cancel removed verified pieces')
    if name=='save_failure_retry':
     second=recv.rpc('cancelmodeljob',[job]);c['repeat_reply']=second;contract('repeat_cancel_error',cancellation_error(second));require(state.read_bytes()==before,'failed repeat changed previous file');fault.rmdir()
     retry=recv.rpc('cancelmodeljob',[job]);c['healthy_retry']=retry;require(not retry.get('error') and retry.get('result',{}).get('cancelled') is False,'terminal retry must not report a new transition');contract('retry_saved_snapshot',not saved(state,job))
     # Read error diagnostic while the helper is live; flushing is guaranteed by cerr.
     c['save_diagnostic']='could not save retrieve jobs' in (out/(name+'-1.log')).read_text(errors='replace')
    recv.stop();c['clean_stop']=True;c['no_saved_job']=not saved(state,job);require(c['no_saved_job'],'healthy shutdown failed to remove cancelled job')
    recv.start();end=time.monotonic()+12
    while time.monotonic()<end:
     require(not recv.job(job),'cancelled job returned after reopen');require(recv.pieces(imported['artifact_id'])==stopped,'cancelled transfer resumed after reopen');time.sleep(.5)
    c['restart_quiet']=True;recv.stop()
   provider.stop();r['native_cases']+=1;record()
  r['complete']=True
 except Exception:r['error']=traceback.format_exc()
 finally:
  signal.alarm(0)
  for f in faults:
   if f.is_dir():
    try:f.rmdir()
    except OSError:pass
  clean,stopped,errors=cleanup_helpers(helpers);r['clean_cleanup']=clean;r['cleanup_errors']=errors;r['processes_stopped']=stopped;r['helpers']=[{'label':h.label,'starts':h.starts,'forced':h.forced}for h in helpers];r['runtime_removed']=remove_stopped_runtime(root,stopped);record()
 validate(r,expect)
 if expect=='candidate':require(r['cases']['save_failure_retry']['save_diagnostic'],'missing persistence diagnostic')
 return r
if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--helper',type=Path,required=True);ap.add_argument('--sha256',required=True);ap.add_argument('--out',type=Path,required=True);ap.add_argument('--expect',choices=('baseline','candidate'),required=True);a=ap.parse_args();execute(a.helper.resolve(),a.out,a.expect,a.sha256)
