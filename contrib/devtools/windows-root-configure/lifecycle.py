"""Resume the exact unfiltered maintained test_btx target; retain normal progress."""
from pathlib import Path
import os,sys,json,hashlib,subprocess,shutil,base64,re,time
import checkpoint
import integration_support as s
P=Path(__file__).resolve().parent;ROOT=s.ROOT;SOURCE=s.SOURCE;BUILD=s.BUILD;E=s.E
I=json.loads((P/'lifecycle-inputs.json').read_text());TARGET=I['target'];s.STATE=E/'lifecycle.json';s.R=json.loads(s.STATE.read_text())if s.STATE.exists()else{'target':TARGET,'scope':I['scope'],'commands':[],'process_active':False,'unit_built':False,'unit_invoked':False,'status':'SETUP'};R=s.R;sha=s.sha

def diff(a,b,p=''):
 out={}
 for k in sorted(set(a)|set(b)):
  x,y=a.get(k),b.get(k)
  if isinstance(x,dict)and isinstance(y,dict):out.update(diff(x,y,p+k+'.'))
  elif x!=y:out[p+k]=[x,y]
 return out

def prepare():
 setup=json.loads((E/'result.json').read_text());assert setup['stages']['profile']=='COMPLETE'
 marker=BUILD/'btx-checkpoint.json';assert sha(marker)==I['checkpoint_sha256'];cp=json.loads(marker.read_text());assert cp['profile']['source']==TARGET
 actual=setup['profile'];expected=cp['profile']['actual_current_profile'];d=diff(expected,actual);allowed=json.loads((P/'profile-transition.json').read_text())['allowed_differences'];reverse={k:list(reversed(v))for k,v in allowed.items()};assert d in [{},allowed,reverse],d
 assert subprocess.check_output(['ninja','--version'],text=True).strip()=='1.13.2'
 bundle=E/'full-source.bundle';bundle.write_bytes(base64.b64decode((P/'full-source.bundle.base64').read_text()));assert sha(bundle)==I['bundle_sha256']
 s.need('full-prerequisite-fetch',['git','fetch','--no-tags','--depth=2','https://github.com/sunnyriverr/btx.git',I['published_source']],120)
 s.need('full-bundle-verify',['git','bundle','verify',str(bundle)],60);s.need('full-bundle-fetch',['git','fetch',str(bundle),I['bundle_ref']],60);s.need('full-source-checkout',['git','checkout','--detach',TARGET],60)
 cat=s.catalog(TARGET,'full-before');assert cat==cp['source_catalog'];R['restore']=checkpoint.restore(ROOT,SOURCE,cp['profile'],cat);assert R['restore']['restored']
 R['source_catalog']=cat;R['actual_profile']=actual;R['input_profile']=cp['profile'];R['host_transition']=d;R['original_config']=cp['profile']['configuration'];assert all(sha(BUILD/n)==h for n,h in R['original_config'].items())
 config=(BUILD/'CMakeCache.txt').read_text()
 for flag in ['WITH_MODELNET:BOOL=ON','BUILD_TESTS:BOOL=ON','ENABLE_WALLET:BOOL=ON','WITH_ZMQ:BOOL=ON']:assert flag in config
 commands=json.loads((BUILD/'compile_commands.json').read_text());R['maintained_test_compile_entries']=sum('/test_btx.dir/'in c['output'].replace('\\','/')for c in commands);assert R['maintained_test_compile_entries']==2606
 manifest=E/'full-unit.ninja';shutil.copyfile(BUILD/'build.ninja',manifest);assert sha(manifest)==R['original_config']['build.ninja'];R['manifest_sha256']=sha(manifest)
 R['expected_missing_unit_objects']=sum('/test_btx.dir/'in c['output'].replace('\\','/')and 'project-build\\'+c['output'].replace('\\','/').split('/project-build/',1)[1].replace('/','\\')not in cp['files']for c in commands)
 R['target_rows']=[]
 for name in I['files']:
  found=[c for c in commands if c['file'].replace('\\','/').endswith('/src/test/'+name)and'/test_btx.dir/'in c['output'].replace('\\','/')];assert len(found)==1
  c=found[0];target=c['output'].replace('\\','/').split('/project-build/',1)[1];key='project-build\\'+target.replace('/','\\');R['target_rows'].append({'file':name,'target':target,'command':c,'present_before':key in cp['files']})
 R['source_changes_from_checkpoint']=[];R['profile']={'source':TARGET,'actual_current_profile':actual,'input_checkpoint_sha256':I['checkpoint_sha256'],'source_bundle_sha256':I['bundle_sha256'],'controls_sha256':sha(P/'lifecycle.py'),'support_sha256':sha(P/'integration_support.py'),'scope':I['scope'],'normal_ninja_dependencies':True,'configuration':R['original_config']};R['status']='FULL_READY';s.save()

