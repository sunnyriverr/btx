"""Assemble verified immutable producers; stop before runtime on any admission failure."""
from pathlib import Path
import os, sys, json, hashlib, tarfile, shutil, subprocess, time, traceback, re
from process_tracker import OwnedProcesses
w=Path(os.environ['GITHUB_WORKSPACE']); out=w/'package-records';out.mkdir(exist_ok=True)
src=w/'product'; retained=w/'package-output';retained.mkdir(exist_ok=True)
inputs=json.loads(Path(__file__).with_name('inputs.json').read_text())
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
def untar_binaries(payload, expected, stage):
 manifest=json.loads((payload/'manifest.json').read_text());assert manifest==expected
 with tarfile.open(payload/'available-executables.tar.gz') as t:
  members=t.getmembers();assert {m.name for m in members}==set(expected)
  for m in members:
   assert m.isfile() and Path(m.name).name==m.name
   dest=stage/m.name;dest.write_bytes(t.extractfile(m).read());dest.chmod(expected[m.name]['mode']);assert sha(dest)==expected[m.name]['sha256']

def plugin_cases(root,label,patched):
 app=root/'btx-qt.app';probe=app/'Contents/MacOS/plugin-admission-probe'
 before={str(p.relative_to(root)):sha(p) for p in root.rglob('*') if p.is_file() and not p.is_symlink()}
 run(['xcrun','clang++','-std=c++17','-F/opt/homebrew/opt/qtbase/lib','-framework','QtCore','-Wl,-rpath,@executable_path/../Frameworks',Path(__file__).with_name('probe.cpp'),'-o',probe],label+'-compile-probe',120)
 linked=run(['otool','-L',probe],label+'-original-link')[1]
 core=[line.strip().split(' (')[0] for line in linked.splitlines()[1:] if 'QtCore.framework/' in line];assert len(core)==1
 run(['install_name_tool','-change',core[0],'@executable_path/../Frameworks/QtCore.framework/Versions/A/QtCore',probe],label+'-bind-probe')
 bound=run(['otool','-L',probe],label+'-bound-link')[1];assert '/opt/homebrew/' not in bound
 run(['codesign','--force','--sign','-',probe],label+'-sign-probe')
 env['DYLD_PRINT_LIBRARIES']='1';results=[]
 try:
  cases=[(str(x.relative_to(app/'Contents/PlugIns')),True,None) for x in sorted((app/'Contents/PlugIns').rglob('*.dylib'))]
  assert len(cases)>=20
  for i,(name,expected,missing) in enumerate(cases):
   status,text=run([probe,app/'Contents/PlugIns'/name],label+'-plugin-'+str(i),20,False)
   lines=[x for x in text.splitlines() if x.startswith('{')];assert len(lines)==1
   result=json.loads(lines[0]);assert result['loaded']==expected,(name,result)
   if not expected:assert missing in result['error'] and 'not loaded' in result['error'].lower()
   ambient=[x for x in text.splitlines() if x.startswith('dyld[') and ('/opt/homebrew/' in x or '/usr/local/opt/' in x)];assert not ambient,(name,ambient)
   results.append({'plugin':name,'loaded':result['loaded'],'exit':status,'error':result['error']})
 finally:
  env.pop('DYLD_PRINT_LIBRARIES',None);probe.unlink()
 after={str(p.relative_to(root)):sha(p) for p in root.rglob('*') if p.is_file() and not p.is_symlink()};assert before==after
 return {'cases':results,'package_bytes_unchanged':True,'files':len(before),'ambient_homebrew_loads':False}
def extract(archive,where):
 where.mkdir()
 with tarfile.open(archive) as t:t.extractall(where,filter='data')
 roots=list(where.iterdir());assert len(roots)==1;return roots[0]
def inspect_images(root):
 images=[]
 for p in root.rglob('*'):
  if not p.is_file() or p.is_symlink():continue
  with p.open('rb') as f:head=f.read(4)
  if head!=b'\xcf\xfa\xed\xfe':continue
  index=str(len(images));arch=run(['lipo','-archs',p],'arch-'+index)[1].strip();assert arch=='arm64'
  run(['codesign','--verify','--strict',p],'signature-'+index)
  loads=run(['otool','-L',p],'dependencies-'+index)[1];assert '/opt/homebrew/' not in loads and '/usr/local/opt/' not in loads
  lc=run(['otool','-l',p],'loadcommands-'+index)[1]
  floors=re.findall(r'\bminos (\d+(?:\.\d+)+)',lc);assert floors
  for floor in floors:assert tuple(map(int,floor.split('.')[:2]))<=(15,8)
  images.append({'path':str(p.relative_to(root)),'sha256':sha(p),'architecture':arch,'minimum_os':floors})
 assert len(images)>=85;state['images']=images;save()
def lifecycle(root,label,expected):
 folder=out/label;folder.mkdir()
 code,text=run([sys.executable,Path(__file__).with_name('case.py'),root,folder,label],label+'-case',300,False)
 result=json.loads((folder/'result.json').read_text());assert result['runtime_removed'] and not result['cleanup_remaining']
 if expected:assert code==0 and result['passed'] and result['guard_contract_pass']
 else:
  assert code!=0 and len(result['boots'])==2
  assert all(not b['guard']['ready'] and all(x['pass'] for x in b['health']) for b in result['boots'])
  assert 'packaged guard actually answers' in result['error']
 return {'exit':code,'passed':result['passed'],'guard_contract_pass':result.get('guard_contract_pass'),'boots':len(result['boots']),'runtime_removed':result['runtime_removed']}
