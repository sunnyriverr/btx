"""Qualify retained installer bytes after the documented CRLF-only guard stop."""
from pathlib import Path
import hashlib,json,re,shutil
HERE=Path(__file__).resolve().parent
OUT=Path('atlas-installer-results').resolve();OUT.mkdir(exist_ok=True)
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
manifest=json.loads((HERE/'inputs.json').read_text())
for name,digest in manifest['fixtures'].items():assert sha(HERE/name)==digest,name
original=json.loads((HERE/'original-build.json').read_text())
assert original['errors']==["RuntimeError('actual dependency macro content unchanged')"]
assert original['pass'] is False
source=json.loads((HERE/'product-inputs.json').read_text())
assert original['inputs']['source']==source['source']=='e70c81f03b76c5e62712ebb51dfaac7d41295af2'
checks={c['name']:c['pass'] for c in original['checks']}
for item in source['files']:assert checks['before '+item['path']],item['path']
assert len([c for c in original['checks'] if c['name'].startswith('before ')])==228
assert all(c['pass'] for c in original['checks'] if c['name']!='actual dependency macro content unchanged')
assert any(c['log']=='package-build.log' and c['exit']==0 for c in original['commands'])
raw=(HERE/'original-FileAssociation.nsh').read_bytes()
content=raw.removeprefix(b'\xef\xbb\xbf')
assert content.count(b'\r\n')==135
assert hashlib.sha256(content.replace(b'\r\n',b'\n')).hexdigest()==manifest['macro_sha256']
generated=(HERE/'original-installer.nsi').read_text(encoding='utf-8-sig')
defs=dict(re.findall(r'^!define\s+(\w+)\s+"(.*)"\s*$',generated,re.M))
assert defs['INSTALLMODE']=='currentUser' and defs['INSTALLWEBVIEW2MODE']=='offlineInstaller'
assert 'APP_ASSOCIATE "btx" "BTX Model Resource"' in generated
assert 'APP_UNASSOCIATE "btx" "BTX Model Resource"' in generated
installers=list(Path('atlas-package-output').resolve().glob('*.exe'));assert len(installers)==1
package=dict(original['built_package_raw']);assert sha(installers[0])==package['installer_sha256']
package.update(installer_path=str(installers[0]),definitions=defs,source=source['source'],installer_size=installers[0].stat().st_size)
facts={'original_run':41983707124,'original_build_pass':False,'compilation_and_packaging_exit':0,'prebuild_source_files_verified':228,'postbuild_source_audit':'not reached after encoding guard stopped; not claimed','macro_difference':'UTF-8 BOM and CRLF in official Windows CLI; source content identical after only CRLF to LF comparison','macro_raw_sha256':hashlib.sha256(raw).hexdigest(),'macro_normalized_sha256':hashlib.sha256(content.replace(b'\r\n',b'\n')).hexdigest(),'installer_rebuilt':False,'product_bytes_changed':False,'payload_hash':'not retained independently; current offline configuration and generated template verified','package_artifact_id':13395671094}
qualification={'qualified_for_lifecycle_test':True,'package':package,'facts':facts,'inputs':manifest}
for name in ['original-build.json','original-installer.nsi','original-FileAssociation.nsh']:shutil.copyfile(HERE/name,OUT/name)
(OUT/'qualification.json').write_text(json.dumps(qualification,indent=2)+'\n')
print(json.dumps(qualification,indent=2))
