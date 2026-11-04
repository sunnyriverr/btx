"""Native original/candidate pair, real source, identical driver, no API shim."""
from pathlib import Path
import hashlib,json,os,platform,shutil,subprocess,sys,tempfile,time
P=Path(__file__).resolve().parent;ROOT=Path.cwd();OUT=ROOT/'windows-environment-results'
OUT.mkdir(exist_ok=True);records=[];cases=[];identities={};owned=None
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def save():
    (OUT/'identities.json').write_text(json.dumps(identities,indent=2)+'\n')
    (OUT/'commands.json').write_text(json.dumps(records,indent=2)+'\n')
def run(label,args,cwd=OUT,env=None,timeout=60):
    row={'label':label,'argv':[str(x) for x in args],'cwd':str(cwd),'exit':None}
    records.append(row);save();start=time.monotonic()
    try:z=subprocess.run(row['argv'],cwd=cwd,env=env,capture_output=True,text=True,timeout=timeout)
    except subprocess.TimeoutExpired as error:
        def text(value):return value.decode(errors='replace') if isinstance(value,bytes) else value or ''
        output=text(error.stdout)+text(error.stderr);(OUT/(label+'.log')).write_text(output)
        row.update(timed_out=True,seconds=time.monotonic()-start,log_sha256=sha(OUT/(label+'.log')));save();raise
    (OUT/(label+'.log')).write_text(z.stdout+z.stderr)
    row.update(exit=z.returncode,seconds=time.monotonic()-start,log_sha256=sha(OUT/(label+'.log')));save();return z
def require_build(label,args,cwd):
    z=run(label,args,cwd);assert z.returncode==0,label+' failed'
def check(label,args,expected,need,env):
    z=run(label,args,env=env,timeout=20)
    ok=z.returncode==expected and all(token in z.stdout for token in need)
    cases.append({'label':label,'expected_exit':expected,'actual_exit':z.returncode,'required_tokens':need,'pass':ok})
    assert ok,label+' result does not match expected state'
try:
    assert os.name=='nt'
    manifest=json.loads((P/'inputs.json').read_text())
    for name,digest in manifest['files'].items():assert sha(ROOT/name)==digest,name
    assert sha(P/'baseline-windows-sandbox.cpp')==manifest['baseline_backend_sha256']
    assert (P/'smoke.cpp').read_bytes().find(b'LOCALAPPDATA_CONTROL')<0
    assert not any((P/n).exists() for n in ['trace.h','env_probe.h'])
    identities.update(source=manifest,platform=platform.platform(),machine=platform.machine(),fixtures={x.name:sha(x) for x in P.iterdir() if x.is_file()},binaries={})
    save()
    cl=shutil.which('cl.exe');assert cl
    flags=['/nologo','/std:c++20','/EHsc','/O2','/MT','/W4','/DWIN32','/D_WINDOWS','/DUNICODE','/D_UNICODE','/utf-8','/Zc:preprocessor','/Zc:__cplusplus','/sdl','/D_WIN32_WINNT=0x0A00','/D_WIN32_IE=0x0A00','/DNOMINMAX','/DWIN32_LEAN_AND_MEAN','/I'+str(ROOT/'src')]
    for worker,source in [('worker.exe','worker.cpp'),('environment-worker.exe','environment-worker.cpp')]:
        require_build('build-'+worker,[cl,*flags,str(P/source),'/Fe:'+worker],OUT)
        identities['binaries'][worker]=sha(OUT/worker);save()
    for variant in ['baseline','candidate']:
        build=OUT/variant;build.mkdir(exist_ok=True)
        backend=P/'baseline-windows-sandbox.cpp' if variant=='baseline' else ROOT/'src/modelnet/swarm_windows_sandbox.cpp'
        args=[cl,*flags,str(P/'smoke.cpp'),str(backend),str(ROOT/'src/modelnet/swarm_confine.cpp'),str(ROOT/'src/modelnet/swarm_fsjail.cpp'),str(ROOT/'src/crypto/sha384.cpp'),'/Fe:smoke.exe','/link','userenv.lib','advapi32.lib','bcrypt.lib','ole32.lib']
        require_build('build-'+variant,args,build)
        identities['binaries'][variant+'/smoke.exe']=sha(build/'smoke.exe');save()
    fixture_env=dict(os.environ)
    fixture_env.pop('BTX_ACCOUNTING_LOCALAPPDATA_CONTROL',None)
    fixture_env['BTX_ENV_PARENT_SENTINEL']='finite-nonsecret-fixture-marker'
    profiles=Path(os.environ['LOCALAPPDATA'])/'Packages'
    before={x.name for x in profiles.glob('btx.native.*')}
    owned=Path(tempfile.mkdtemp(prefix='btx-env-pair-'))
    worker=OUT/'worker.exe';driver_before=OUT/'baseline/smoke.exe';driver_after=OUT/'candidate/smoke.exe'
    check('baseline-valid',[driver_before,worker,owned/'before'],1,['code=JAIL_ABSENT','launched=0','output_bytes=0','inputs_unchanged=1'],fixture_env)
    check('baseline-direct',[driver_before,worker,owned/'before-direct','backend'],1,['code=WINDOWS_SANDBOX_CREATEPROCESS','launched=0','output_bytes=0','inputs_unchanged=1'],fixture_env)
    good=['code=JAILED','launched=1','child=0','output_bytes=512','output_ok=1','inputs_unchanged=1','verdict=PASS']
    check('candidate-valid',[driver_after,worker,owned/'after'],0,good,fixture_env)
    check('candidate-parent-sentinel-excluded',[driver_after,OUT/'environment-worker.exe',owned/'private-environment'],0,good,fixture_env)
    missing=dict(fixture_env)
    for key in list(missing):
        if key.upper()=='LOCALAPPDATA':del missing[key]
    check('candidate-missing-profile-value',[driver_after,worker,owned/'missing','backend'],1,['code=WINDOWS_SANDBOX_ENVIRONMENT','launched=0','output_bytes=0','inputs_unchanged=1'],missing)
    check('candidate-fresh-after-refusal',[driver_after,worker,owned/'fresh-after-refusal'],0,good,fixture_env)
    remaining=sorted({x.name for x in profiles.glob('btx.native.*')}-before)
    assert not remaining,'New matching profile directories remain'
    identities['binary_hashes_still_match']=all(sha(OUT/name)==digest for name,digest in identities['binaries'].items())
    assert identities['binary_hashes_still_match']
    verdict='PASS';error=None
except Exception as exc:verdict='FAIL';error=str(exc)
finally:
    cleanup='No temporary root created'
    if owned is not None:
        try:shutil.rmtree(owned);cleanup='Owned temporary root removed'
        except Exception as exc:verdict='FAIL';error=str(exc);cleanup='Owned fixture cleanup failed'
    save()
    result={'verdict':verdict,'error':error,'cases':cases,'cleanup':cleanup,'identities':'identities.json','commands':'commands.json','no_API_environment_injection':True,'scope':'Native Windows component source comparison; not full node/cap02 CLI, resource accounting, Windows11 or release qualification','profile_observation':'No new btx.native.* directories after completed tests' if verdict=='PASS' else 'Not established'}
    (OUT/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
sys.exit(0 if verdict=='PASS' else 1)
