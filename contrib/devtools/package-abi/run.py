from pathlib import Path
import urllib.request,hashlib,subprocess,json,os,importlib.util,sys,shutil,tempfile
p=Path(os.environ['GITHUB_WORKSPACE']);out=p/'abi-results';out.mkdir();script=Path(__file__).with_name('verify_release_btxd.py')
expected='796b9edd064272b1f443cf3e08646565936183f9f1e15339cad60e84e1014b32'
s={'fixture':os.environ['GITHUB_SHA'],'checker_sha256':hashlib.sha256(script.read_bytes()).hexdigest(),'application_launch':False}
with tempfile.TemporaryDirectory(prefix='btx-abi-') as tmp:
 root=Path(tmp);a=root/'release.tar.gz'
 with urllib.request.urlopen('https://github.com/btxchain/btx/releases/download/v0.34.16/btx-0.34.16-x86_64-linux-gnu.tar.gz',timeout=60) as src,a.open('wb') as dst:shutil.copyfileobj(src,dst)
 s['archive_sha256']=hashlib.sha256(a.read_bytes()).hexdigest();assert s['archive_sha256']==expected and a.stat().st_size==158893566
 with (out/'archive-gate.log').open('wb') as f:
  r=subprocess.run([sys.executable,str(script),'--archive',str(a),'--no-launch','--require-model-helpers'],stdout=f,stderr=subprocess.STDOUT,timeout=180)
 s['gate_exit']=r.returncode
 spec=importlib.util.spec_from_file_location('existing_gate',script);m=importlib.util.module_from_spec(spec);sys.modules[spec.name]=m;spec.loader.exec_module(m)
 dest=root/'extracted';dest.mkdir();m.extract_release_archive(a,dest)
 inventory=[]
 for path in sorted(dest.rglob('*')):
  if not path.is_file() or path.is_symlink():continue
  with path.open('rb') as f:magic=f.read(4)
  if magic!=b'\x7fELF':continue
  versions=m.elf_required_versions(path)
  inventory.append({'path':str(path.relative_to(dest)),'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'versions':versions})
 s['elf_inventory']=inventory;s['glibc_offenders']=[x for x in inventory if 'GLIBC' in x['versions'] and m.version_key(x['versions']['GLIBC'])>m.version_key(m.GLIBC_CEILING)]
 s['host_glibc']=subprocess.check_output(['getconf','GNU_LIBC_VERSION'],text=True).strip()
 s['archive_unchanged']=hashlib.sha256(a.read_bytes()).hexdigest()==expected
s['temporary_files_removed']=not root.exists()
(out/'result.json').write_text(json.dumps(s,indent=2)+'\n')
assert s['archive_unchanged'] and s['temporary_files_removed']
print('Inventory complete; gate exit',s['gate_exit'],'ELFs',len(inventory),'GLIBC offenders',len(s['glibc_offenders']))
