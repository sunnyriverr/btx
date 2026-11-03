from pathlib import Path
import argparse,hashlib,json,shutil
from apply_exact_patch import apply_patch
p=argparse.ArgumentParser();p.add_argument('--work',required=True,type=Path);a=p.parse_args()
package=Path(__file__).resolve().parent;work=a.work.resolve();m=json.loads((package/'manifest.json').read_text());sha=lambda f:hashlib.sha256(f.read_bytes()).hexdigest()
assert not work.exists();work.mkdir(mode=0o700)
for name,digest in m['package_inputs'].items():assert sha(package/name)==digest,name
for name,digest in m['source_files'].items():assert sha(package/'source'/name)==digest,name
shutil.copytree(package/'source',work/'source')
shutil.copytree(package/'source/src/modelnet/security_v2',work/'common/src/modelnet/security_v2')
# Apply the unchanged known timing prerequisite to common source and each Service variant.
for variant in ['baseline','candidate']:
 root=work/('assembly-'+variant);shutil.copytree(work/'common',root)
 for name in ['service.cpp','work.cpp','work.h']:
  shutil.copy2(package/('baseline' if variant=='baseline' else 'source/src/modelnet/security_v2')/name,root/'src/modelnet/security_v2'/name)
 apply_patch(root,package/'timing-prerequisite.patch')
 dst=work/variant;dst.mkdir()
 headers=dst/'include/modelnet/security_v2';headers.mkdir(parents=True)
 shutil.copy2(root/'src/modelnet/security_v2/work.h',headers/'work.h')
 for name in ['service.cpp','work.cpp']:shutil.copy2(root/'src/modelnet/security_v2'/name,dst/name)
 if variant=='candidate':
  shutil.rmtree(work/'common');shutil.copytree(root,work/'common')
 shutil.rmtree(root)
testroot=work/'patch-check';testpath=testroot/'test/util/model_security';testpath.mkdir(parents=True)
shutil.copy2(package/'source/test/util/model_security/security_tests.cpp',testpath/'security_tests.cpp')
apply_patch(testroot,package/'test-only.patch');assert sha(testpath/'security_tests.cpp')==sha(package/'security_tests.cpp')
shutil.rmtree(testroot)
shutil.copy2(package/'security_tests.cpp',work/'security_tests.cpp');shutil.copy2(package/'CMakeLists.txt',work/'CMakeLists.txt')
ident={str(f.relative_to(work)):sha(f) for f in work.rglob('*') if f.is_file()};(work/'assembled-identities.json').write_text(json.dumps(ident,indent=2)+'\n')
print('ASSEMBLY PASS',len(ident))
