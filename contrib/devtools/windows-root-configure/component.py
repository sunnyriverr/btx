from pathlib import Path
import datetime,hashlib,json,os,platform,subprocess,sys,shutil
P=Path(__file__).resolve().parent
source=Path(sys.argv[1]).resolve(); out=Path(sys.argv[2]).resolve(); variant=sys.argv[3]
compiler=sys.argv[4] if len(sys.argv)>4 else ('clang-cl' if os.name=='nt' else 'clang++')
out.mkdir(parents=True,exist_ok=True)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
shutil.copyfile(P/(variant+'.cpp'),out/'runtime.cpp')
shutil.copyfile(P/'controls.cpp',out/'controls.cpp')
sources=[out/'controls.cpp']+[source/'src'/f for f in ['modelnet/capability_exec.cpp','modelnet/capability_types.cpp','modelnet/types.cpp','univalue/lib/univalue.cpp','univalue/lib/univalue_get.cpp','univalue/lib/univalue_read.cpp','univalue/lib/univalue_write.cpp','crypto/sha384.cpp','crypto/hex_base.cpp','util/strencodings.cpp']]
exe=out/('component.exe' if os.name=='nt' else 'component')
includes=[source/'src',source/'src/univalue/include']
if os.name=='nt':
    includes=[source/'src/compat/msvc',source/'src/compat/mingw']+includes
    command=[compiler,'/nologo','/std:c++20','/EHsc','/O2','/Gy','/MT','/DWIN32','/DNOMINMAX','/D_CRT_SECURE_NO_WARNINGS']+['/I'+str(p) for p in includes]+['/FI'+str(source/'src/compat/mingw/posix_extra.h')]+list(map(str,sources))+['/Fe'+str(exe),'/link','/OPT:REF','ws2_32.lib']
else:
    command=[compiler,'-std=c++20','-O2','-ffunction-sections','-fdata-sections']+['-I'+str(p) for p in includes]+list(map(str,sources))+['-Wl,-dead_strip','-o',str(exe)]
receipt={'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'platform':platform.platform(),'variant':variant,'compiler':compiler,'command':command,'cwd':str(out),'sources':{str(p):sha(p) for p in sources},'runtime_sha256':sha(out/'runtime.cpp'),'status':'IN_PROGRESS','randomness':'Deterministic GetRandBytes test lease fixture; production randomness not qualified'}
try:
    with (out/'build.log').open('wb') as log: build=subprocess.run(command,cwd=out,stdout=log,stderr=subprocess.STDOUT,timeout=180)
    receipt['build_exit']=build.returncode
    if build.returncode: raise RuntimeError('component build failed; retained build.log')
    receipt['binary_sha256_before_execution']=sha(exe)
    run=subprocess.run([str(exe),str(exe)],cwd=out,capture_output=True,timeout=30)
    (out/'run.log').write_bytes(run.stdout+run.stderr);receipt['run_exit']=run.returncode
    text=run.stdout.decode(errors='replace')
    if run.returncode or 'failures=0' not in text: raise RuntimeError('component controls failed')
    assert sha(exe)==receipt['binary_sha256_before_execution']
    receipt['status']='PASS'
except BaseException as ex:
    receipt['status']='ERROR';receipt['error']=type(ex).__name__+': '+str(ex);raise
finally:
    receipt['logs']={p.name:sha(p) for p in out.glob('*.log')}
    (out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps({k:receipt.get(k) for k in ['variant','compiler','status','build_exit','run_exit','error']}))
