from pathlib import Path
import json,subprocess,hashlib,re,platform,datetime
P=Path(__file__).resolve().parent;D=P/'posix';R=Path('/Users/wildwood/Documents/Playground/work/btx-review-tools/toolchain-2026-10-31/source');manifest=json.loads((P/'source-manifest.json').read_text());base=manifest['base']
def sha(b):return hashlib.sha256(b).hexdigest()
commands=[]
def run(label,cmd):
 z=subprocess.run(cmd,cwd=D,capture_output=True,timeout=90);(D/(label+'.log')).write_bytes(z.stdout+z.stderr);commands.append({'label':label,'command':cmd,'exit':z.returncode,'log_sha256':sha(z.stdout+z.stderr)});assert z.returncode==0,(label,(z.stdout+z.stderr).decode(errors='replace')[-3000:]);return z.stdout
compiler=subprocess.check_output(['xcrun','--find','clang++'],text=True).strip();flags=[compiler,'-std=c++20','-Wall','-Wextra','-Werror','-I'+str(D/'src'),'-I'+str(D/'src/univalue/include')];results={}
for variant in ['baseline','candidate']:
 (D/'src/modelnet/supervisor.h').write_bytes((P/(variant+'.h')).read_bytes());exe=D/variant
 run(variant+'-build',flags+['-Xclang','-fdump-record-layouts','header-first.cpp','-o',str(exe)]);out=run(variant+'-run',[str(exe)]).decode();ast=run(variant+'-ast',flags+['-Xclang','-ast-dump','-Xclang','-ast-dump-filter=modelnet::HelperSupervisor','-fsyntax-only','header-first.cpp']).decode()
 pid=[s for s in ast.splitlines() if 'FieldDecl' in s and ' m_pid ' in s];assert len(pid)==1 and "'pid_t':'int'" in pid[0],pid
 pre=run(variant+'-preprocessed',flags+['-E','-P','header-first.cpp']).decode();start=pre.index('class HelperSupervisor {');end=pre.index('\n};',start)+3;class_tokens=pre[start:end]
 results[variant]={'runtime':out,'member_ast':pid[0],'class_tokens_sha256':sha(class_tokens.encode()),'binary_sha256':sha(exe.read_bytes()),'header_sha256':sha((D/'src/modelnet/supervisor.h').read_bytes())}
assert results['baseline']['runtime']==results['candidate']['runtime'];assert results['baseline']['class_tokens_sha256']==results['candidate']['class_tokens_sha256']
# All process-handling implementation is exactly the accepted source; no lifecycle code is changed.
cpp=subprocess.check_output(['git','-C',str(R),'show',base+':src/modelnet/supervisor.cpp']);(D/'supervisor.cpp').write_bytes(cpp)
proof={'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'base':base,'platform':platform.platform(),'architecture':platform.machine(),'compiler':run('compiler-version',[compiler,'--version']).decode(),'scope':'Actual nine-header dependency closure, first include compile/link/run and compiler AST/layout on Mac; no supervisor lifecycle execution or Linux result','results':results,'commands':commands,'posix_preprocessed_class_identical':True,'posix_member_still_pid_t':True,'supervisor_cpp_sha256':sha(cpp),'headers':{str(f.relative_to(D)):sha(f.read_bytes()) for f in (D/'src').rglob('*') if f.is_file()}}
(P/'posix-verification.json').write_text(json.dumps(proof,indent=2)+'\n');print(json.dumps({k:v for k,v in proof.items() if k not in ['commands','headers','compiler']},indent=2))
