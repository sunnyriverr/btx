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
  cases=[('platforms/libqcocoa.dylib',True,None),('styles/libqmacstyle.dylib',True,None),('iconengines/libqsvgicon.dylib',patched,'QtSvg'),('imageformats/libqpdf.dylib',patched,'QtPdf'),('platforminputcontexts/libqtvirtualkeyboardplugin.dylib',patched,'QtVirtualKeyboard')]
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
try:
 assert json.loads((w/'mac-config-records/result.json').read_text())['complete']
 archives=list((w/'package-input').rglob('*.tar.gz'));assert len(archives)==1
 archive=archives[0];assert sha(archive)=='de76a82d1e59fe12bbb8dba9cbc7e7de5167c150acfb754e3d6cb13eb8f2d50d'
 baseline=w/'baseline';baseline.mkdir()
 with tarfile.open(archive) as t:t.extractall(baseline,filter='data')
 root=next(baseline.iterdir());state['before']=plugin_cases(root,'before',False);save()
 stage=w/'staged-bin';stage.mkdir()
 untar_binaries(w/'cmake-binaries',inputs['cmake']['available_executables'],stage)
 untar_binaries(w/'atlas-binaries',{'btx-atlas':inputs['atlas']['executable']},stage)
 protected={p.name:sha(p) for p in stage.iterdir()};assert len(protected)==18
 for relative in ['scripts/release/bundle_qt_gui.py','test/util/package_release_archive_test.py']:
  shutil.copy2(Path(__file__).parent/'candidate'/relative,src/relative)
 changes=run(['git','-C',src,'diff','--name-only'],'candidate-changes')[1].splitlines();assert sorted(changes)==['scripts/release/bundle_qt_gui.py','test/util/package_release_archive_test.py']
 patch=run(['git','-C',src,'diff','--binary'],'candidate-patch')[1];(out/'candidate.patch').write_text(patch)
 run([sys.executable,src/'test/util/package_release_archive_test.py'],'maintained-unit-suite',180)
 args=[sys.executable,src/'scripts/release/package_release_archive.py','--platform-id','macos-arm64-metal','--version','0.34.16','--btxd',stage/'btxd','--btx-cli',stage/'btx-cli','--btx-util',stage/'btx-util','--metal-lib-dir',root/'libexec/metal','--source-root',src,'--require-gui','--require-model-helpers','--output-dir',retained]
 run(args,'candidate-assemble',600)
 candidate=list(retained.glob('*.tar.gz'));assert len(candidate)==1
 run([sys.executable,src/'scripts/release/verify_release_btxd.py','--archive',candidate[0],'--require-model-helpers'],'candidate-stock-check',600)
 extracted=w/'candidate-extracted';extracted.mkdir()
 with tarfile.open(candidate[0]) as t:t.extractall(extracted,filter='data')
 newroot=next(extracted.iterdir());state['after']=plugin_cases(newroot,'after',True)
 assert protected=={p.name:sha(p) for p in stage.iterdir()}
 frameworks=['QtSvg','QtPdf','QtVirtualKeyboardQml','QtVirtualKeyboard']
 assert all((newroot/f'btx-qt.app/Contents/Frameworks/{name}.framework/Versions/A/{name}').is_file() for name in frameworks)
 # Stock checker remains authoritative; no custom dependency exemption.
 state.update(complete=True,producer_binaries_unchanged=True,original_archive_unchanged=sha(archive)=='de76a82d1e59fe12bbb8dba9cbc7e7de5167c150acfb754e3d6cb13eb8f2d50d',candidate_archive_sha256=sha(candidate[0]),candidate_patch_sha256=sha(out/'candidate.patch'),frameworks_present=frameworks,node_started=False,app_launched=False,pr452_included=False)
except Exception as e:state['error']=repr(e);state['traceback']=traceback.format_exc()
finally:save()
sys.exit(0 if state.get('complete') else 1)
