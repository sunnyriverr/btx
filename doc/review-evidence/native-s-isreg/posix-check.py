from pathlib import Path
import json,subprocess,hashlib,datetime,platform,shutil
P=Path(__file__).resolve().parent;D=P/'posix';D.mkdir(exist_ok=True);(D/'src/compat/mingw').mkdir(parents=True,exist_ok=True)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
compiler=subprocess.check_output(['xcrun','--find','clang++'],text=True).strip();fixture=P/'file-type-check.cpp';logs=[]
def run(label,cmd):
 z=subprocess.run(cmd,cwd=D,capture_output=True,timeout=90);f=D/(label+'.log');f.write_bytes(z.stdout+z.stderr);row={'label':label,'command':cmd,'exit':z.returncode,'log_sha256':sha(f)};logs.append(row);assert z.returncode==0,(label,z.stderr.decode(errors='replace')[-2500:]);return z.stdout
flags=[compiler,'-std=c++20','-Wall','-Wextra','-Werror','-I'+str(D/'src')];results={}
for variant in ['baseline','candidate']:
 header=D/'src/compat/mingw/posix_extra.h';header.write_bytes((P/(variant+'.h')).read_bytes());exe=D/variant
 run(variant+'-build',flags+[str(fixture),'-o',str(exe)]);normal=run(variant+'-run',[str(exe),str(D/(variant+'-files'))]).decode();assert 'RESULT checks=23 failures=0' in normal,normal
 predefined=D/(variant+'-predefined');run(variant+'-predefined-build',flags+['-DTEST_EXISTING_PREDICATE',str(fixture),'-o',str(predefined)]);control=run(variant+'-predefined-run',[str(predefined)]).decode();assert 'RESULT checks=2 failures=0'in control
 output=run(variant+'-preprocessed',flags+['-E','-P',str(fixture)]);macros=run(variant+'-macros',flags+['-E','-dM',str(fixture)]).decode();predicate=[line for line in macros.splitlines()if line.startswith('#define S_ISREG(')];assert len(predicate)==1
 results[variant]={'normal':normal,'predefined':control,'executable_sha256':sha(exe),'predefined_executable_sha256':sha(predefined),'preprocessed_sha256':hashlib.sha256(output).hexdigest(),'system_macro':predicate[0]}
assert results['baseline']['normal']==results['candidate']['normal'];assert results['baseline']['preprocessed_sha256']==results['candidate']['preprocessed_sha256'];assert results['baseline']['system_macro']==results['candidate']['system_macro']
proof={'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'platform':platform.platform(),'architecture':platform.machine(),'compiler':subprocess.check_output([compiler,'--version'],text=True),'fixture_sha256':sha(fixture),'base':json.loads((P/'source-manifest.json').read_text())['base'],'results':results,'commands':logs,'posix_preprocessed_program_identical':True,'system_predicate_unchanged':True,'fixture_directories_removed':not any((D/(v+'-files')).exists()for v in ['baseline','candidate']),'scope':'Actual system lstat/S_ISREG and unchanged storage file-type predicate on Mac, actual regular/directory/file-dir-dangling symlink controls; not whole ModelStore materialization or native Linux'};(P/'posix-verification.json').write_text(json.dumps(proof,indent=2)+'\n');print(json.dumps({k:v for k,v in proof.items()if k not in ['commands','compiler','results']},indent=2));print(results['candidate']['normal'])
