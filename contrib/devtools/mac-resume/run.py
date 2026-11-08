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
try:
 assert json.loads((w/'mac-config-records/result.json').read_text())['complete']
 candidates=list((w/'package-input').rglob('*.tar.gz'));assert len(candidates)==1
 archive=candidates[0];assert sha(archive)=='de76a82d1e59fe12bbb8dba9cbc7e7de5167c150acfb754e3d6cb13eb8f2d50d'
 extract=w/'original-package';extract.mkdir()
 with tarfile.open(archive) as t:t.extractall(extract,filter='data')
 root=next(extract.iterdir());state['archive_sha256']=sha(archive)
 before={str(p.relative_to(root)):sha(p) for p in root.rglob('*') if p.is_file() and not p.is_symlink()}
 app=root/'btx-qt.app';probe=app/'Contents/MacOS/plugin-admission-probe'
 code=Path(__file__).with_name('probe.cpp')
 run(['xcrun','clang++','-std=c++17','-F/opt/homebrew/opt/qtbase/lib','-framework','QtCore','-Wl,-rpath,@executable_path/../Frameworks',code,'-o',probe],'compile-probe',120)
 _,linked=run(['otool','-L',probe],'probe-original-loads')
 core=[line.strip().split(' (')[0] for line in linked.splitlines()[1:] if 'QtCore.framework/' in line];assert len(core)==1
 run(['install_name_tool','-change',core[0],'@executable_path/../Frameworks/QtCore.framework/Versions/A/QtCore',probe],'bind-probe-to-bundle')
 _,bound=run(['otool','-L',probe],'probe-bound-loads');assert '/opt/homebrew/' not in bound and '@executable_path/../Frameworks/QtCore.framework/Versions/A/QtCore' in bound
 run(['codesign','--force','--sign','-',probe],'sign-probe')
 run(['otool','-L',probe],'probe-loads');run(['otool','-l',probe],'probe-load-commands')
 env['DYLD_PRINT_LIBRARIES']='1'
 cases=[('platforms/libqcocoa.dylib',True,None),('styles/libqmacstyle.dylib',True,None),('iconengines/libqsvgicon.dylib',False,'QtSvg'),('imageformats/libqpdf.dylib',False,'QtPdf'),('platforminputcontexts/libqtvirtualkeyboardplugin.dylib',False,'QtVirtualKeyboard')]
 results=[]
 for index,(name,expected,missing) in enumerate(cases):
  status,text=run([probe,app/'Contents/PlugIns'/name],'plugin-'+str(index),20,False)
  lines=[line for line in text.splitlines() if line.startswith('{')];assert len(lines)==1,(name,text[-1000:])
  value=json.loads(lines[0]);assert value['loaded']==expected,(name,value)
  if not expected:assert missing in value['error'] and 'not loaded' in value['error'].lower(),value
  loaded=[line for line in text.splitlines() if line.startswith('dyld[')]
  ambient=[line for line in loaded if '/opt/homebrew/' in line or '/usr/local/opt/' in line];assert not ambient,(name,ambient)
  results.append({'plugin':name,'expected_load':expected,'exit':status,'result':value,'actual_loaded_images':loaded})
 probe.unlink()
 after={str(p.relative_to(root)):sha(p) for p in root.rglob('*') if p.is_file() and not p.is_symlink()};assert before==after
 state.update(complete=True,plugin_results=results,package_bytes_unchanged=True,original_file_count=len(before),archive_unchanged=sha(archive)==state['archive_sha256'],scope='QCoreApplication/QPluginLoader dependency probe added temporarily in the extracted executable directory; no actual app window, node or user workflow execution. No package repair.')
except Exception as e:state['error']=repr(e);state['traceback']=traceback.format_exc()
finally:save()
sys.exit(0 if state.get('complete') else 1)
