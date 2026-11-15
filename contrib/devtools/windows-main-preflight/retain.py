from pathlib import Path
import json,hashlib,os,subprocess
R=Path('D:/btx-native-035');B=R/'project-build';E=R/'preflight-evidence';S=Path(os.environ['GITHUB_WORKSPACE'])/'btx'
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
files={str(p.relative_to(R)):{'sha256':sha(p),'bytes':p.stat().st_size} for folder in ['project-build','vcpkg-installed'] for p in (R/folder).rglob('*') if p.is_file() and p.name not in ['btx-checkpoint.json','btx-successor.json']}
source={}
for n in subprocess.check_output(['git','ls-files'],cwd=S,text=True).splitlines():
 p=S/n
 if p.is_file() and not p.is_symlink():source[n]={'sha256':sha(p),'mtime_ns':p.stat().st_mtime_ns}
receipt={'source':subprocess.check_output(['git','rev-parse','HEAD'],cwd=S,text=True).strip(),'files':files,'source_files':source,'profile':(B/'CMakeCache.txt').read_text(),'run':os.environ['GITHUB_RUN_ID'],'build_result':json.loads((E/'build-result.json').read_text()) if (E/'build-result.json').exists() else None,'baseline_marker_preserved':True}
(B/'btx-successor.json').write_text(json.dumps(receipt,indent=2));(E/'retention-receipt.json').write_text(json.dumps({'source':receipt['source'],'manifest_sha256':sha(B/'btx-successor.json'),'files':len(files),'objects':sum(n.endswith('.obj') for n in files),'cache_key':'btx-main074-successor-'+os.environ['GITHUB_RUN_ID']},indent=2));print('Retained',len(files),'files')
