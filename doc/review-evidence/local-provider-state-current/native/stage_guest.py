from pathlib import Path
import subprocess,json,sys,base64,hashlib
sys.path.insert(0,'work/btx-review-tools/lan-linux-native');from vm import vm
S=Path('work/btx-lanes/session-2/mlkem-peer-key-validation/source');P=Path(__file__).resolve().parent
r=json.loads((P/'guest-source-audit.json').read_text());assert r['checked']==14309 and not r['missing']
files={n:base64.b64encode(subprocess.check_output(['git','show','666673a3:'+n],cwd=S)).decode() for n in r['mismatches']}
code='''from pathlib import Path
import json,sys,base64,io,tarfile,hashlib
r=Path('/tmp/btx-session2-helper-restart-current');root=r/'source';files=json.load(sys.stdin);backup=io.BytesIO()
with tarfile.open(fileobj=backup,mode='w:gz') as tar:
 for name in files:tar.add(root/name,arcname=name,recursive=False)
(r/'provider-state-current').mkdir(exist_ok=True)
(r/'provider-state-current/pre-source.tar.gz').write_bytes(backup.getvalue())
for name,data in files.items():
 p=root/name;assert p.is_file() and not p.is_symlink();p.write_bytes(base64.b64decode(data))
print(json.dumps({'restored_files':len(files),'backup_sha256':hashlib.sha256(backup.getvalue()).hexdigest()}))
'''
z=vm(['python3','-c',code],input=json.dumps(files).encode(),capture_output=True,timeout=30,check=True);(P/'stage-receipt.json').write_bytes(z.stdout)
z=vm(['cat','/tmp/btx-session2-helper-restart-current/provider-state-current/pre-source.tar.gz'],capture_output=True,timeout=30,check=True);(P/'pre-source.tar.gz').write_bytes(z.stdout)
# Install the maintained regression at its actual source-tree path on both variants.
data=(P.parent/'source/test/util/modelnet_provider_state.py').read_bytes()
code="from pathlib import Path;import sys;p=Path('/tmp/btx-session2-helper-restart-current/source/test/util/modelnet_provider_state.py');p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(sys.stdin.buffer.read())"
vm(['python3','-c',code],input=data,capture_output=True,timeout=20,check=True)
print('Accepted source staged; previous 20-file delta preserved; maintained test staged unchanged')