def build():
 assert R['status']=='FULL_READY';common=['ninja','-C',str(BUILD),'-f',str(E/'full-unit.ninja')];exe=BUILD/'bin/btxd.exe';R['before_binary_sha256']=sha(exe);R['modelnet_library_sha256']=sha(BUILD/'lib/bitcoin_modelnet.lib');assert R['modelnet_library_sha256']=='4c924f0731642e0b8aedece02ba8a3229a59b254c0da20637aaea39db5fb529c'
 s.need('node-plan',common+['-d','explain','-n','btxd'],120);text=(E/'node-plan.log').read_text(errors='replace');steps=re.findall(r'^\[(\d+)/(\d+)\]',text,re.M);R['planned_steps']=int(steps[-1][1])if steps else 0;assert 0<R['planned_steps']<=120,R['planned_steps'];assert 'command line changed for'not in text and 'Re-running CMake'not in text and 'Re-checking globbed directories'not in text
 assert sha(E/'full-unit.ninja')==R['original_config']['build.ninja'];R['status']='NODE_BUILDING';s.save();code=s.run('candidate-node-build',common+['--verbose','-j','4','-k','1','btxd'],900);R['node_build_exit']=code
 if code:R['status']='NODE_BUILD_FAILURE';raise RuntimeError('Actual node compiler/link barrier')
 R['binary_sha256']=sha(exe);assert R['binary_sha256']!=R['before_binary_sha256'];R['build_info']=(BUILD/'src/bitcoin-build-info.h').read_text();assert TARGET in R['build_info']and 'BUILD_GIT_DIRTY 0'in R['build_info'];assert sha(BUILD/'lib/bitcoin_modelnet.lib')==R['modelnet_library_sha256'];s.need('node-imports',['dumpbin','/dependents',str(exe)],60);s.need('node-version',[str(exe),'-version'],30);R['node_linked']=True;R['status']='NODE_LINKED';s.save()

# Actual node lifecycle; no helper replacement, public peers, wallet or mining.
def rpc(port,cookie,method,params=None):
 import urllib.request,urllib.error,base64
 token=cookie.read_bytes().strip();data=json.dumps({'jsonrpc':'1.0','id':'wl','method':method,'params':params or []}).encode();req=urllib.request.Request('http://127.0.0.1:'+str(port),data=data,headers={'Authorization':'Basic '+base64.b64encode(token).decode(),'Content-Type':'application/json'})
 try:
  with urllib.request.urlopen(req,timeout=3)as z:out=json.load(z)
 except urllib.error.HTTPError as ex:
  out=json.loads(ex.read());raise RuntimeError('RPC '+method+' error code '+str((out.get('error')or{}).get('code')))
 if out.get('error'):raise RuntimeError('RPC '+method+' error code '+str(out['error'].get('code')))
 return out['result']

def port_free():
 import socket
 with socket.socket()as sock:sock.bind(('127.0.0.1',0));return sock.getsockname()[1]

def stopped_port(port):
 import socket
 with socket.socket()as sock:sock.settimeout(1);return sock.connect_ex(('127.0.0.1',port))!=0

def snapshot(label):
 rows=s.owned_processes();R.setdefault('process_snapshots',[]).append({'label':label,'rows':rows});s.save();return rows

