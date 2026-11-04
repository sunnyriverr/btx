"""Native valid-control build; no project cache, dependency download or hostile worker."""
import hashlib,json,os,platform,shutil,subprocess,sys,tempfile,time
from pathlib import Path
P=Path(__file__).resolve().parent
ROOT=Path.cwd();OUT=ROOT/'accounting-smoke-results';OUT.mkdir(exist_ok=True)
records=[]
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def run(name,args,timeout=60):
    start=time.monotonic()
    row={'name':name,'argv':[str(x) for x in args],'returncode':None,'log':name+'.log'}
    records.append(row)
    try:z=subprocess.run(row['argv'],cwd=OUT,capture_output=True,text=True,timeout=timeout)
    except subprocess.TimeoutExpired as error:
        def text(value):return value.decode(errors='replace') if isinstance(value,bytes) else value or ''
        (OUT/(name+'.log')).write_text(text(error.stdout)+text(error.stderr))
        row.update(timed_out=True,elapsed_seconds=time.monotonic()-start)
        raise
    (OUT/(name+'.log')).write_text(z.stdout+z.stderr)
    row.update(returncode=z.returncode,elapsed_seconds=time.monotonic()-start)
    if z.returncode:raise RuntimeError(name+' returned '+str(z.returncode))
    return z
try:
    manifest=json.loads((P/'inputs.json').read_text())
    for n,h in manifest['files'].items():assert sha(ROOT/n)==h,n
    assert os.name=='nt','Requires native Windows'
    cl=shutil.which('cl.exe');assert cl,'VS tool environment not initialized'
    flags=['/nologo','/std:c++20','/EHsc','/O2','/MT','/W4','/DWIN32','/D_WINDOWS','/DUNICODE','/D_UNICODE','/utf-8','/Zc:preprocessor','/Zc:__cplusplus','/sdl','/D_WIN32_WINNT=0x0A00','/D_WIN32_IE=0x0A00','/DNOMINMAX','/DWIN32_LEAN_AND_MEAN','/I'+str(ROOT/'src')]
    run('build-worker',[cl,*flags,str(P/'worker.cpp'),'/Fe:worker.exe'])
    run('build-component',[cl,*flags,str(P/'smoke.cpp'),str(ROOT/'src/modelnet/swarm_windows_sandbox.cpp'),str(ROOT/'src/modelnet/swarm_confine.cpp'),str(ROOT/'src/modelnet/swarm_fsjail.cpp'),str(ROOT/'src/crypto/sha384.cpp'),'/Fe:smoke.exe','/link','userenv.lib','advapi32.lib','bcrypt.lib','ole32.lib'])
    profiles=Path(os.environ['LOCALAPPDATA'])/'Packages'
    before={x.name for x in profiles.glob('btx.native.*')}
    owned=Path(tempfile.mkdtemp(prefix='btx-accounting-valid-'))
    try:
        try:run('valid-native-output',[OUT/'smoke.exe',OUT/'worker.exe',owned/'first'],timeout=20)
        except Exception:
            # The wrapper deliberately maps backend setup errors to JAIL_ABSENT.
            # Inspect a fresh identical-policy backend invocation without relaxing it.
            try:run('direct-backend-diagnostic',[OUT/'smoke.exe',OUT/'worker.exe',owned/'diagnostic','backend'],timeout=20)
            except Exception:pass
            raise
        run('fresh-native-output',[OUT/'smoke.exe',OUT/'worker.exe',owned/'fresh'],timeout=20)
    finally:shutil.rmtree(owned)
    remaining={x.name for x in profiles.glob('btx.native.*')}-before
    assert not remaining,'New profile directories remain: '+str(sorted(remaining))
    result={'verdict':'PASS','scope':'Unchanged accepted wrapper/backend; two finite valid native AppContainer outputs. Not resource-overrun/rejection or full-node proof.','os':platform.platform(),'machine':platform.machine(),'source':manifest,'records':records,'binaries':{n:sha(OUT/n) for n in ['smoke.exe','worker.exe']},'fixture_hashes':{n:sha(P/n) for n in ['worker.cpp','smoke.cpp','run.py']},'cleanup':'Owned fixture root removed; successful backend cleanup required by JAILED return; no new btx.native.* directories observed','native_profile_glob_limit':'Directory observation only, not registry/profile enumeration'}
except Exception as e:
    result={'verdict':'FAIL','scope':'Build/setup/valid-control failure requires classification; no resource defect inferred','error':str(e),'records':records,'os':platform.platform()}
    (OUT/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2));sys.exit(1)
(OUT/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
