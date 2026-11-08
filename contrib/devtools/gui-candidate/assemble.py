"""Construct a separate GUI candidate; protected monetary/model-plane bytes stay unchanged."""
from pathlib import Path
import os,sys,subprocess,hashlib,json,tarfile,urllib.request,shutil,importlib.util
w=Path(os.environ['GITHUB_WORKSPACE']);out=w/'candidate-results';out.mkdir();dst=w/'candidate-output';dst.mkdir();runtime=w/'candidate-runtime';runtime.mkdir()
s={'fixture':os.environ['GITHUB_SHA'],'source':'ff5f3f04ea11f044594987fc6be043ff68b136ad','reconstructed_candidate':True,'release_qualified':False}
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
def files(root):
 return {str(p.relative_to(root)):({'link':os.readlink(p)} if p.is_symlink() else {'sha256':sha(p),'mode':p.stat().st_mode&0o777}) for p in root.rglob('*') if p.is_file() or p.is_symlink()}
def load(name,path):
 spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);sys.modules[name]=m;spec.loader.exec_module(m);return m
def run(args,label,limit=180):
 with (out/(label+'.log')).open('wb') as f:r=subprocess.run(list(map(str,args)),stdout=f,stderr=subprocess.STDOUT,timeout=limit)
 return r.returncode
