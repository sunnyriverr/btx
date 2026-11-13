"""Assemble verified immutable producers; stop before runtime on any admission failure."""
from pathlib import Path
import os, sys, json, hashlib, tarfile, shutil, subprocess, time, traceback, re
from process_tracker import OwnedProcesses
w=Path(os.environ['GITHUB_WORKSPACE']); out=w/'package-records';out.mkdir(exist_ok=True)
src=w/'product'; retained=w/'package-output';retained.mkdir(exist_ok=True)
inputs=json.loads(Path(__file__).with_name('inputs.json').read_text())
state={'node_started':False,'app_launched':False,'package_acceptance':False,'source':'c6f9678dd225572528d06c456c16eb4c78bc637c','commands':[]}
env=dict(os.environ,TMPDIR=str(w/'isolated-tmp'),BTX_OPENSSL='/opt/homebrew/opt/openssl@3/bin/openssl',DEVELOPER_DIR='/Applications/Xcode_16.4.app/Contents/Developer')
Path(env['TMPDIR']).mkdir(exist_ok=True)
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
def audit(root,label):
 images={};magic={b'\xcf\xfa\xed\xfe',b'\xfe\xed\xfa\xcf',b'\xca\xfe\xba\xbe'}
 for p in root.rglob('*'):
  if not p.is_file() or p.is_symlink():continue
  with p.open('rb') as f:head=f.read(4)
  if head not in magic:continue
  _,arch=run(['lipo','-archs',p],label+'-arch-'+str(len(images)));assert arch.strip()=='arm64',(p,arch)
  _,loads=run(['otool','-l',p],label+'-loads-'+str(len(images)))
  run(['codesign','--verify','--strict',p],label+'-sign-'+str(len(images)))
  commands=re.split(r'Load command \d+\n',loads)[1:];deps=[];rpaths=[];floors=[]
  for c in commands:
   typ=re.search(r'\bcmd (\S+)',c)
   if not typ:continue
   typ=typ[1]
   if typ in ['LC_LOAD_DYLIB','LC_LOAD_WEAK_DYLIB','LC_REEXPORT_DYLIB','LC_LOAD_UPWARD_DYLIB']:
    deps.append(re.search(r'\bname (.+) \(offset',c)[1])
   if typ=='LC_RPATH':rpaths.append(re.search(r'\bpath (.+) \(offset',c)[1])
   if typ in ['LC_BUILD_VERSION','LC_VERSION_MIN_MACOSX']:
    v=re.search(r'\b(?:minos|version) (\d+(?:\.\d+)+)',c)
    if v:floors.append(v[1])
  images[str(p.resolve())]={'dependencies':deps,'rpaths':rpaths,'minimum_os':floors,'sha256':sha(p)}
 assert len(images)>=18,'Missing expected Mach-O inventory'
 failures=[];resolved=[]
 def expand(s,loader,exe):return s.replace('@loader_path',str(loader.parent)).replace('@executable_path',str(exe.parent))
 def walk(path,exe,inherited,seen):
  path=path.resolve();key=str(path)
  if key in seen:return
  seen=seen|{key};meta=images.get(key);assert meta is not None,('Dependency not audited',path)
  rp=list(dict.fromkeys([expand(x,path,exe) for x in meta['rpaths']]+inherited))
  for dep in meta['dependencies']:
   if dep.startswith(('/System/Library/','/usr/lib/')):continue
   if dep.startswith('@rpath/'):
    found={Path(x,dep.removeprefix('@rpath/')).resolve() for x in rp if '@' not in x and Path(x,dep.removeprefix('@rpath/')).exists()}
   else:
    dest=Path(expand(dep,path,exe));found={dest.resolve()} if dest.exists() else set()
   if len(found)!=1 or not next(iter(found)).is_relative_to(root.resolve()):failures.append({'image':key,'dependency':dep,'matches':list(map(str,found))});continue
   dest=next(iter(found));resolved.append({'image':key,'dependency':dep,'resolved':str(dest)});walk(dest,exe,rp,seen)
 qt=root/'btx-qt.app/Contents/MacOS/btx-qt'
 for name in images:
  path=Path(name);exe=qt if path.is_relative_to(root/'btx-qt.app') else path
  inherited=[expand(x,exe,exe) for x in images.get(str(exe.resolve()),{}).get('rpaths',[])]
  walk(path,exe,inherited,set())
 (out/(label+'-dependency-map.json')).write_text(json.dumps({'images':images,'resolved':resolved,'failures':failures},indent=2));assert not failures,failures[:8]
 return {'images':len(images),'minimum_os_floors':sorted({v for m in images.values() for v in m['minimum_os']})}
