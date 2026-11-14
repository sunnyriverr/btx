from pathlib import Path
import os,json
from checkpoint import create
w=Path(os.environ['GITHUB_WORKSPACE']);r=json.load(open(w/'pilot-records/result.json'))
assert r['verdict']=='PREPARATION_PASS' and r['product_compile_started'] is False
m=create(w,w/'configured-checkpoint',{'source':'f40eb37a6fb8b665340fe92a2f248ff3f23ec7f6','purpose':'verified configured helper dry-plan; no compile'})
(w/'pilot-records/checkpoint-receipt.json').write_text(json.dumps({'archive_sha256':m['archive_sha256'],'files':len(m['rows']),'source':m['identity']['source'],'compiled':False},indent=2))
print('CONFIGURED_CHECKPOINT_RETAINED',m['archive_sha256'],flush=True)
