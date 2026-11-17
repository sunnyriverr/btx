# Run inside the isolated Linux payload directory after hash verification.
from pathlib import Path
import subprocess,json,hashlib,platform
r=Path(__file__).resolve().parent
sources=['src/modelnet/package_install.cpp','src/modelnet/transfer_session.cpp','src/modelnet/types.cpp','src/crypto/sha384.cpp','src/crypto/hex_base.cpp','src/util/time.cpp']
sources += [str(p.relative_to(r)) for p in (r/'src/univalue/lib').glob('*.cpp')]
rows=[]
for label,product in [('baseline','src/modelnet/package_execute.cpp'),('candidate','candidate.cpp')]:
 cmd=['g++','-std=c++20','-O0','-ffunction-sections','-fdata-sections','-Wl,--gc-sections','-Isrc','-Isrc/univalue/include',product,*sources,'controller.cpp','-o',label]
 p=subprocess.run(cmd,cwd=r,capture_output=True,text=True);(r/(label+'-compile.log')).write_text(p.stdout+p.stderr);p.check_returncode()
 p=subprocess.run([str(r/label),str(r/(label+'-fixture'))],cwd=r,capture_output=True,text=True)
 rows.append({'variant':label,'exit':p.returncode,'stdout':p.stdout,'stderr':p.stderr,'command':cmd,'binary_sha256':hashlib.sha256((r/label).read_bytes()).hexdigest()})
(r/'results.json').write_text(json.dumps({'platform':platform.platform(),'compiler':subprocess.check_output(['g++','--version'],text=True),'results':rows},indent=2))
assert rows[0]['exit']==7 and 'FAIL previous destination' in rows[0]['stderr']
assert rows[1]['exit']==0
