from pathlib import Path
import subprocess,json,shutil,hashlib,os
source=Path('source');ref=Path('current-source');out=Path('records');pin='1e2f8b5f12295002334d3390c12cac0bb4ae2aff';assert subprocess.check_output(['git','-C',str(ref),'rev-parse','HEAD'],text=True).strip()==pin
tracked=subprocess.check_output(['git','-C',str(ref),'ls-files','-z']).decode().split('\0');tracked={n for n in tracked if n};old={p.relative_to(source).as_posix() for p in source.rglob('*') if p.is_file() or p.is_symlink()};changed=[];added=[];removed=[]
def same(a,b):
 if a.is_symlink() or b.is_symlink():return a.is_symlink() and b.is_symlink() and os.readlink(a)==os.readlink(b)
 return a.is_file() and b.is_file() and hashlib.sha256(a.read_bytes()).digest()==hashlib.sha256(b.read_bytes()).digest()
for n in sorted(tracked):
 a=source/n;b=ref/n
 if same(a,b):continue
 assert not (n.endswith('CMakeLists.txt') or n.startswith('cmake/')),'Changed CMake input requires fresh configure: '+n
 (changed if a.exists() else added).append(n);a.parent.mkdir(parents=True,exist_ok=True)
 if a.exists() or a.is_symlink():a.unlink()
 if b.is_symlink():a.symlink_to(os.readlink(b))
 else:shutil.copyfile(b,a);shutil.copymode(b,a)
for n in old-tracked:
 if not n.startswith('.git/'):
  p=source/n
  if p.is_file() or p.is_symlink():p.unlink();removed.append(n)
shutil.copytree(ref/'.git',source/'.git');assert subprocess.check_output(['git','-C',str(source),'rev-parse','HEAD'],text=True).strip()==pin
for n in tracked:assert same(source/n,ref/n),n
with (out/'current-remaining-plan.log').open('w') as f:subprocess.run(['ninja','-C','build','-n','btxd','btx-cli'],stdout=f,stderr=subprocess.STDOUT,check=True,timeout=120)
lines=(out/'current-remaining-plan.log').read_text().splitlines();d={'source':pin,'changed':changed,'added':added,'removed':removed,'remaining_steps':sum(l.startswith('[') for l in lines),'retained_objects':sum(1 for p in Path('build').rglob('*.o')),'identical_source_mtimes_preserved':True};(out/'overlay.json').write_text(json.dumps(d,indent=2)+'\n');print(json.dumps(d),flush=True)
