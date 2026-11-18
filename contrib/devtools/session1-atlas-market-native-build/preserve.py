"""Preserve only this hosted task's source/build, regardless of test verdict."""
from pathlib import Path
import os,json,hashlib,tarfile,shutil,time
w=Path(os.environ['GITHUB_WORKSPACE']);r=w/'records';r.mkdir(exist_ok=True);out=w/'retained';out.mkdir(exist_ok=True)
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for x in iter(lambda:f.read(1048576),b''):h.update(x)
 return h.hexdigest()
inv={};total=0
roots=['product','mac-config-build','job-deps']
for root in roots:
 p=w/root
 if not p.exists():continue
 for x in p.rglob('*'):
  rel=x.relative_to(w)
  if '.git' in rel.parts or '__pycache__' in rel.parts:continue
  st=x.lstat()
  if x.is_symlink():meta={'type':'symlink','target':os.readlink(x)}
  elif x.is_dir():meta={'type':'dir'}
  elif x.is_file():meta={'type':'file','bytes':st.st_size,'sha256':sha(x)};total+=st.st_size
  else:continue
  inv[str(rel)]={**meta,'mode':st.st_mode&0o777,'mtime_ns':st.st_mtime_ns}
(r/'checkpoint-inventory.json').write_text(json.dumps(inv,indent=2)+'\n')
if total and shutil.disk_usage(w).free>total+3*1024**3:
 archive=out/'checkpoint.tar.gz'
 with tarfile.open(archive,'w:gz',compresslevel=2,dereference=False) as t:
  for name in inv:t.add(w/name,arcname=name,recursive=False)
 receipt={'sha256':sha(archive),'bytes':archive.stat().st_size,'live_bytes':total,'files':len(inv),'scope':'Session1 Atlas market candidate node build checkpoint; no runtime/fullsuite/release qualification'}
 (out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');shutil.copy2(r/'checkpoint-inventory.json',out/'inventory.json');(r/'preservation-outcome.json').write_text(json.dumps({'preserved':True,**receipt},indent=2)+'\n');print(json.dumps(receipt))
else:(r/'preservation-outcome.json').write_text(json.dumps({'live_bytes':total,'free':shutil.disk_usage(w).free,'reason':'Insufficient space for a second compressed copy or no restored state'}))
