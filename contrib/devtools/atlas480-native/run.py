"""Actual packaged Tauri wallet journey; ordinary controls, isolated zero-fund node."""
from pathlib import Path
import base64,hashlib,json,os,secrets,shutil,signal,socket,subprocess,tarfile,time,urllib.request,urllib.parse
from result_handling import classify
ARCHIVE='0caaa7d2d762d51bde262bff0bfb3965f58cc09bb1726b034783608930d3d633'
BASE_ATLAS='a6765f554ecacfd32f80d2fc2f3a4d221fabd0ae18c47dd616ee5113d09d21df'
HEAD='f6b2ac8e606789d69c5d7a4edbf21ff11826b557'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 import ui,pyatspi
 assert os.environ.get('BTX_RUN_ATLAS_WALLET')=='explicit-native-authorisation'
 w=Path(os.environ['GITHUB_WORKSPACE']);out=w/'atlas480-native-records';out.mkdir(exist_ok=True)
 runtime=w/'atlas480-private-runtime';assert not runtime.exists();runtime.mkdir(mode=0o700)
 state={'source':HEAD,'profile':'Ubuntu24 x86_64 X11 virtual desktop; wallet-enabled isolated regtest; keypool=1; Modelnet off; no blocks/funds', 'baseline':{},'candidate':{},'cleanup_signals':[]}
 node=app=None;handles=[];package=candidate=None;before=after_deploy=None;phrase=secrets.token_urlsafe(32);port=None
 def save():(out/'result.json').write_text(json.dumps(state,indent=2)+'\n')
 def snapshot(label):
  assert phrase not in ui.text(),'Credential visible in static UI'
  p=out/(label+'.png');subprocess.run(['scrot',str(p)],check=True,timeout=10)
  return {'file':p.name,'sha256':sha(p)}
 def observe(r,key,value=True):r[key]=value;save();print('OBSERVED',key,flush=True)
 def start(args,label,env):
  f=(out/(label+'.log')).open('wb');handles.append(f)
  return subprocess.Popen(list(map(str,args)),env=env,stdout=f,stderr=subprocess.STDOUT,start_new_session=True)
 def rpc(method,params=None,wallet=None):
  if not (runtime/'node/regtest/.cookie').is_file():raise RuntimeError('Private node cookie not ready')
  cookie=(runtime/'node/regtest/.cookie').read_text().strip()
  path='/wallet/'+urllib.parse.quote(wallet,safe='') if wallet else '/'
  req=urllib.request.Request('http://127.0.0.1:'+str(port)+path,data=json.dumps({'jsonrpc':'2.0','id':'acceptance','method':method,'params':params or []}).encode(),headers={'Authorization':'Basic '+base64.b64encode(cookie.encode()).decode(),'Content-Type':'application/json'})
  try:
   with urllib.request.urlopen(req,timeout=10) as response:r=json.load(response)
  except Exception:raise RuntimeError('Independent node control unavailable') from None
  if r.get('error'):raise RuntimeError('Independent node control returned an RPC error')
  return r['result']
 def wallets():return {'loaded':sorted(rpc('listwallets')),'directory':sorted(x['name'] for x in rpc('listwalletdir')['wallets'])}
 def unchanged(r,key):
  v=wallets();assert v==empty,'Unexpected wallet mutation';observe(r,key)
 def package_hashes(root):return {str(p.relative_to(root)):sha(p) for p in root.rglob('*') if p.is_file()}
 def owned_processes():
  found=[]
  for p in Path('/proc').iterdir():
   if not p.name.isdigit():continue
   try:
    exe=Path(os.readlink(p/'exe'));env=(p/'environ').read_bytes()
    if exe.is_relative_to(runtime) or (b'HOME='+str(runtime).encode()+b'/') in env:found.append(int(p.name))
   except OSError:pass
  return found
 def close_app(r):
  nonlocal app
  subprocess.run(['wmctrl','-c','BTX'],check=True,timeout=5);app.wait(timeout=20)
  assert app.returncode==0;observe(r,'app_clean_exit');app=None
 def connect(root,label):
  nonlocal app
  home=runtime/(label+'-home');home.mkdir(mode=0o700)
  env=dict(os.environ,HOME=str(home),XDG_CONFIG_HOME=str(home/'config'),XDG_DATA_HOME=str(home/'data'),XDG_CACHE_HOME=str(home/'cache'),NO_AT_BRIDGE='0',GTK_MODULES='atk-bridge')
  app=start([root/'bin/btx-atlas'],label+'-atlas',env)
  ui.wait(lambda:'The node is the network.' in ui.text(),45)
  ui.press('Connect to a local BTX node');ui.wait(lambda:'Choose cookie and connect' in ui.text())
  endpoint='127.0.0.1:'+str(port);ui.endpoint(endpoint);ui.press('Choose cookie and connect')
  ui.wait(lambda:"Choose this BTX node's RPC .cookie file" in ui.text());ui.file_path(runtime/'node/regtest/.cookie')
  ui.wait(lambda:'Connect to local node' in ui.text())
  t=ui.text();assert 'Endpoint: '+endpoint in t and 'Chain: regtest' in t and genesis in t
  ui.press('Ok');ui.wait(lambda:'LIVE LOCAL' in ui.text() and '0 blocks' in ui.text(),45)
  observe(state[label],'connected');state[label]['endpoint']=endpoint;state[label]['genesis']=genesis
  ui.press('Wallet');ui.wait(lambda:len(ui.find(lambda n:n.name=='Create' and n.getRoleName() in ('button','push button')))==1)
  ui.press('Create');ui.wait(lambda:bool(ui.find(lambda n:n.name=='New wallet name')))
  observe(state[label],'panel_reached')
 def field(name,value,root=None,secret=False,prefix=False):ui.type_value(ui.entry(name,root,prefix),value,runtime/'typed-secret',secret)
 def operation(title):
  root=None
  def found():
   nonlocal root
   try:root=ui.web_dialog(title);return True
   except TimeoutError:return False
  ui.wait(found);return root
 def approval(r,label):
  root=None
  def found():
   nonlocal root
   try:root=ui.native_dialog('Authorize exact operation');return True
   except TimeoutError:return False
  ui.wait(found);t=ui.text(root)
  assert phrase not in t and '[credential hidden]' in t
  assert 'Chain: regtest' in t and genesis in t and 'Method: createwallet' in t and 'Wallet: node / none' in t and walletname in t
  r[label+'_review_text']=t;r[label+'_image']=snapshot(label);save();return root
 def palette(query):
  subprocess.run(['xdotool','key','--clearmodifiers','ctrl+k'],check=True,timeout=5)
  ui.wait(lambda:bool(ui.find(lambda n:n.name=='Command search' and n.getState().contains(pyatspi.STATE_EDITABLE))))
  field('Command search',query);time.sleep(.5)
 def close_web(root):ui.press('Close',root);time.sleep(.3)
 try:
  assert shutil.disk_usage(w).free>4*1024**3
  archive=w/'candidate-input/btx-linux-gui-candidate.tar.gz';assert sha(archive)==ARCHIVE
  provenance=json.loads((w/'candidate-input/provenance.json').read_text());dest=runtime/'baseline';dest.mkdir()
  with tarfile.open(archive) as tar:
   assert sum(m.size for m in tar.getmembers())<2*1024**3;tar.extractall(dest,filter='data')
  roots=list(dest.rglob('bin/btx-atlas'));assert len(roots)==1;package=roots[0].parent.parent
  before=package_hashes(package);assert before=={n:v['sha256'] for n,v in provenance['candidate_files'].items()}
  assert sha(package/'libexec/btx-atlas.real')==BASE_ATLAS
  build=json.loads((w/'build-input/result.json').read_text());assert build['pass'] is True and build['source']==HEAD
  producer=w/'candidate-binary/btx-atlas';assert sha(producer)==build['binary_sha256']
  candidate=runtime/'candidate';shutil.copytree(package,candidate,symlinks=True)
  shutil.copy2(producer,candidate/'libexec/btx-atlas.real');os.chmod(candidate/'libexec/btx-atlas.real',0o755)
  subprocess.run(['patchelf','--set-rpath','$ORIGIN/../lib',candidate/'libexec/btx-atlas.real'],check=True,timeout=20)
  after_deploy=package_hashes(candidate);assert set(before)==set(after_deploy)
  assert [k for k in before if before[k]!=after_deploy[k]]==['libexec/btx-atlas.real']
  state['binaries']={'baseline':BASE_ATLAS,'candidate_producer':sha(producer),'candidate_deployed':sha(candidate/'libexec/btx-atlas.real'),'node':sha(package/'bin/btxd'),'cli':sha(package/'bin/btx-cli')}
  state['archive_sha256']=ARCHIVE;state['protected_file_count']=len(before)-1
  for label,root in [('baseline',package),('candidate',candidate)]:
   env=dict(os.environ,LD_LIBRARY_PATH=str(root/'lib'))
   probe=subprocess.check_output(['ldd',str(root/'libexec/btx-atlas.real')],text=True,env=env,stderr=subprocess.STDOUT,timeout=30)
   (out/(label+'-ldd.log')).write_text(probe);assert 'not found' not in probe
  with socket.socket() as sock:sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
  (runtime/'node').mkdir(mode=0o700)
  node=start([package/'bin/btxd','-regtest','-datadir='+str(runtime/'node'),'-server=1','-rpcbind=127.0.0.1','-rpcallowip=127.0.0.1','-rpcport='+str(port),'-listen=0','-connect=0','-dnsseed=0','-discover=0','-natpmp=0','-modelnet=0','-dbcache=32','-keypool=1','-printtoconsole=1'],'node',dict(os.environ,HOME=str(runtime)))
  end=time.monotonic()+45
  while True:
   try:chain=rpc('getblockchaininfo');break
   except RuntimeError:
    if node.poll() is not None or time.monotonic()>end:raise
    time.sleep(.5)
  assert chain['chain']=='regtest' and chain['blocks']==0 and rpc('getconnectioncount')==0
  genesis=rpc('getblockhash',[0]);empty=wallets();assert empty=={'loaded':[],'directory':[]}
  connect(package,'baseline');r=state['baseline']
  repeat=ui.find(lambda n:n.name=='Repeat wallet passphrase' and 'password' in n.getRoleName())
  observe(r,'panel_repeat_password',bool(repeat));unchanged(r,'wallets_unchanged');r['panel_image']=snapshot('baseline-panel');close_app(r)
  assert not repeat,'Baseline now implements the candidate oracle; recheck source'
  connect(candidate,'candidate');r=state['candidate']
  assert 'password' in ui.entry('Repeat wallet passphrase').getRoleName();observe(r,'panel_repeat_password')
  assert 'Nobody can recover it.' in ui.text();observe(r,'loss_warning')
  walletname='atlas480-native-'+secrets.token_hex(4);r['wallet_name']=walletname
  field('New wallet name',walletname);field('Wallet passphrase',phrase,secret=True);field('Repeat wallet passphrase',phrase+'mismatch',secret=True)
  ui.press('Create wallet');ui.wait(lambda:'The passphrases do not match' in ui.text());unchanged(r,'panel_mismatch_no_wallet')
  assert not ui.find(lambda n:'Authorize exact operation' in n.name)
  field('Repeat wallet passphrase',phrase,secret=True);ui.press('Create wallet');dialog=operation('Create wallet')
  assert 'password' in ui.entry('Repeat passphrase',dialog,True).getRoleName();observe(r,'operation_repeat_password')
  checks=ui.find(lambda n:n.getRoleName()=='check box' and n.name.startswith('Use exact JSON array/object'),dialog)
  assert len(checks)==1 and not checks[0].getState().contains(pyatspi.STATE_ENABLED)
  assert not ui.find(lambda n:n.name=='Exact JSON RPC parameters',dialog);observe(r,'secret_json_disabled')
  field('Repeat passphrase',phrase+'mismatch',dialog,True,True);ui.press('Prepare for native review',dialog)
  ui.wait(lambda:'passphrase: the two entries do not match' in ui.text(dialog));unchanged(r,'operation_mismatch_no_wallet')
  assert not ui.find(lambda n:'Authorize exact operation' in n.name)
  field('Repeat passphrase',phrase,dialog,True,True);ui.press('Prepare for native review',dialog)
  native=approval(r,'cancel');ui.native_press(native,'cancel');ui.wait(lambda:'CANCELLED' in ui.text(dialog));unchanged(r,'native_cancel_no_wallet')
  # Preparation clears both secrets: refill explicitly, never approve empty defaults.
  field('passphrase',phrase,dialog,True,True);field('Repeat passphrase',phrase,dialog,True,True)
  ui.press('Prepare for native review',dialog);native=approval(r,'approve');ui.native_press(native,'ok')
  # Node mutation alone must not qualify a lost/UNKNOWN native reply as a complete journey.
  web_result=None
  def successful_result():
   nonlocal web_result
   for n in ui.nodes(dialog):
    try:
     if n.getState().contains(pyatspi.STATE_EDITABLE) or 'password' in n.getRoleName():continue
     v=n.queryText();t=v.getText(0,min(v.characterCount,20000)).strip()
     if not t.startswith('{'):continue
     obj=json.loads(t)
     if isinstance(obj,dict) and isinstance(obj.get('result'),dict) and obj['result'].get('name')==walletname:
      web_result=obj;return True
    except Exception:pass
   return False
  ui.wait(successful_result,45)
  assert 'UNKNOWN' not in ui.text(dialog) and 'DO NOT RETRY' not in ui.text(dialog)
  assert phrase not in json.dumps(web_result),'Credential in result display'
  r['create_response']=web_result;observe(r,'web_creation_result')
  ui.wait(lambda:wallets()['loaded']==[walletname],45);observe(r,'native_approved')
  info=rpc('getwalletinfo',wallet=walletname)
  assert info['walletname']==walletname and info['descriptors'] is True and info['private_keys_enabled'] is True
  assert 'unlocked_until' in info and info['unlocked_until']==0
  r['wallet_control']={k:info[k] for k in ('walletname','descriptors','private_keys_enabled','unlocked_until')};observe(r,'encrypted_locked')
  rpc('walletpassphrase',[phrase,10],walletname);assert rpc('getwalletinfo',wallet=walletname)['unlocked_until']>0
  rpc('walletlock',wallet=walletname);assert rpc('getwalletinfo',wallet=walletname)['unlocked_until']==0
  observe(r,'intended_passphrase_control');r['unlock_control_scope']='Independent RPC, not native UI unlock'
  close_web(dialog);ui.press('Wallet');ui.wait(lambda:walletname in ui.text());r['wallet_selection_refresh']='Ordinary Wallet navigation after creation'
  palette('walletpassphrase');ui.press('Unlock wallet temporarily',prefix=True);dialog=operation('Unlock wallet temporarily')
  passwords=ui.find(lambda n:'password' in n.getRoleName(),dialog);assert len(passwords)==1 and not ui.find(lambda n:n.name.startswith('Repeat '),dialog)
  existing_box=ui.unique(lambda n:n.getRoleName()=='check box' and n.name.startswith('Use exact JSON array/object'),dialog)
  assert not existing_box.getState().contains(pyatspi.STATE_ENABLED)
  observe(r,'existing_secret_single_field');close_web(dialog)
  palette('disconnectnode');ui.press('Disconnect peer',prefix=True);dialog=operation('Disconnect peer')
  box=ui.unique(lambda n:n.getRoleName()=='check box' and n.name.startswith('Use exact JSON array/object'),dialog)
  assert box.getState().contains(pyatspi.STATE_ENABLED);ui.activate(box)
  ui.wait(lambda:bool(ui.find(lambda n:n.name=='Exact JSON RPC parameters',dialog)))
  raw=ui.entry('Exact JSON RPC parameters',dialog);field('Exact JSON RPC parameters','{}',dialog)
  ui.activate(box);ui.wait(lambda:not ui.find(lambda n:n.name=='Exact JSON RPC parameters',dialog))
  observe(r,'nonsecret_json_control');close_web(dialog)
  palette('send');subprocess.run(['xdotool','key','--clearmodifiers','Return'],check=True,timeout=5)
  ui.wait(lambda:'Exact transaction composer' in ui.text());assert not ui.find(lambda n:n.getRoleName()=='heading' and n.name=='Send to address')
  observe(r,'send_composer');r['composer_image']=snapshot('send-composer');assert rpc('getblockcount')==0 and rpc('getconnectioncount')==0
  close_app(r)
 except Exception as error:
  state['error']=type(error).__name__+': '+str(error).replace(phrase,'[redacted]')
  try:
   t=ui.text();assert phrase not in t;state['last_ui_text']=t;state['last_ui_metadata']=ui.metadata();state['last_image']=snapshot('last-observation')
  except Exception:state['diagnostic']='Static UI could not be safely captured'
 finally:
  if app and app.poll() is None:
   # Close a test-owned picker/approval normally if an observation failed mid-dialog.
   try:
    if "Choose this BTX node's RPC .cookie file" in ui.text():ui.press('Cancel')
    elif ui.find(lambda n:'Authorize exact operation' in n.name):ui.native_press(ui.native_dialog('Authorize exact operation'),'cancel')
   except Exception:pass
   try:subprocess.run(['wmctrl','-c','BTX'],timeout=5,check=True);app.wait(timeout=15)
   except Exception:pass
  if node and node.poll() is None:
   try:rpc('stop');node.wait(timeout=20);state['node_clean_exit']=node.returncode==0
   except Exception:pass
  for child in (app,node):
   if child and child.poll() is None:
    state['cleanup_signals'].append(child.pid);os.killpg(child.pid,signal.SIGTERM)
    try:child.wait(timeout=5)
    except subprocess.TimeoutExpired:os.killpg(child.pid,signal.SIGKILL);child.wait(timeout=5)
  if package and candidate and before is not None and after_deploy is not None:
   state['protected_files_unchanged']=package_hashes(package)==before and package_hashes(candidate)==after_deploy
  time.sleep(2);state['cleanup_remaining']=owned_processes()
  for handle in handles:handle.close()
  for record in out.iterdir():
   if record.is_file() and record.suffix in ('.log','.json','.txt'):
    data=record.read_bytes()
    if phrase.encode() in data:
     record.write_bytes(data.replace(phrase.encode(),b'[fixture credential redacted]'))
     state['error']='Fixture credential appeared in output; redacted, evidence incomplete'
  if not state['cleanup_remaining']:shutil.rmtree(runtime)
  state['runtime_removed']=not runtime.exists();state.update(classify(state));save()
 return 0 if state['overall']=='PASS' else 1
if __name__=='__main__':raise SystemExit(main())
