from pathlib import Path
import argparse,hashlib,json,shutil,subprocess,time
from apply_exact_patch import apply_patch
p=argparse.ArgumentParser();p.add_argument('--source',required=True,type=Path);p.add_argument('--crypto',required=True,type=Path);p.add_argument('--json',required=True,type=Path);p.add_argument('--work',required=True,type=Path);a=p.parse_args()
source=a.source.resolve();work=a.work.resolve();package=Path(__file__).resolve().parent;m=json.loads((package/'manifest.json').read_text());sha=lambda f:hashlib.sha256(f.read_bytes()).hexdigest()
for name,digest in m['source_sha256'].items():assert sha(source/name)==digest,name
assert sha(a.crypto)==m['dependency_archives']['crypto.a'];assert sha(a.json)==m['dependency_archives']['json.a'];assert sha(package/'timing-prerequisite.patch')==m['timing_patch_sha256']
assert not work.exists();work.mkdir(parents=True,mode=0o700)
shutil.copytree(source/'src/modelnet/security_v2',work/'src/modelnet/security_v2');target=work/'test/util/model_security';target.mkdir(parents=True);shutil.copy2(source/'test/util/model_security/security_tests.cpp',target/'security_tests.cpp')
apply_patch(work,package/'timing-prerequisite.patch');apply_patch(work,package/'test-only.patch');assert sha(target/'security_tests.cpp')==m['test_sha256']
service=work/'src/modelnet/security_v2/service.cpp';s=service.read_text();needle='if(++submitted==2)break;';assert s.count(needle)==1;(work/'cap99-service.cpp').write_text(s.replace(needle,'if(++submitted==99)break;'))
shutil.copy2(package/'CMakeLists.txt',work/'CMakeLists.txt')
subprocess.run(['cmake','-S',str(work),'-B',str(work/'build'),'-DCMAKE_BUILD_TYPE=Release','-DCMAKE_EXPORT_COMPILE_COMMANDS=ON','-DBTX_SOURCE_ROOT='+str(source),'-DCRYPTO_ARCHIVE='+str(a.crypto.resolve()),'-DJSON_ARCHIVE='+str(a.json.resolve())],check=True)
subprocess.run(['cmake','--build',str(work/'build'),'--parallel','1'],check=True)
identities={str(f.relative_to(work)):sha(f) for f in [service,work/'cap99-service.cpp',target/'security_tests.cpp',work/'build/cap2',work/'build/cap99',work/'build/security-probe',work/'build/CMakeFiles/harness.dir/test/util/model_security/security_tests.cpp.o']};(work/'identities.json').write_text(json.dumps(identities,indent=2));rows=[]
for cap in [2,99]:
 out=work/('result-cap'+str(cap));out.mkdir(mode=0o700);start=time.monotonic()
 with (out/'run.log').open('w') as log:r=subprocess.run([str(work/('build/cap'+str(cap))),str(work/'build/security-probe'),str(out/'summary.json'),'scheduler-valid-work-and-two-per-tick'],stdout=log,stderr=subprocess.STDOUT,timeout=25)
 j=json.loads((out/'summary.json').read_text());lines=(out/'run.log').read_text().splitlines();observation=[s for s in lines if s.startswith('CAP_OBSERVATION ')];row={'cap':cap,'exit':r.returncode,'seconds':time.monotonic()-start,'passed':j['passed'],'failed':j['failed'],'tests':j['tests'],'observations':observation,'signed_endpoints':len(j['scheduler_evidence'])};rows.append(row);print(json.dumps(row),flush=True)
(work/'results.json').write_text(json.dumps(rows,indent=2))
