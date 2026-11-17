from pathlib import Path
import json,hashlib,tarfile,os,shutil,subprocess
w=Path(os.environ['GITHUB_WORKSPACE']);r=w/'retryqual';out=w/'records';out.mkdir(exist_ok=True)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(w/'checkpoint/build-state.tar.gz')=='7099e445368c278fefde438ed282238a55fdfffb2c3566a2354a1ca43aa121ba'
m=json.load(open(w/'checkpoint/manifest.json'));prefix='gui-pilot-runtime/openssl';selected={k:v for k,v in m['rows'].items() if k==prefix or k.startswith(prefix+'/')};assert selected
with tarfile.open(w/'checkpoint/build-state.tar.gz') as t:
 for member in t:
  if member.name in selected:
   assert not Path(member.name).is_absolute() and '..' not in Path(member.name).parts;t.extract(member,w,filter='data')
for name,row in selected.items():
 p=w/name
 if row['kind']=='file':assert sha(p)==row['sha256'];p.chmod(row['mode'])
 elif row['kind']=='link':assert p.is_symlink() and os.readlink(p)==row['target']
 elif row['kind']=='directory':p.chmod(row['mode'])
expected={'baseline':'2e3ac26cca88103937a11c0c771e82b96e3f055b3fe4c45f09a504ed56c29ce9','candidate':'f62fb21f1246658c04c437b96b228bf41f9552f7897e287c8183fa29082c50eb'}
for phase,h in expected.items():
 p=w/'binaries'/phase/'btx-modeld';assert sha(p)==h;p.chmod(0o755)
(r/'stage-receipt.json').write_text(json.dumps({'openssl_manifest_files':len(selected),'helpers':expected,'rebuild':False},indent=2));shutil.copyfile(r/'stage-receipt.json',out/'stage-receipt.json')

# The hosted checkout parents are private to runner. Stage only verified inputs in /tmp.
portable=Path('/tmp/bounty-save-input');assert not portable.exists();portable.mkdir(mode=0o755)
shutil.copytree(w/prefix,portable/'openssl',symlinks=True)
for phase in expected:
 shutil.copy2(w/'binaries'/phase/'btx-modeld',portable/('helper-'+phase));assert sha(portable/('helper-'+phase))==expected[phase]
shutil.copy2(r/'test.py',portable/'test.py');assert sha(portable/'test.py')==sha(r/'test.py')
