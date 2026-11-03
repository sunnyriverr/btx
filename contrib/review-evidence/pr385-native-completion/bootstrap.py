from pathlib import Path
import argparse,subprocess,hashlib,json,tarfile
p=argparse.ArgumentParser();p.add_argument('--repo',required=True,type=Path);a=p.parse_args()
here=Path(__file__).resolve().parent;m=json.loads((here/'manifest.json').read_text())
paths=['src/compat','src/crypto','src/modelnet/security_v2','src/univalue','src/libbitcoinpqc/include','test/util/model_security']
data=subprocess.check_output(['git','-C',str(a.repo),'archive','--format=tar','--prefix=source/',m['candidate'],*paths])
assert hashlib.sha256(data).hexdigest()==m['package_inputs']['source.tar']
(here/'source.tar').write_bytes(data)
with tarfile.open(here/'source.tar') as t:
 for member in t.getmembers():
  assert not member.name.startswith('/') and '..' not in Path(member.name).parts and not member.issym() and not member.islnk()
 t.extractall(here)
(here/'baseline').mkdir(exist_ok=True)
for name in ['work.h','work.cpp','service.cpp']:
 (here/'baseline'/name).write_bytes(subprocess.check_output(['git','-C',str(a.repo),'show',m['baseline']+':src/modelnet/security_v2/'+name]))
for name,digest in m['package_inputs'].items():assert hashlib.sha256((here/name).read_bytes()).hexdigest()==digest,name
print('BOOTSTRAP PASS: exact tested package inputs reconstructed')
