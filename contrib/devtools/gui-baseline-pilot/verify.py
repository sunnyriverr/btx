from pathlib import Path
import json,os,tarfile
from checkpoint import sha,snapshot,restore_timestamps,verify_restored
w=Path(os.environ['GITHUB_WORKSPACE']);co=w/'saved-checkpoint';m=json.loads((co/'manifest.json').read_text());assert sha(co/'build-state.tar.gz')==m['archive_sha256']
d=w/'restored';d.mkdir()
with tarfile.open(co/'build-state.tar.gz') as t:
 x=t.getmember('product/src/libbitcoinpqc/dilithium/avx2/fips202.c');print('MEMBER',x.name,x.type,x.linkname,x.pax_headers,flush=True);print('MANIFEST',m['rows'][x.name],flush=True)
 t.extractall(d,filter='data')
actual=snapshot(d);deltas=[{'path':n,'actual':v,'expected':m['rows'][n]} for n,v in actual.items() if {k:x for k,x in v.items() if k!='mtime_ns'}!={k:x for k,x in m['rows'][n].items() if k!='mtime_ns'}];print('METADATA_DELTA',deltas[:3],flush=True)
restore_timestamps(d,m);verify_restored(d,m)
(w/'checkpoint-verification.json').write_text(json.dumps({'source':m['identity']['source'],'archive_sha256':m['archive_sha256'],'entries':len(m['rows']),'roundtrip':True,'qt_compiled':False,'metadata_differences':len(deltas)})+'\n')