def run():
 assert R['status']=='NODE_LINKED';exe=BUILD/'bin/btxd.exe';root=Path('D:/wl'+os.environ['GITHUB_RUN_ID']);assert not root.exists();root.mkdir();R['unit_data']=str(root);R['forced_cleanup_events']=[];R['cases']=[];assert not snapshot('before-runtime');missing=root/'deliberately-absent-modeld.exe';assert not missing.exists();active=[]
 common=['-regtest','-server=1','-disablewallet=1','-listen=0','-listenonion=0','-connect=0','-networkactive=0','-dnsseed=0','-fixedseeds=0','-discover=0','-upnp=0','-natpmp=0','-autoupdate=0','-modellandiscovery=0','-modelfollowpeers=0','-modelbind=0','-printtoconsole=0','-logtimestamps=1','-modelhelper='+str(missing)]
 R['common_node_args']=common;R['unavailable_condition']='Explicit non-existent modelhelper path; supported no-substitute optional-helper path. No real helper launched; no Unix RPC/worker/crash-recovery qualification.'
 def start(label,datadir,extra):
  datadir.mkdir(exist_ok=True);port=port_free();argv=[str(exe),'-datadir='+str(datadir),'-rpcbind=127.0.0.1','-rpcallowip=127.0.0.1','-rpcport='+str(port),*common,*extra];log=E/(label+'-console.log');f=log.open('wb');debug=datadir/'regtest/debug.log';offset=debug.stat().st_size if debug.exists() else 0;proc=subprocess.Popen(argv,stdout=f,stderr=subprocess.STDOUT,cwd=SOURCE);active.append((label,proc,f,datadir));debug=datadir/'regtest/debug.log';row={'label':label,'pid':proc.pid,'args':argv,'rpc_port':port,'data':str(datadir),'expected_helper_exists':missing.exists(),'debug_offset':offset};R['cases'].append(row);s.save();return row,proc,f,port,datadir/'regtest/.cookie'
 def ready(row,proc,port,cookie):
  start=time.monotonic();last='';info=None
  while time.monotonic()-start<90:
   if proc.poll()is not None:raise RuntimeError(row['label']+' exited before RPC: '+str(proc.returncode))
   try:
    if cookie.is_file():info=rpc(port,cookie,'getblockchaininfo');break
   except (OSError,RuntimeError)as ex:last=type(ex).__name__+': '+str(ex)
   time.sleep(.25)
  assert info is not None,(row['label'],'RPC not ready',last);assert info['chain']=='regtest'and info['blocks']==0;net=rpc(port,cookie,'getnetworkinfo');assert net['networkactive']is False and net['connections']==0;assert rpc(port,cookie,'getblockcount')==0
  row.update(rpc_ready=True,startup_seconds=round(time.monotonic()-start,3),blockchain=info,network=net);rows=snapshot(row['label']+'-live');assert {x['ProcessId']for x in rows}=={proc.pid},rows
  samples=[]
  for _ in range(5):
   assert proc.poll()is None;count=rpc(port,cookie,'getblockcount');best=rpc(port,cookie,'getbestblockhash');assert count==0 and best==info['bestblockhash'];samples.append({'blocks':count,'bestblockhash':best});time.sleep(.5)
  row['health_polls']=samples;s.save();return info
 def finish(row,proc,f,port,cookie,natural_expected):
  code=proc.wait(timeout=45);f.close();row['exit']=code;row['cookie_removed']=not cookie.exists();row['rpc_port_closed']=stopped_port(port);assert code==natural_expected and row['cookie_removed']and row['rpc_port_closed'],row
  assert not snapshot(row['label']+'-stopped');src=Path(row['data'])/'regtest/debug.log';assert src.is_file();raw=src.read_bytes()[row['debug_offset']:];(E/(row['label']+'-debug.log')).write_bytes(raw);row['debug_sha256']=sha(E/(row['label']+'-debug.log'));row['debug_scope']='New bytes for this boot only';s.save();return raw.decode(errors='replace')
 try:
  data=root/'optional';row,proc,f,port,cookie=start('optional-first',data,[]);first=ready(row,proc,port,cookie);row['stop_reply']=rpc(port,cookie,'stop');text=finish(row,proc,f,port,cookie,0);assert 'btx-modeld not found next to btxd'in text and 'monetary node continues'in text;assert 'path does not exist; not spawning a substitute'in text;assert not any(x.startswith('-modelnet=')or x.startswith('-modelnetrequired=')for x in row['args']);row['missing_helper_fallback_log']=True
  row,proc,f,port,cookie=start('optional-restart',data,[]);second=ready(row,proc,port,cookie);assert second['bestblockhash']==first['bestblockhash'];row['same_chain_after_restart']=True;row['stop_reply']=rpc(port,cookie,'stop');text=finish(row,proc,f,port,cookie,0);assert 'btx-modeld not found next to btxd'in text and 'monetary node continues'in text;row['missing_helper_fallback_log']=True
  row,proc,f,port,cookie=start('disabled-control',root/'disabled',['-modelnet=0']);ready(row,proc,port,cookie);row['stop_reply']=rpc(port,cookie,'stop');text=finish(row,proc,f,port,cookie,0);assert 'model network disabled (-modelnet=0); monetary node continues'in text;assert 'not spawning a substitute'not in text;row['disabled_control_log']=True
  row,proc,f,port,cookie=start('required-control',root/'required',['-modelnetrequired=1']);text=finish(row,proc,f,port,cookie,1);assert 'Model network required (-modelnetrequired) but helper failed'in text and 'btx-modeld not found next to btxd'in text;row['required_refusal_log']=True;row['expected_refusal']=True
  assert not missing.exists();assert sha(exe)==R['binary_sha256'];assert not snapshot('all-cases-complete');R['status']='LIFECYCLE_PASS'
 finally:
  # Forced cleanup is cumulative evidence and can never be called a pass.
  for label,proc,f,datadir in active:
   if proc.poll()is None:
    R['forced_cleanup_events'].append({'label':label,'pid':proc.pid});z=subprocess.run(['taskkill','/PID',str(proc.pid),'/T','/F'],capture_output=True);(E/(label+'-forced-cleanup.log')).write_bytes(z.stdout+z.stderr);proc.wait(timeout=30)
   if not f.closed:f.close()
   debug=datadir/'regtest/debug.log'
   if debug.is_file():shutil.copyfile(debug,E/(label+'-final-debug.log'))
  rows=snapshot('runtime-final');assert not rows,'Owned child remains';R['runtime_cleanup_confirmed']=True
  if R['forced_cleanup_events']and R.get('status')=='LIFECYCLE_PASS':R['status']='LIFECYCLE_FAILED_FORCED_CLEANUP'
  s.save()
 assert R['status']=='LIFECYCLE_PASS'and not R['forced_cleanup_events'];s.save()

