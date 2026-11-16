"""Retain this disposable runner's actual state under a new immutable cache key."""
from pathlib import Path
import hashlib,json,datetime,os
R=Path('D:/btx-native-035');B=R/'project-build';E=R/'governor-repair-evidence';S=Path(os.environ['GITHUB_WORKSPACE'])/'btx'
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for x in iter(lambda:f.read(1048576),b''):h.update(x)
 return h.hexdigest()
E.mkdir(exist_ok=True)
if not (B/'btx-successor.json').is_file():raise SystemExit('No restored checkpoint; no state to retain')
cp=json.loads((B/'btx-successor.json').read_text());result=json.loads((E/'result.json').read_text()) if (E/'result.json').exists() else {'status':'SETUP_INCOMPLETE','phases':{}}
for n,v in cp['files'].items():
 p=R/n
 if p.is_file():v.update(sha256=sha(p),mtime_ns=p.stat().st_mtime_ns,size=p.stat().st_size)
for n,v in cp['source_files'].items():
 p=S/n
 if p.is_file():v.update(sha256=sha(p),mtime_ns=p.stat().st_mtime_ns,size=p.stat().st_size)
cp['governor_repair']={'run':os.environ['GITHUB_RUN_ID'],'harness_commit':os.environ['GITHUB_SHA'],'status':result['status'],'phases':result.get('phases',{}),'original_checkpoint':'d980ca1fae8a45385fc5ca9777fc89ffb3ae977f5af7b841dde18f3352e0d515','candidate_source_manifest':json.loads((Path(__file__).parent/'source-manifest.json').read_text()),'utc':datetime.datetime.now(datetime.timezone.utc).isoformat()}
cp['build_result']={'status':result['status'],'tests_run':bool(result.get('phases',{}).get('candidate',{}).get('tests')),'acceptance':'Not full-unit acceptance; consult exact governor result'}
(B/'btx-governor-checkpoint.json').write_text(json.dumps(cp,indent=2)+'\n')
(E/'checkpoint-receipt.json').write_text(json.dumps({'sha256':sha(B/'btx-governor-checkpoint.json'),'cache_key':'btx-governor-repair-'+os.environ['GITHUB_RUN_ID'],'files':len(cp['files']),'source_files':len(cp['source_files'])},indent=2)+'\n')
