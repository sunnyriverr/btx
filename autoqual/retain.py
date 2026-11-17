from pathlib import Path
import os,json,shutil
from checkpoint import create
w=Path(os.environ['GITHUB_WORKSPACE']);p=w/'records/build-result.json'
if not p.exists():raise SystemExit(0)
s=json.load(open(p))
if s.get('binary_sha256') is None:raise SystemExit(0)
m=create(w,w/'retained-checkpoint',{'source_head':s['source_head'],'binary_sha256':s['binary_sha256'],'stage':s['status']})
shutil.copy2(w/'saved-checkpoint/external-inputs.json',w/'retained-checkpoint/external-inputs.json')
(w/'records/checkpoint-receipt.json').write_text(json.dumps({'source_head':s['source_head'],'archive_sha256':m['archive_sha256'],'rows':len(m['rows']),'binary_sha256':s['binary_sha256'],'private_build_only':True},indent=2)+'\n')
print('retained verified checkpoint',m['archive_sha256'],flush=True)
