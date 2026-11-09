"""Construct a separate GUI candidate; protected monetary/model-plane bytes stay unchanged."""
from pathlib import Path
import os,sys,subprocess,hashlib,json,tarfile,urllib.request,shutil,importlib.util
w=Path(os.environ['GITHUB_WORKSPACE']);out=w/'candidate-results';out.mkdir();dst=w/'candidate-output';dst.mkdir();runtime=w/'candidate-runtime';runtime.mkdir()
s={'fixture':os.environ['GITHUB_SHA'],'source':'dac9aee53520bd49ed320ec7a49b9072fc7d88d9','reconstructed_candidate':True,'release_qualified':False}
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
 assert sha(old)=='0552bcbceef9fab5a6b9e24f26f4ccf7e615437e5d4c4af608a6247d5c21e6dc'
 s['original_archive_sha256']=sha(old)
 with tarfile.open(old) as t:
  assert sum(m.size for m in t.getmembers())<2*1024**3;t.extractall(runtime/'package',filter='data')
 root=runtime/'package/btx-0.34.16';assert root.is_dir();before=files(root)
 baseline=runtime/'baseline';shutil.copytree(root,baseline,symlinks=True)
 qt=w/'retained-qt/btx-qt';atlas=w/'retained-atlas/btx-atlas'
 assert sha(qt)=='7239c3b1e80e8114e47ebf3bd5b060b95c23db746dd70533681a9858763329a5'
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
 # Reuse only the qualified baseline Qt runtime closure, not old BTX binaries.
 prior=w/'retained-runtime/btx-linux-gui-candidate-corrected.tar.gz'
 assert sha(prior)=='d1bce2176834400fbd5202a268524d7348473b469db81a427179943ae063e2d9'
 prior_dir=runtime/'qt-runtime'
 with tarfile.open(prior) as t:t.extractall(prior_dir,filter='data')
 qtlibs=prior_dir/'btx-0.34.16/lib/qt-private'
 assert (qtlibs/'qt6/plugins/platforms/libqxcb.so').is_file()
 # Build-time dependency discovery uses current protected shared runtime first.
 os.environ['LD_LIBRARY_PATH']=str(baseline/'lib')+':'+str(qtlibs)
 shutil.copy2(qt,root/'libexec/btx-qt.real');(root/'libexec/btx-qt.real').chmod(0o755)
 shutil.copy2(atlas,root/'libexec/btx-atlas.real');(root/'libexec/btx-atlas.real').chmod(0o755)
 bundler=load('current_qt_bundler',Path(__file__).with_name('bundle_qt_gui.py'))
 bundler._qt_plugins_root=lambda:qtlibs/'qt6/plugins'
 bundler.bundle_linux_qt(root/'libexec/btx-qt.real',root/'lib/qt-private',shared_roots=[baseline/n for n in protected_roots])
 assert run(['patchelf','--set-rpath','$ORIGIN/../lib',root/'libexec/btx-atlas.real'],'atlas-rpath')==0
 after=files(root);allowed={'libexec/btx-qt.real','libexec/btx-atlas.real','libexec/qt.conf'}|removable
 protected={n:v for n,v in before.items() if n not in allowed}
 assert all(after.get(n)==v for n,v in protected.items()),'Protected package file changed'
 s['protected_files_unchanged']=len(protected);s['node_and_openssl_unchanged']=True
 s['changes']={n:{'before':before.get(n),'after':after.get(n)} for n in sorted(set(before)|set(after)) if before.get(n)!=after.get(n)}
 s['gui_candidate_binaries']={n:sha(root/n) for n in gui};s['candidate_files']=after
 os.environ.pop('LD_LIBRARY_PATH',None)
 # Drop only empty directories; the release writer owns archive metadata.
 for d in sorted(root.rglob('*'),key=lambda x:len(x.parts),reverse=True):
  if d.is_dir() and not d.is_symlink() and not any(d.iterdir()):d.rmdir()
 packager=load('current_packager',Path(__file__).with_name('package_release_archive.py'))
 archive=dst/'btx-linux-gui-candidate.tar.gz';packager.write_tar_gz(archive,root)
 s['candidate_archive_sha256']=sha(archive);s['archive_checker_sha256']=sha(checker)
 s['gate_exit']=run([sys.executable,checker,'--archive',archive,'--no-launch','--require-model-helpers'],'archive-gate')
 s['archive_problems']=[x for x in(out/'archive-gate.log').read_text().splitlines() if x.startswith('  - ')]
 assert s['gate_exit']==0,'Archive admission failed: stop before GUI'
 s.update(full_archive_gate_pass=True,only_unchanged_guard_diagnostic=False,gui_observation_allowed=True,remaining_gate_scope='Normal daemon-launch gate and native runtime still required',assembly_complete=True)
 (dst/'provenance.json').write_text(json.dumps(s,indent=2)+'\n')
except Exception as e:
 import traceback
 s['error']=repr(e);s['traceback']=traceback.format_exc()
finally:(out/'result.json').write_text(json.dumps(s,indent=2)+'\n')
raise SystemExit(0 if s.get('assembly_complete') and not s.get('error') else 1)