def gui(root,name):
 folder=w/('gui-'+name);folder.mkdir();home=folder/'home';home.mkdir();data=folder/'data';data.mkdir()
 ge=dict(env,HOME=str(home),TMPDIR=str(folder),DYLD_PRINT_LIBRARIES='1')
 if name=='atlas':args=[root/'bin/btx-atlas']
 else:args=[root/'bin/btx-qt','-regtest','-datadir='+str(data),'-disablewallet','-server=0','-listen=0','-networkactive=0','-connect=0','-dnsseed=0','-discover=0','-natpmp=0','-modelbind=off','-modelhost=0','-modelseed=off','-modelfollowpeers=0','-modellandiscovery=0','-modelstorage=16MiB']
 log=out/(name+'-gui.log');result={'window_seen':False,'screenshot':False}
 with log.open('w') as f:
  proc=subprocess.Popen(list(map(str,args)),env=ge,cwd=folder,stdout=f,stderr=subprocess.STDOUT,start_new_session=True);tracked=OwnedProcesses(proc)
  try:
   deadline=time.monotonic()+45
   while time.monotonic()<deadline:
    tracked.update();assert proc.poll() is None,(name,proc.returncode)
    _,text=run([w/'window-probe',str(proc.pid)],name+'-window',5)
    windows=json.loads(text)
    visible=[x for x in windows if x.get('kCGWindowLayer')==0 and x.get('kCGWindowBounds',{}).get('Width',0)>300]
    if visible:
     result.update(window_seen=True,windows=visible)
     time.sleep(3)
     code,_=run(['screencapture','-x','-l',str(visible[0]['kCGWindowNumber']),out/(name+'-window.png')],name+'-capture',10,False)
     result['screenshot']=code==0 and (out/(name+'-window.png')).is_file();break
    time.sleep(1)
  except Exception as e:result['error']=repr(e)
  finally:result['cleanup']=tracked.stop();assert not result['cleanup']['processes']
 text=log.read_text();result['ambient_loads']=[x for x in text.splitlines() if x.startswith('dyld[') and ('/opt/homebrew/' in x or '/usr/local/opt/' in x)]
 assert not result['ambient_loads'];shutil.rmtree(folder);return result
try:
 assert json.loads((w/'mac-config-records/result.json').read_text())['complete']
 admission=json.loads(Path(__file__).with_name('admission.json').read_text())
 old=list((w/'without-guard-input').rglob('*.tar.gz'));new=list((w/'combined-input').rglob('*.tar.gz'));assert len(old)==len(new)==1
 assert sha(old[0])=='1f38442ac8d7253abdad32ed5aa5d76567d81f9d617517093d55bee903ce3b53'
 baseline=extract(old[0],w/'baseline');root=extract(new[0],w/'combined')
 for row in admission['images']:assert sha(root/row['path'])==row['sha256']
 assert (root/'libexec/btx-guardd').samefile(root/'libexec/btx-guardd.real') and not (root/'libexec/btx-guardd').is_symlink()
 state.update(images=admission['images'],all_plugin_loads=admission['all_plugin_loads'],archive_checks_reused_from=42538530491,combined_archive_sha256=sha(new[0]))
 # Same owned physical directory through its /tmp alias isolates path policy.
 physical=Path('/tmp').resolve()/('btx-guard-path-'+os.environ['GITHUB_RUN_ID']);physical.mkdir(mode=0o700)
 alias=Path('/tmp')/physical.name
 try:
  path_checks=[]
  for label,folder in [('alias',alias/'security'),('physical',physical/'security')]:
   result=subprocess.run([str(root/'libexec/btx-guardd'),'--stdio','--security-dir',str(folder)],input='PING\n',capture_output=True,text=True,timeout=10,env={'LANG':'C','PATH':'/usr/bin:/bin'})
   path_checks.append({'path':str(folder),'exit':result.returncode,'stdout':result.stdout,'stderr':result.stderr})
  assert path_checks[0]['exit']!=0 and path_checks[1]['exit']==0 and 'READY BTX_GUARD/1' in path_checks[1]['stdout'],path_checks
  state['guard_path_control']=path_checks
 finally:shutil.rmtree(physical)
 state['baseline_guard']=lifecycle(baseline,'without452physical',False);save()
 state['combined_lifecycle']=lifecycle(root,'with452physical',True);save()
 run(['xcrun','clang','-fobjc-arc',Path(__file__).with_name('window.m'),'-framework','Foundation','-framework','CoreGraphics','-o',w/'window-probe'],'compile-window-probe',90)
 before={str(p.relative_to(root)):sha(p) for p in root.rglob('*') if p.is_file()}
 state['gui']={name:gui(root,name) for name in ['atlas','qt']}
 after={str(p.relative_to(root)):sha(p) for p in root.rglob('*') if p.is_file()};assert before==after
 state.update(complete=True,package_bytes_unchanged=True,producer_binaries_unchanged=True,original_archives_unchanged=True,pr452_included=True,visual_review_pending=True)
except Exception as e:state['error']=repr(e);state['traceback']=traceback.format_exc()
finally:save()
sys.exit(0 if state.get('complete') else 1)
