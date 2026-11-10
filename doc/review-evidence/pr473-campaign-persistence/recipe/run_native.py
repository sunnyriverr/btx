"""Real local btx-modeld Unix RPC and disposable file-size failure, no node."""
from pathlib import Path
import os,sys,json,hashlib,socket,struct,subprocess,resource,signal,shutil,time,tempfile,re
from result_contract import classify
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 w=Path(os.environ['GITHUB_WORKSPACE']);out=w/'campaign-native-records';out.mkdir(exist_ok=True)
 build=json.loads((w/'build-input/result.json').read_text());assert build['pass'] and build['archive_unchanged']
 assert build['integration_tree']=='ed72649dc18f4eaf55c9a6d1a2b171e587b482dd'
 state={'profile':'Ubuntu22 x86_64 real helper Unix RPC; no btxd, wallet, peers, inference or spending','variants':{},'build_binary_sha256':build['binaries']}
 def save():(out/'result.json').write_text(json.dumps(state,indent=2)+'\n')
 def variant(label):
  r=state['variants'][label]={'cleanup_signals':[],'leftovers':[]};tmp=Path(tempfile.mkdtemp(prefix='cp473-'));home=tmp/'home';home.mkdir();store=tmp/'store';store.mkdir();sock=tmp/'rpc.sock';proc=None;pid=None;logs=[];seq=0
  binary=w/'helper-input'/label;assert sha(binary)==build['binaries'][label];binary.chmod(0o755);r['exact_binary_identity']=True
  model=tmp/'toy.safetensors';hdr=json.dumps({'__metadata__':{'format':'pt'},'w':{'dtype':'F32','shape':[1],'data_offsets':[0,4]}}).encode();model.write_bytes(struct.pack('<Q',len(hdr))+hdr+b'\0'*4)
  def rpc(method,params):
   nonlocal seq
   seq+=1;req={'jsonrpc':'1.0','id':seq,'method':method,'params':params}
   with socket.socket(socket.AF_UNIX) as s:
    s.settimeout(25);s.connect(str(sock));s.sendall(json.dumps(req).encode()+b'\n');s.shutdown(socket.SHUT_WR)
    with s.makefile('rb') as f:data=f.read(1024*1024+1)
   assert len(data)<=1024*1024
   ans=json.loads(data);assert ans['id']==seq and 'error' in ans and 'result' in ans
   return ans
  def ok(method,params):
   ans=rpc(method,params);assert ans['error'] is None,(method,ans['error']);return ans['result']
  def owned():
   result=[]
   if proc is not None:
    for f in Path('/proc').iterdir():
     if not f.name.isdigit():continue
     i=int(f.name)
     try:
      if os.getpgid(i)==proc.pid and (f/'exe').resolve()==binary.resolve():result.append(i)
     except OSError:pass
   return result
  def start(phase,trace_file=None,campaign=None):
   nonlocal proc,pid
   assert proc is None and not sock.exists()
   args=[binary,'-modeldir='+str(store),'-modelrpcsocket='+str(sock),'-modelstorage=8MiB','-modellandiscovery=0','-modelfollowpeers=0','-modelnatpmp=0','-modelhost=0','-modelseed=off','-pwcchain=regtest']
   if trace_file:args=['strace','-f','-y','-s','0','-e','trace=write,writev,fsync,fdatasync,close,rename,renameat,renameat2,openat','-P',campaign,'-P',str(campaign)+'.tmp','-o',trace_file,*args]
   log=(out/(label+'-'+phase+'.log')).open('wb');logs.append(log)
   proc=subprocess.Popen(list(map(str,args)),env=dict(os.environ,HOME=str(home),XDG_DATA_HOME=str(home/'data'),XDG_RUNTIME_DIR=str(tmp)),stdout=log,stderr=subprocess.STDOUT,start_new_session=True,preexec_fn=lambda:signal.signal(signal.SIGXFSZ,signal.SIG_IGN))
   until=time.monotonic()+30
   while not sock.exists():
    assert proc.poll() is None and time.monotonic()<until,'Helper failed startup';time.sleep(.1)
   pids=owned();assert len(pids)==1,pids;pid=pids[0]
   assert int(re.search(r'^SigIgn:\s*([0-9a-f]+)',Path(f'/proc/{pid}/status').read_text(),re.M)[1],16)&(1<<(signal.SIGXFSZ-1))
   assert isinstance(ok('getmodelnetworkinfo',[]),dict)
  def stop():
   nonlocal proc,pid
   assert proc is not None and pid in owned()
   os.kill(pid,signal.SIGTERM)  # documented normal helper stop
   proc.wait(timeout=25);assert proc.returncode==0 and not owned()
   assert not sock.exists();proc=None;pid=None
  def new_campaign():
   hosted=ok('hostmodel',[str(model)]);assert hosted['uri'].startswith('btx:')
   rel=ok('createmodelrelease',[{'uri':hosted['uri'],'secret32_hex':hashlib.sha256(b'disposable-campaign-fixture').hexdigest(),'refund_height':50,'target_atoms':100000000,'publish_search_record':False}]);assert rel['automatic_spend_atoms']==0 and rel['publish_state']=='local_campaign_only'
   return rel['release_id']
  def memory(rid):
   res=ok('getmodelrelease',[]);assert res['automatic_spend_atoms']==0
   rows=[c for c in res['campaigns'] if c['release_id']==rid];assert len(rows)<=1
   return int(rows[0]['pledged_atoms']) if rows else None
  def disk(path,rid):
   raw=path.read_bytes();d={'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}
   try:
    v=json.loads(raw);d['parseable']=True;rows=[c for c in v['campaigns'] if c['release_id']==rid];d['pledged_atoms']=int(rows[0]['pledged_atoms']) if rows else None
   except (ValueError,KeyError,TypeError):d['parseable']=False
   return d
  try:
   start('seed');rid=new_campaign();assert memory(rid)==0
   assert int(ok('pledgemodelrelease',[rid,1])['pledged_atoms'])==1
   found=list(tmp.rglob('campaigns.json'));assert len(found)==1;campaign=found[0];seed=disk(campaign,rid);assert seed['pledged_atoms']==1
   r['supported_nonspending_request']=True;r['before_disk']=seed;stop()
   trace=out/(label+'-campaign-io.log');start('fault',trace,campaign);assert memory(rid)==1
   seed=disk(campaign,rid);assert seed['pledged_atoms']==1;r['before_disk']=seed;r['normal_save_restart']=True
   # This PID is verified against the exact binary and owned process group.
   soft,hard=resource.prlimit(pid,resource.RLIMIT_FSIZE);assert hard==resource.RLIM_INFINITY or hard>=seed['bytes'];resource.prlimit(pid,resource.RLIMIT_FSIZE,(seed['bytes'],hard));assert resource.prlimit(pid,resource.RLIMIT_FSIZE)[0]==seed['bytes']
   r['limit_bytes']=seed['bytes'];delta=10000000
   ans=rpc('pledgemodelrelease',[rid,delta]);r['fault_reply']=ans;r['rpc_acknowledged']=ans['error'] is None
   live=memory(rid);assert live in (1,1+delta);r['memory_after']=live;r['memory_changed']=live!=1
   if r['rpc_acknowledged']:assert int(ans['result']['pledged_atoms'])==1+delta and ans['result']['automatic_spend_atoms']==0
   r['fault_disk']=disk(campaign,rid);r['disk_changed']=r['fault_disk']['sha256']!=seed['sha256']
   assert not Path(str(campaign)+'.tmp').exists()
   assert isinstance(ok('getmodelnetworkinfo',[]),dict);assert resource.prlimit(pid,resource.RLIMIT_FSIZE)[0]==seed['bytes']
   stop();r['same_failure_held_through_stop']=True;r['after_stop_disk']=disk(campaign,rid)
   lines=trace.read_text().splitlines();writes=[l for l in lines if ('campaigns.json>' in l or 'campaigns.json.tmp>' in l) and ('write(' in l or 'writev(' in l)]
   short=[]
   for line in writes:
    m=re.search(r', (\d+)\)\s+=\s+(\d+)(?:\s|$)',line)
    if 'EFBIG' in line or (m and int(m[2])<int(m[1])):short.append(line)
   r['fault_trace_matches']=short;r['campaign_save_failure_confirmed']=bool(short);assert short,'No campaign write failure observed'
   start('restart');assert resource.prlimit(pid,resource.RLIMIT_FSIZE)[0]==soft;r['fault_removed']=True
   after=memory(rid);r['restart_amount']=after;r['restart_observed']=True;r['restart_retained_change']=after==1+delta
   # Recovery is a new valid increment after reconciling actual state, never blind retry.
   recid=rid if after is not None else new_campaign();old=memory(recid);assert old is not None
   assert int(ok('pledgemodelrelease',[recid,3])['pledged_atoms'])==old+3;assert disk(campaign,recid)['pledged_atoms']==old+3;stop();start('recovery-check');assert memory(recid)==old+3;stop()
   r['normal_write_recovery']=True;r['recovery_amount']=old+3;r['recreated_missing_campaign']=recid!=rid;r['clean_shutdown']=True
  except Exception as e:r['error']=repr(e)
  finally:
   if proc is not None:
    try:stop()
    except Exception:
     if proc.poll() is None:
      r['cleanup_signals'].append('SIGKILL');os.killpg(proc.pid,signal.SIGKILL);proc.wait(timeout=10)
   r['leftovers']=owned();[f.close() for f in logs]
   if not r['leftovers']:shutil.rmtree(tmp)
   r['owned_runtime_removed']=not tmp.exists();r['classification']=classify(r);save()
 for label in ('base','candidate'):variant(label)
 state['complete']=all(r['classification']['outcome'] not in ('INCOMPLETE','UNRESOLVED') for r in state['variants'].values());save();return 0 if state['complete'] else 1
if __name__=='__main__':raise SystemExit(main())
