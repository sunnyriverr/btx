"""Assemble verified immutable producers; stop before runtime on any admission failure."""
from pathlib import Path
import os, sys, json, hashlib, tarfile, shutil, subprocess, time, traceback, re
from process_tracker import OwnedProcesses
w=Path(os.environ['GITHUB_WORKSPACE']); out=w/'package-records';out.mkdir(exist_ok=True)
src=w/'product'; retained=w/'package-output';retained.mkdir(exist_ok=True)
inputs={}
state={'node_started':False,'app_launched':False,'package_acceptance':False,'source':'36ab43008cac48aa5c8410e4b70d90a249196a33','commands':[]}
env=dict(os.environ,HOME=str(w/'isolated-home'),TMPDIR=str(w/'isolated-tmp'),BTX_OPENSSL='/opt/homebrew/opt/openssl@3/bin/openssl',DEVELOPER_DIR='/Applications/Xcode_16.4.app/Contents/Developer')
for k in ['HOME','TMPDIR']:Path(env[k]).mkdir(exist_ok=True)
for k in list(env):
 if k.startswith(('BTX_','BITCOIN_','DYLD_')) and k!='BTX_OPENSSL':env.pop(k)
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def save():(out/'result.json').write_text(json.dumps(state,indent=2)+'\n')
def run(args,label,seconds=120,check=True):
 with (out/(label+'.log')).open('w') as f:
  p=subprocess.Popen(list(map(str,args)),env=env,stdout=f,stderr=subprocess.STDOUT,start_new_session=True);t=OwnedProcesses(p);began=time.monotonic()
  try:
   while p.poll() is None:
    obs=t.update();assert obs['rss_bytes']<5.5*1024**3 and shutil.disk_usage(w).free>10*1024**3
    assert time.monotonic()-began<seconds,label+' timeout'
    time.sleep(.2)
  finally:assert not t.stop()['processes']
 state['commands'].append({'label':label,'exit':p.returncode});save()
 text=(out/(label+'.log')).read_text()
 if check:assert p.returncode==0,(label,text[-1500:])
 return p.returncode,text
def gui(root,name):
 folder=w/('gui-'+name);folder.mkdir();home=folder/'home';home.mkdir();data=folder/'data';data.mkdir()
 ge=dict(env,HOME=str(home),TMPDIR=str(folder),DYLD_PRINT_LIBRARIES='1')
 if name=='atlas':args=[root/'bin/btx-atlas']
 else:args=[root/'bin/btx-qt','-splash=0','-regtest','-datadir='+str(data),'-disablewallet','-server=0','-listen=0','-networkactive=0','-connect=0','-dnsseed=0','-discover=0','-natpmp=0','-modelbind=off','-modelhost=0','-modelseed=off','-modelfollowpeers=0','-modellandiscovery=0','-modelstorage=16MiB']
 log=out/(name+'-gui.log');result={'window_seen':False,'screenshot':False}
 with log.open('w') as f:
  proc=subprocess.Popen(list(map(str,args)),env=ge,cwd=folder,stdout=f,stderr=subprocess.STDOUT,start_new_session=True);tracked=OwnedProcesses(proc)
  try:
   deadline=time.monotonic()+45
   while time.monotonic()<deadline:
    tracked.update();assert proc.poll() is None,(name,proc.returncode)
    _,text=run([w/'window-probe',str(proc.pid)],name+'-window',5)
    windows=json.loads(text)
    visible=[x for x in windows if x.get('kCGWindowLayer')==0 and x.get('kCGWindowBounds',{}).get('Width',0)>600 and x.get('kCGWindowBounds',{}).get('Height',0)>400]
    if visible:
     result.update(window_seen=True,windows=visible)
     time.sleep(3)
     code,_=run(['screencapture','-x','-l',str(visible[0]['kCGWindowNumber']),out/(name+'-window.png')],name+'-capture',10,False)
     result['screenshot']=code==0 and (out/(name+'-window.png')).is_file()
     if result['screenshot']:break
    time.sleep(1)
  except Exception as e:result['error']=repr(e)
  finally:result['cleanup']=tracked.stop();assert not result['cleanup']['processes']
 text=log.read_text();result['ambient_loads']=[x for x in text.splitlines() if x.startswith('dyld[') and ('/opt/homebrew/' in x or '/usr/local/opt/' in x)]
 assert not result['ambient_loads'];shutil.rmtree(folder);return result
try:
 assert os.environ.get('ImageVersion')=='20261104.0514.1'
 archives=list((w/'combined-input').rglob('*.tar.gz'));assert len(archives)==1
 archive=archives[0];assert sha(archive)=='06f13142517636345f82ab6e2121e305acc6d0b584a046327856afd7fa0c7bc7'
 extract=w/'package';extract.mkdir()
 with tarfile.open(archive) as t:t.extractall(extract,filter='data')
 root=next(extract.iterdir());before={str(p.relative_to(root)):sha(p) for p in root.rglob('*') if p.is_file()}
 run(['xcrun','clang','-fobjc-arc',Path(__file__).with_name('window.m'),'-framework','Foundation','-framework','CoreGraphics','-o',w/'window-probe'],'compile-window-probe',90)
 state['gui']={'qt':gui(root,'qt')}
 after={str(p.relative_to(root)):sha(p) for p in root.rglob('*') if p.is_file()};assert before==after
 state.update(complete=True,archive_sha256=sha(archive),package_bytes_unchanged=True,visual_review_pending=True)
except Exception as e:state['error']=repr(e);state['traceback']=traceback.format_exc()
finally:save()
sys.exit(0 if state.get('complete') else 1)
