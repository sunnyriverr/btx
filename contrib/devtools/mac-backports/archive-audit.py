"""Audit all package Mach-O images and qualify the integrity gate on owned copies."""
from pathlib import Path
import sys,importlib.util,subprocess,json,shutil,hashlib
root=Path(sys.argv[1]).resolve();source=Path(sys.argv[2]);out=Path(sys.argv[3]);out.mkdir(exist_ok=True)
spec=importlib.util.spec_from_file_location('runtime_bundle',source/'scripts/release/bundle_macos_python_runtime.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
images=[p for p in root.rglob('*') if m.macho(p)];assert len(images)>=16
m.verify_architectures(images,'arm64');m.verify_closure(images,root)
for p in images:
 subprocess.run(['codesign','--verify','--strict',str(p)],check=True,capture_output=True)
 shown=subprocess.run(['codesign','-d','--verbose=4',str(p)],check=True,capture_output=True,text=True);assert 'Signature=adhoc' in shown.stderr,('Unexpected signing identity',str(p))
target=root/'libexec/btxd.real';original=target.read_bytes();digest=hashlib.sha256(original).hexdigest();row={'images':len(images),'all_closure_architecture_signatures_pass':True}
try:
 deps=m.helper('verify_release_btxd').macho_load_paths(target)[0];dep=next(x for x in deps if not m.system_load(x))
 subprocess.run(['install_name_tool','-change',dep,'/opt/homebrew/forbidden-archive-control.dylib',str(target)],check=True,capture_output=True)
 # Keep the dependency control distinct from the signature control below.
 subprocess.run(['codesign','--force','--sign','-',str(target)],check=True,capture_output=True)
 try:m.verify_closure([target],root)
 except RuntimeError as e:
  assert 'homebrew' in str(e).lower();row['bad_load_rejected']=str(e)
 else:raise AssertionError('Bad dependency passed closure gate')
finally:target.write_bytes(original)
try:
 damaged=bytearray(original);assert len(damaged)>4096;damaged[4096]^=1;target.write_bytes(damaged)
 r=subprocess.run(['codesign','--verify','--strict',str(target)],capture_output=True,text=True);assert r.returncode!=0;row['bad_signature_rejected']=r.stderr
finally:target.write_bytes(original)
assert hashlib.sha256(target.read_bytes()).hexdigest()==digest
subprocess.run(['codesign','--verify','--strict',str(target)],check=True,capture_output=True);m.verify_closure(images,root);row['restored_daemon_sha256']=digest
row['image_hashes']={str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in images};(out/'archive-audit.json').write_text(json.dumps(row,indent=2)+'\n');print('All-image archive audit and negative controls PASS',len(images))
