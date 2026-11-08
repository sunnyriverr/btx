from pathlib import Path
import os,json,tarfile,sys
from checkpoint import sha,restore_timestamps,verify_restored
w=Path(os.environ['GITHUB_WORKSPACE']);records=w/'saved-records';s=json.loads((records/'result.json').read_text());out=w/'retention-verification.json'
assert sys.version_info>=(3,12)
assert s['fixture']==os.environ['EXPECTED_FIXTURE']
assert s['source']=='ff5f3f04ea11f044594987fc6be043ff68b136ad'
assert s.get('precompile_gate',{}).get('pass') is True
assert s['qt_compiled'] and s['abi_pass'] and s['source_clean'] and s['checkpoint_verified'] and not s.get('error') and not s.get('checkpoint_error')
binary=w/'saved-binary/btx-qt';assert sha(binary)==s['component_sha256']
co=w/'saved-checkpoint';m=json.loads((co/'manifest.json').read_text());assert m['identity']['source']==s['source'] and m['identity']['fixture']==s['fixture']
assert sha(co/'build-state.tar.gz')==m['archive_sha256']==s['checkpoint_archive_sha256']
assert m['rows']['gui-pilot-runtime/qtbuild/bin/btx-qt']['sha256']==s['component_sha256']
d=w/'restored';d.mkdir()
with tarfile.open(co/'build-state.tar.gz') as t:t.extractall(d,filter='data')
restore_timestamps(d,m);verify_restored(d,m)
assert sha(d/'gui-pilot-runtime/qtbuild/bin/btx-qt')==sha(binary)
result={'source':s['source'],'fixture':s['fixture'],'component_sha256':s['component_sha256'],'checkpoint_sha256':m['archive_sha256'],'entries':len(m['rows']),'full_compiled_tree_restored':True,'independent_binary_matches':True,'precompile_gate':s['precompile_gate'],'abi_pass':s['abi_pass'],'python':sys.version,'atlas_rebuilt':False,'packaged_gui_qualified':False}
out.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
