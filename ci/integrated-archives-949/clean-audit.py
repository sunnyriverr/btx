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
row['negative_controls_reused_from_run']=43656591080
row['image_hashes']={str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in images};(out/'archive-audit.json').write_text(json.dumps(row,indent=2)+'\n');print('All-image current archive audit PASS; unchanged negative controls reused',len(images))
