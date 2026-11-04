from pathlib import Path
import datetime,hashlib,json,os,platform,subprocess,sys,tempfile,shutil
P=Path(__file__).resolve().parent
source=Path(sys.argv[1]).resolve();out=Path(sys.argv[2]).resolve();variant=sys.argv[3]
compiler=sys.argv[4] if len(sys.argv)>4 else ('clang-cl' if os.name=='nt' else 'clang++')
out.mkdir(parents=True,exist_ok=True)
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
unit=P/(variant+'.cpp')
sources=[unit,P/'controls.cpp']+[source/'src'/f for f in ['univalue/lib/univalue.cpp','univalue/lib/univalue_get.cpp','univalue/lib/univalue_read.cpp','univalue/lib/univalue_write.cpp','crypto/sha384.cpp','crypto/hex_base.cpp','util/strencodings.cpp','modelnet/types.cpp']]
exe=out/('component.exe' if os.name=='nt' else 'component')
includes=[source/'src',source/'src/univalue/include']
if os.name=='nt':
 includes=[source/'src/compat/msvc',source/'src/compat/mingw']+includes
 command=[compiler,'/nologo','/std:c++20','/EHsc','/O2','/MT','/DWIN32','/DNOMINMAX','/D_CRT_SECURE_NO_WARNINGS']+['/I'+str(p) for p in includes]+['/FI'+str(source/'src/compat/mingw/posix_extra.h')]+list(map(str,sources))+['/Fe'+str(exe),'/link','ws2_32.lib']
else:
 command=[compiler,'-std=c++20','-O2']+['-I'+str(p) for p in includes]+list(map(str,sources))+['-o',str(exe)]
receipt={'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'platform':platform.platform(),'variant':variant,'compiler':compiler,'command':command,'cwd':str(out),'sources':{str(p):sha(p) for p in sources},'status':'IN_PROGRESS'}
scratch=None;parent_env=dict(os.environ)
try:
 with (out/'build.log').open('wb') as log: build=subprocess.run(command,cwd=out,stdout=log,stderr=subprocess.STDOUT,timeout=180)
 receipt['build_exit']=build.returncode
 if build.returncode:raise RuntimeError('component build failed; retained build.log')
 receipt['binary_sha256_before_execution']=sha(exe)
 scratch=Path(tempfile.mkdtemp(prefix='btx-eval-control-',dir=out))
 run=subprocess.run([str(exe),str(scratch)],cwd=out,capture_output=True,timeout=30)
 (out/'run.log').write_bytes(run.stdout+run.stderr);receipt['run_exit']=run.returncode
 receipt['scratch_empty']=not any(scratch.iterdir());receipt['parent_environment_unchanged']=dict(os.environ)==parent_env
 text=run.stdout.decode(errors='replace');failed=[s for s in text.splitlines() if s.startswith('FAIL ')]
 if variant=='mutant':
  if run.returncode!=1 or failed!=['FAIL Windows caller-shaped job terminal FAILED']:raise RuntimeError('state mutant did not fail only terminal-state control')
  receipt['status']='EXPECTED_STATE_MUTANT_REJECTED'
 elif run.returncode or 'failures=0' not in text:raise RuntimeError('valid component control failed')
 else:receipt['status']='PASS'
 if not receipt['scratch_empty'] or not receipt['parent_environment_unchanged']:raise RuntimeError('component cleanup/environment control failed')
 if sha(exe)!=receipt['binary_sha256_before_execution']:raise RuntimeError('executed binary changed')
except BaseException as ex:
 receipt['status']='ERROR';receipt['error']=type(ex).__name__+': '+str(ex);raise
finally:
 if scratch and scratch.exists():
  receipt['scratch_remaining_before_cleanup']=[x.name for x in scratch.iterdir()];shutil.rmtree(scratch)
 receipt['logs']={p.name:sha(p) for p in out.glob('*.log')}
 (out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
 print(json.dumps({k:receipt.get(k) for k in ['variant','compiler','status','build_exit','run_exit','error']}))