def retain():
 assert not R['process_active']and R.get('cleanup_confirmed',True);assert not R.get('forced_cleanup_events',[]);assert not s.owned_processes();assert R.get('source_catalog',{}).get('head')==TARGET;cat=s.catalog(TARGET,'full-retained');assert cat==R['source_catalog']
 assert all(sha(BUILD/n)==h for n,h in R['original_config'].items()),'Original CMake graph/config changed'
 R['checkpoint_capture']=checkpoint.capture(ROOT,SOURCE,R['profile'],cat,{'status':R['status'],'unit_build_exit':R.get('unit_build_exit'),'unit_exit':R.get('unit_exit'),'unit_built':R['unit_built'],'unit_invoked':R['unit_invoked']});shutil.copyfile(BUILD/'btx-checkpoint.json',E/'full-checkpoint.json');cp=json.loads((BUILD/'btx-checkpoint.json').read_text());R['objects_retained']=sum(k.endswith('.obj')for k in cp['files']);R['checkpoint_key']=hashlib.sha256(json.dumps(R['profile'],sort_keys=True).encode()).hexdigest();s.save()
 with open(os.environ['GITHUB_OUTPUT'],'a')as f:f.write('checkpoint_valid=true\ncheckpoint_key='+R['checkpoint_key']+'\n')

stage=sys.argv[1];failed=False
try:{'prepare':prepare,'build':build,'run':run,'retain':retain}[stage]()
except BaseException as e:
 failed=True;R.setdefault('failures',[]).append({'stage':stage,'error':str(e),'type':type(e).__name__})
 if R['status']in ['FULL_UNIT_BUILDING','FULL_UNIT_RUNNING','COHORT_BUILDING']:R['status']+='_' + ('BUDGET_STOP'if 'stopped:'in str(e)else'ERROR')
 print(type(e).__name__,str(e),flush=True)
finally:s.save();print(json.dumps({k:R.get(k)for k in ['status','planned_steps','unit_built','unit_invoked','unit_build_exit','unit_exit','failures']},indent=2),flush=True)
raise SystemExit(1 if failed else 0)
