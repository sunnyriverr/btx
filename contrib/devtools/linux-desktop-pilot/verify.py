from pathlib import Path
import os,json,tarfile,sys
from checkpoint import sha,restore_timestamps,verify_restored
w=Path(os.environ['GITHUB_WORKSPACE']);p=w/'saved-successor';m=json.loads((p/'manifest.json').read_text());assert sha(p/'build-state.tar.gz')==m['archive_sha256'];out=w/'restored';out.mkdir()
with tarfile.open(p/'build-state.tar.gz') as t:t.extractall(out,filter='data')
restore_timestamps(out,m);verify_restored(out,m)
b=w/'saved-binary/btx-qt';assert sha(b)==sha(out/'gui-pilot-runtime/qtbuild/bin/btx-qt')
r={'checkpoint_verified':True,'archive_sha256':m['archive_sha256'],'entries':len(m['rows']),'binary_sha256':sha(b),'source':m['identity']['source'],'compile_pass':m['identity']['compile_pass']}
(w/'verification.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
