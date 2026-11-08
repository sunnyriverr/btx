from pathlib import Path
import json,os,tarfile
from checkpoint import sha,restore_timestamps,verify_restored
w=Path(os.environ['GITHUB_WORKSPACE']);co=w/'saved-checkpoint';m=json.loads((co/'manifest.json').read_text());assert sha(co/'build-state.tar.gz')==m['archive_sha256']
d=w/'restored';d.mkdir()
with tarfile.open(co/'build-state.tar.gz') as t:t.extractall(d,filter='data')
restore_timestamps(d,m);verify_restored(d,m)
(w/'checkpoint-verification.json').write_text(json.dumps({'source':m['identity']['source'],'archive_sha256':m['archive_sha256'],'entries':len(m['rows']),'roundtrip':True,'qt_compiled':False})+'\n')