def package(source,label):
 output=retained/label;output.mkdir()
 args=[sys.executable,source/'scripts/release/package_release_archive.py','--platform-id','macos-arm64-metal','--version','0.34.16','--btxd',stage/'btxd','--btx-cli',stage/'btx-cli','--btx-util',stage/'btx-util','--metal-lib-dir',metal,'--source-root',source,'--require-gui','--require-model-helpers','--output-dir',output]
 code,text=run(args,label+'-assemble',600,False)
 result={'assembly_exit':code,'source':str(source)};state[label]=result;save()
 if code:return result
 archives=list(output.glob('*.tar.gz'));assert len(archives)==1
 archive=archives[0];result['archive_sha256']=sha(archive)
 run([sys.executable,source/'scripts/release/verify_release_btxd.py','--archive',archive,'--require-model-helpers','--no-launch'],label+'-stock-check',600)
 extract=w/('extracted-'+label);extract.mkdir()
 with tarfile.open(archive) as t:t.extractall(extract,filter='data')
 roots=list(extract.iterdir());assert len(roots)==1;root=roots[0]
 assert all((root/'bin'/name).is_file() for name in expected)
 assert len(list((root/'libexec/metal').glob('*.metallib')))==len(metal_files)
 result['macho_audit']=audit(root,label)
 result['guard_sibling']=(root/'libexec/btx-guardd').is_file() and not (root/'libexec/btx-guardd').is_symlink()
 result['static_admission_pass']=result['guard_sibling'];save();return result
try:
 assert json.loads((w/'mac-config-records/result.json').read_text())['complete']
 run(['git','-C',src,'rev-parse','HEAD'],'source');assert (out/'source.log').read_text().strip()==state['source']
 stage=w/'staged-bin';stage.mkdir();expected=inputs['cmake']['available_executables']|{'btx-atlas':inputs['atlas']['executable']}
 cmake_bins=w/'producer-binaries/cmake-chunk-binaries'
 atlas_bins=w/'producer-binaries/cargo-chunk-binaries'
 assert sha(cmake_bins/'available-executables.tar.gz')==inputs['cmake']['binary_artifact_sha256']
 assert sha(atlas_bins/'available-executables.tar.gz')==inputs['atlas']['binary_artifact_sha256']
 untar_binaries(cmake_bins,inputs['cmake']['available_executables'],stage)
 untar_binaries(atlas_bins,{'btx-atlas':inputs['atlas']['executable']},stage)
 assert len(expected)==18;state['producer_hashes_verified']=expected;save()
 payload=w/'producer-checkpoints/cmake-chunk-checkpoint/after';receipt=json.loads((payload/'receipt.json').read_text());invfile=payload/'inventory.json';archive=payload/'checkpoint.tar.gz'
 assert receipt==inputs['cmake']['checkpoint'];assert sha(invfile)==receipt['inventory_sha256'] and sha(archive)==receipt['sha256']
 inv=json.loads(invfile.read_text());metal=w/'staged-metal';metal.mkdir();metal_files={}
 with tarfile.open(archive) as t:
  for m in t.getmembers():
   if m.name.endswith('.metallib'):
    assert m.isfile() and m.name in inv
    blob=t.extractfile(m).read();digest=hashlib.sha256(blob).hexdigest();assert digest==inv[m.name]['sha256']
    name=Path(m.name).name;assert name not in metal_files or metal_files[name]==digest
    (metal/name).write_bytes(blob);metal_files[name]=digest
 assert len(metal_files)==7;state['metal']=metal_files;save()
 fixture=Path(__file__).resolve().parent
 overlay=fixture/'bundle-overlay.py'
 gate=fixture/'archive-gate.py'
 for f, pin in ((overlay, 'overlay-blob.txt'), (gate, 'gate-blob.txt')):
  _,blob=run(['git','hash-object',f],pin)
  assert blob.strip()==(fixture/pin).read_text().strip()
 config=json.loads((w/'mac-config-records/result.json').read_text())
 deploy=config['packaging_tools']['macdeployqt']
 deploy_tool=Path(deploy['path'])
 assert sha(deploy_tool)==deploy['sha256']
 env['PATH']=str(deploy_tool.parent)+os.pathsep+env['PATH']
 state['macdeployqt']=deploy
 baseline=package(src,'baseline')
 assert baseline.get('static_admission_pass'), baseline
 before_archive=Path(baseline['archive_path'])
 gate_args=[sys.executable,gate,'--require-model-helpers','--no-launch','--archive']
 before_code,before_text=run([*gate_args,before_archive],'baseline-608',600,False)
 assert before_code==1 and 'libjpeg.8.dylib: non-portable macOS runpath:' in before_text,before_text
 bundler=src/'scripts/release/bundle_qt_gui.py'
 _,original=run(['git','hash-object',bundler],'original-bundler')
 assert original.strip()=='aaf552f2e5df700abfae3243b1c330d3919ac473'
 shutil.copyfile(overlay,bundler)
 candidate=package(src,'candidate')
 assert candidate.get('static_admission_pass'), candidate
 archive=Path(candidate['archive_path'])
 digest=candidate['archive_sha256']
 assert sha(archive)==digest
 run([*gate_args,archive],'candidate-608',600)
 root=w/'extracted-candidate/btx-0.34.16'
 run(['codesign','--verify','--deep','--strict','--verbose=2',root/'btx-qt.app'],'app-signature')
 probe=w/'window-probe'
 run(['xcrun','clang','-fobjc-arc',fixture/'window.m','-framework','Foundation','-framework','CoreGraphics','-o',probe],'compile-window-probe')
 run([sys.executable,fixture/'launch.py',root,probe,out],'qt-launch',100)
 assert sha(archive)==digest
 state['candidate_gate_signature_launch_sha256']=digest
 state['finished']=True
 state['complete']=True
except Exception as e:state['error']=repr(e);state['traceback']=traceback.format_exc()
finally:save()
sys.exit(0 if state.get('complete') else 1)