try:
 assert shutil.disk_usage(w).free>5*1024**3
 old=runtime/'original.tar.gz'
 with urllib.request.urlopen('https://github.com/btxchain/btx/releases/download/v0.34.16/btx-0.34.16-x86_64-linux-gnu.tar.gz',timeout=60) as src,old.open('wb') as f:shutil.copyfileobj(src,f)
 assert sha(old)=='796b9edd064272b1f443cf3e08646565936183f9f1e15339cad60e84e1014b32' and old.stat().st_size==158893566
 s['original_archive_sha256']=sha(old)
 with tarfile.open(old) as t:
  assert sum(m.size for m in t.getmembers())<2*1024**3;t.extractall(runtime/'package',filter='data')
 root=runtime/'package/btx-0.34.16';assert root.is_dir();before=files(root)
 qt=w/'retained-qt/btx-qt';atlas=w/'retained-atlas/btx-atlas'
 assert sha(qt)=='a68a0af76eb1332b4646f8f7dfdff4474cced1076d5511c3e5567283c0c3d5a9'
 assert sha(atlas)=='720a718afbe1d8e282345057acc7ff22af5121de1f004b57f644565cbb0ad8be'
 s['input_binaries']={'qt':sha(qt),'atlas':sha(atlas)}
 checker=Path(__file__).with_name('verify_release_btxd.py');m=load('candidate_archive_checker',checker)
 elf={}
 for p in root.rglob('*'):
  if p.is_file() and not p.is_symlink():
   with p.open('rb') as f:magic=f.read(4)
   if magic==b'\x7fELF':elf[str(p.relative_to(root))]=m.elf_dynamic_info(p)
 libs={str(p.relative_to(root)):p for p in (root/'lib').rglob('*') if p.is_file() and str(p.relative_to(root)) in elf}
 byname={}
 for n,p in libs.items():byname.setdefault(p.name,[]).append(n)
 def closure(roots):
  seen=set();pending=list(roots)
  while pending:
   n=pending.pop()
   if n in seen:continue
   seen.add(n)
   if n in elf:
    for need in elf[n].needed:pending.extend(byname.get(need,[]))
  return seen
 gui={'libexec/btx-qt.real','libexec/btx-atlas.real'}
 protected_roots=[n for n in elf if not n.startswith('lib/') and n not in gui]
 protected_libs=closure(protected_roots)&set(libs)
 gui_roots=list(gui)+[n for n in libs if Path(n).name.startswith(('libQt5','libQt6')) or n.endswith('libqxcb.so')]
 old_gui=closure(gui_roots)&set(libs)
 removable=old_gui-protected_libs
 s['dependency_graph']={'protected_roots':protected_roots,'protected_libraries':sorted(protected_libs),'gui_only_removed':sorted(removable),'needed':{n:i.needed for n,i in elf.items()}}
 for name in sorted(removable): (root/name).unlink()
 # Stage the unmodified upstream Qt bundler away from the protected shared library set.
 stage=runtime/'qt-stage';(stage/'libexec').mkdir(parents=True)
 stageqt=stage/'libexec/btx-qt.real';shutil.copy2(qt,stageqt);stageqt.chmod(0o755)
 bundler=load('candidate_qt_bundler',Path(__file__).with_name('bundle_qt_gui.py'))
 bundler.bundle_linux_qt(stageqt,stage/'lib')
 assert not any(x.name.startswith(('libssl.so','libcrypto.so')) for x in (stage/'lib').rglob('*')),'Unexpected GUI OpenSSL copy; inspect before widening scope'
 shutil.copytree(stage/'lib',root/'lib/qt-private')
 shutil.copy2(stageqt,root/'libexec/btx-qt.real');shutil.copy2(atlas,root/'libexec/btx-atlas.real');(root/'libexec/btx-atlas.real').chmod(0o755)
 assert run(['patchelf','--set-rpath','$ORIGIN/../lib/qt-private:$ORIGIN/../lib',root/'libexec/btx-qt.real'],'qt-private-rpath')==0
 assert run(['patchelf','--set-rpath','$ORIGIN/../lib',root/'libexec/btx-atlas.real'],'atlas-rpath')==0
 wrapper=root/'bin/btx-qt';text=wrapper.read_text();oldblock='''if [ -e "$LIB_DIR/libssl.so.3" ]; then
  LD_LIBRARY_PATH="$LIB_DIR${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
  export LD_LIBRARY_PATH
fi''';assert text.count(oldblock)==1
 text=text.replace(oldblock,'''LD_LIBRARY_PATH="$SELF_DIR/../lib/qt-private:$LIB_DIR${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
export LD_LIBRARY_PATH''').replace('PLUGIN_DIR="$SELF_DIR/../lib/qt6/plugins"','PLUGIN_DIR="$SELF_DIR/../lib/qt-private/qt6/plugins"');wrapper.write_text(text)
 (root/'libexec/qt.conf').write_text('[Paths]\nPrefix = ..\nPlugins = lib/qt-private/qt6/plugins\nLibraries = lib/qt-private\n')
 after=files(root)
 allowed={'bin/btx-qt','libexec/btx-qt.real','libexec/btx-atlas.real','libexec/qt.conf'}|removable
 protected={n:v for n,v in before.items() if n not in allowed}
 assert all(after.get(n)==v for n,v in protected.items()),'Protected package file changed'
 s['protected_files_unchanged']=len(protected);s['node_and_openssl_unchanged']=all(after[n]==before[n] for n in before if n.startswith(('bin/btxd','libexec/btxd','lib/libssl.so','lib/libcrypto.so')))
 assert s['node_and_openssl_unchanged']
 s['changes']={n:{'before':before.get(n),'after':after.get(n)} for n in sorted(set(before)|set(after)) if before.get(n)!=after.get(n)}
 s['gui_candidate_binaries']={n:sha(root/n) for n in gui}
 s['candidate_files']=after
 archive=dst/'btx-linux-gui-candidate.tar.gz'
 with tarfile.open(archive,'w:gz',compresslevel=1) as t:t.add(root,arcname=root.name)
 s['candidate_archive_sha256']=sha(archive)
 s['archive_checker_sha256']=sha(checker)
 s['gate_exit']=run([sys.executable,checker,'--archive',archive,'--no-launch','--require-model-helpers'],'archive-gate')
 problems=[x for x in (out/'archive-gate.log').read_text().splitlines() if x.startswith('  - ')]
 s['archive_problems']=problems
 known='  - btx-0.34.16/libexec/btx-guardd: no RUNPATH reaches btx-0.34.16/lib, so the host\'s libsqlite3.so.0, libstdc++.so.6, libgcc_s.so.1 load instead of the copies this archive ships'
 s['full_archive_gate_pass']=s['gate_exit']==0
 s['only_unchanged_guard_diagnostic']=(s['gate_exit']!=0 and len(problems)==1 and problems[0].startswith('  - btx-0.34.16/libexec/btx-guardd: no RUNPATH reaches ') and problems[0].endswith(', so the host'+known.split(', so the host',1)[1]) and after['libexec/btx-guardd']==before['libexec/btx-guardd'])
 # The inherited guard warning is not silently waived for release. A no-guard/modelnet-off GUI observation may proceed with the failure explicit.
 assert s['full_archive_gate_pass'] or s['only_unchanged_guard_diagnostic'],'New archive failure: stop before GUI'
 assert s['node_and_openssl_unchanged']
 s['gui_observation_allowed']=True
 (dst/'provenance.json').write_text(json.dumps(s,indent=2)+'\n')
 s['assembly_complete']=True
except Exception as e:s['error']=repr(e)
finally:
 (out/'result.json').write_text(json.dumps(s,indent=2)+'\n')
raise SystemExit(0 if s.get('assembly_complete') and not s.get('error') else 1)
