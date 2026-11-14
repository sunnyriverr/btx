import importlib.util,json,subprocess,shutil,tempfile
from pathlib import Path
P=Path(__file__).resolve().parents[1];S=P/'repair/source/scripts/release';spec=importlib.util.spec_from_file_location('mac_bundle',S/'bundle_macos_python_runtime.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);root=P/'repair/relocated archives/candidate moved/btx-0.34.16';images=[p for p in root.rglob('*') if m.macho(p)];m.verify_closure(images,root);results={'positive_native_images_verified':len(images),'negative':[]};original=root/'libexec/btxd.real';old=next(x for x in m.loads(original) if 'Python.framework/' in x)
for kind in ['signature','missing','escape','homebrew']:
 probe=root/'libexec/gate-probe';shutil.copy2(original,probe)
 try:
  if kind=='signature':
   with probe.open('ab') as f:f.write(b'tamper-signature-control')
  else:
   target={'missing':'@loader_path/not-present/Python','escape':m.relative_load(probe,P/'python-pkg/Python_Framework.pkg/Payload/Versions/3.12/Python'),'homebrew':'/opt/homebrew/lib/libpython3.12.dylib'}[kind]
   subprocess.run(['install_name_tool','-change',old,target,str(probe)],check=True,capture_output=True);subprocess.run(['codesign','--force','--sign','-',str(probe)],check=True,capture_output=True)
  try:m.verify_closure([probe],root)
  except (RuntimeError,Exception) as error:
   message=str(error);expected={'signature':'codesign','missing':'missing','escape':'escapes','homebrew':'Homebrew'}[kind];assert expected in message,(kind,message);results['negative'].append({'case':kind,'rejected':True,'error':message})
  else:raise AssertionError(kind+' accepted')
 finally:probe.unlink(missing_ok=True)
(P/'repair/native-gate-results.json').write_text(json.dumps(results,indent=2)+'\n');print(json.dumps(results,indent=2))
