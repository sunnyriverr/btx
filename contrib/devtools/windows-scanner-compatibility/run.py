"""Bounded native scanner API probe around an unchanged accepted backend."""
from pathlib import Path
import hashlib,json,os,platform,shutil,subprocess,sys,tempfile,time
P=Path(__file__).resolve().parent;ROOT=Path.cwd();OUT=ROOT/'windows-scanner-results'
OUT.mkdir(exist_ok=True);commands=[];identities={};owned=None;verdict='FAIL';error=None
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save():
    (OUT/'commands.json').write_text(json.dumps(commands,indent=2)+'\n')
    (OUT/'identities.json').write_text(json.dumps(identities,indent=2)+'\n')
def run(label,args,cwd=OUT,timeout=90):
    r={'label':label,'argv':[str(a) for a in args],'cwd':str(cwd),'exit':None};commands.append(r);save();start=time.monotonic()
    try:
        z=subprocess.run(r['argv'],cwd=cwd,capture_output=True,text=True,timeout=timeout)
        log=z.stdout+z.stderr;r['exit']=z.returncode
    except subprocess.TimeoutExpired as e:
        def text(x):return x.decode(errors='replace') if isinstance(x,bytes) else x or ''
        log=text(e.stdout)+text(e.stderr);r['timed_out']=True
        (OUT/(label+'.log')).write_text(log);r['seconds']=time.monotonic()-start;save();raise
    (OUT/(label+'.log')).write_text(log);r['seconds']=time.monotonic()-start;r['log_sha256']=sha(OUT/(label+'.log'));save();return z
try:
    assert os.name=='nt'
    manifest=json.loads((P/'inputs.json').read_text())
    for name,digest in manifest['files'].items():assert sha(ROOT/name)==digest,name
    identities={'accepted_source':manifest,'platform':platform.platform(),'machine':platform.machine(),
        'fixtures':{x.name:sha(x) for x in P.iterdir() if x.is_file()},'binaries':{}}
    cl=shutil.which('cl.exe');assert cl
    flags=['/nologo','/std:c++20','/EHsc','/O2','/MT','/W4','/DWIN32','/D_WINDOWS','/DUNICODE','/D_UNICODE','/utf-8',
        '/Zc:preprocessor','/Zc:__cplusplus','/sdl','/D_WIN32_WINNT=0x0A00','/D_WIN32_IE=0x0A00','/DNOMINMAX','/DWIN32_LEAN_AND_MEAN','/I'+str(ROOT/'src')]
    for name,source in [('worker.exe',[P/'worker.cpp']),('probe.exe',[P/'probe.cpp',ROOT/'src/modelnet/swarm_windows_sandbox.cpp',
        ROOT/'src/modelnet/swarm_confine.cpp',ROOT/'src/modelnet/swarm_fsjail.cpp',ROOT/'src/crypto/sha384.cpp'])]:
        build=OUT/name.replace('.exe','');build.mkdir(exist_ok=True)
        args=[cl,*flags,*source,'/Fe:'+str(OUT/name)]
        if name=='probe.exe':args+=['/link','userenv.lib','advapi32.lib','bcrypt.lib','ole32.lib']
        z=run('build-'+name,args,cwd=build);assert z.returncode==0,'build failed: '+name
        identities['binaries'][name]=sha(OUT/name);save()
    profiles=Path(os.environ['LOCALAPPDATA'])/'Packages';before={x.name for x in profiles.glob('btx.native.*')}
    owned=Path(tempfile.mkdtemp(prefix='btx-scanner-compat-'));root=owned/'finite';root.mkdir()
    shutil.copyfile(OUT/'worker.exe',root/'worker.exe');(root/'input.bin').write_bytes(b'finite-immutable-input\n')
    inputs={x.name:sha(x) for x in root.iterdir() if x.is_file()}
    z=run('native-probe',[OUT/'probe.exe',root,root/'worker.exe'],timeout=90)
    checks=[line for line in z.stdout.splitlines() if line.startswith('CHECK ')]
    identities['original_inputs_unchanged']=all(sha(root/n)==h for n,h in inputs.items())
    identities['binary_hashes_unchanged']=all(sha(OUT/n)==h for n,h in identities['binaries'].items())
    new_profiles=sorted({x.name for x in profiles.glob('btx.native.*')}-before)
    assert identities['original_inputs_unchanged'] and identities['binary_hashes_unchanged']
    assert not new_profiles,'new matching profile directories remain: '+repr(new_profiles)
    assert z.returncode==0 and 'VERDICT PASS' in z.stdout,'scanner compatibility not established; see native-probe.log'
    expected=['initial-nested-enumeration','exclusive-writer-live-size','content-reader-sharing-control','directory-rename-with-monitor-handle',
        'directory-and-file-deletion','post-rename-rescan','closed-file-content-and-size','owned-staged-root-cleanup','real-backend-output']
    assert all(any(line.startswith('CHECK '+name+' PASS') for line in checks) for name in expected)
    verdict='PASS'
except Exception as e:error=str(e)
finally:
    cleanup='No owned temporary root created'
    if owned is not None:
        try:shutil.rmtree(owned);cleanup='Owned original fixture root removed'
        except Exception as e:verdict='FAIL';error=str(e);cleanup='Owned fixture cleanup failed'
    save()
    result={'verdict':verdict,'error':error,'cleanup':cleanup,'cases':locals().get('checks',[]),
        'profile_directories_remaining':locals().get('new_profiles',None),'scope':'Windows Server native scanner compatibility with ordinary worker through unchanged accepted AppContainer wrapper/backend; not production accounting, all-filesystem support, Windows11, full-node or release qualification',
        'fixture_only':True,'production_API_shims':False}
    (OUT/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
sys.exit(0 if verdict=='PASS' else 1)
