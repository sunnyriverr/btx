from pathlib import Path
import subprocess,json
r=Path(__file__).resolve().parent;ctx=json.load(open(r/'build-context.json'));s=Path(ctx['source']);o=r/'current/src';b=r.parent/'pr794-real-node-recovery/build';
files=[o/f for f in ['modelnet/package_execute.cpp','modelnet/package_install.cpp','modelnet/transfer_session.cpp','crypto/sha384.cpp','crypto/hex_base.cpp','util/time.cpp']]+[s/'modelnet/types.cpp',r/'acquisition-call.cpp']
cmd=['clang++','-std=c++20','-O0','-ffunction-sections','-fdata-sections','-Wl,-dead_strip','-I'+str(o),'-I'+str(s/'src')]
# s is checkout root
files[-2]=s/'src/modelnet/types.cpp'
cmd+=['-I'+str(s/'src/univalue/include'),'-I'+str(b/'src')]+[str(f) for f in files]+[str(b/'src/univalue/libunivalue.a'),'-o',str(r/'acquisition-call')]
(r/'compile-command.json').write_text(json.dumps(cmd));p=subprocess.run(cmd,capture_output=True,text=True);(r/'call-compile.log').write_text(p.stdout+p.stderr);print((p.stdout+p.stderr)[-6000:]);p.check_returncode()
