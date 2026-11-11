from pathlib import Path
import os,sys,json,subprocess,hashlib,datetime,time,urllib.request,shutil
P=Path(__file__).resolve().parent
BASE='c6f9678dd225572528d06c456c16eb4c78bc637c'
VCPKG_COMMIT='afa249f12f52ed8a3b919f195495ba8b330288d1'
OPENSSL_SHA='967311f84955316969bdb1d8d4b983718ef42338639c621ec4c34fddef355e99'
ROOT=Path(os.environ['BTX_NATIVE_ROOT']);SOURCE=Path(os.environ['GITHUB_WORKSPACE'])/'btx'
E=ROOT/'evidence';E.mkdir(parents=True,exist_ok=True);STATE=E/'result.json'
result=json.loads(STATE.read_text())if STATE.exists()else{'base':BASE,'scope':'Exact native Windows bridge unit translation-unit comparison','status':'IN_PROGRESS','commands':[],'stages':{},'product_fixes':[],'planned_test_source_fix':'src/test/modelnet_bridge_tests.cpp','whole_node_build_run':False,'unit_test_execution':False,'PR397_in_upstream':True,'compiler_env':{k:os.environ.get(k)for k in ['VCToolsVersion','WindowsSDKVersion','ImageVersion','PROCESSOR_ARCHITECTURE']}}
EXPECTED_WORKING_BLOBS={}
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save():
 result['updated_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat();STATE.write_text(json.dumps(result,indent=2)+'\n')
def run(label,command,cwd=ROOT,timeout=1800):
 log=E/(label+'.log');start=time.monotonic();timed_out=False
 with log.open('wb')as out:
  proc=subprocess.Popen(command,cwd=cwd,stdout=out,stderr=subprocess.STDOUT)
  while proc.poll()is None:
   if time.monotonic()-start>timeout:
    cleanup=subprocess.run(['taskkill','/PID',str(proc.pid),'/T','/F'],capture_output=True)
    (E/(label+'-timeout-cleanup.log')).write_bytes(cleanup.stdout+cleanup.stderr)
    proc.wait(timeout=30);timed_out=True;break
   time.sleep(2)
 result['commands'].append({'label':label,'command':command,'cwd':str(cwd),'exit':proc.returncode,'seconds':round(time.monotonic()-start,2),'timed_out':timed_out,'log_sha256':sha(log)});save();print(label,proc.returncode,log.read_text(errors='replace')[-6500:],flush=True)
 if timed_out:raise TimeoutError(label+' timed out; owned process tree terminated and log retained')
 return proc.returncode
def need(label,command,cwd=ROOT,timeout=1800):
 if run(label,command,cwd,timeout):raise RuntimeError(label+' failed; see original log')
def source_identity(label):
 head=subprocess.check_output(['git','-C',str(SOURCE),'rev-parse','HEAD']).decode().strip()
 if head!=BASE:raise RuntimeError('wrong source HEAD')
 tree=subprocess.check_output(['git','-C',str(SOURCE),'ls-tree','-rz','--full-tree',BASE]);entries={}
 for record in tree.split(b'\0'):
  if not record:continue
  meta,name=record.split(b'\t',1);mode,kind,oid=meta.decode().split()
  if kind!='blob':raise RuntimeError('unexpected gitlink')
  name=name.decode();path=SOURCE/name
  if mode=='120000':
   expected=subprocess.check_output(['git','-C',str(SOURCE),'cat-file','blob',oid])
   if path.is_symlink():
    data=os.readlink(path).replace('\\','/').encode()
    if data!=expected:raise RuntimeError('symlink target differs: '+name)
    entries[name]={'git_mode':mode,'git_blob':oid,'checkout_kind':'symlink','target':data.decode(),'resolved_sha256':sha(path)if path.is_file()else None}
   else:
    data=path.read_bytes()
    if data!=expected:raise RuntimeError('symlink placeholder differs: '+name)
    entries[name]={'git_mode':mode,'git_blob':oid,'checkout_kind':'link_placeholder','target':data.decode(),'working_sha256':sha(path)}
   continue
  if path.is_symlink():raise RuntimeError('unexpected symlink for regular Git blob: '+name)
  data=path.read_bytes();raw=hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()
  if raw!=EXPECTED_WORKING_BLOBS.get(name,oid):raise RuntimeError('working bytes differ: '+name)
  entries[name]={'git_mode':mode,'git_blob':oid,'expected_working_blob':EXPECTED_WORKING_BLOBS.get(name,oid),'working_sha256':hashlib.sha256(data).hexdigest()}
 target=E/(label+'-source.json');target.write_text(json.dumps({'head':head,'files':entries},indent=2)+'\n');result[label+'_source_sha256']=sha(target);result[label+'_tracked_files']=len(entries)
def metadata():
 result['compiler_env']={k:os.environ.get(k) for k in ['VCToolsVersion','WindowsSDKVersion','ImageVersion','PROCESSOR_ARCHITECTURE']}
 source_identity('before')
 for label,cmd in [('cmake-version',['cmake','--version']),('ninja-version',['ninja','--version']),('clang-version',['clang-cl','--version'])]:need(label,cmd)
 run('cl-version',['cl','/Bv']);result['resolved_tools']={x:shutil.which(x)for x in ['cl','clang-cl','cmake','ninja','perl','nasm','nmake','dumpbin']}
 if any(not v for v in result['resolved_tools'].values()):raise RuntimeError('required native setup tool missing')
def openssl():
 prefix=ROOT/'openssl-3.5.4-static';metadata();archive=ROOT/'openssl-3.5.4.tar.gz';cached=(prefix/'lib/libcrypto.lib').exists()
 if cached:
  receipt=prefix/'btx-build-provenance.json'
  if not receipt.exists():raise RuntimeError('incomplete OpenSSL cache; no provenance')
  prior=json.loads(receipt.read_text())
  if prior['source_sha256']!=OPENSSL_SHA or prior['toolset']!=os.environ.get('VCToolsVersion'):raise RuntimeError('cached OpenSSL source/toolset mismatch')
  for f,h in prior['files'].items():
   if sha(prefix/f)!=h:raise RuntimeError('cached OpenSSL library/header mismatch')
  if sha(prefix/'btx-Makefile.txt')!=prior['makefile_sha256']:raise RuntimeError('cached OpenSSL Makefile mismatch')
  shutil.copyfile(prefix/'btx-Makefile.txt',E/'openssl-Makefile.txt')
 result['openssl_cache_reused']=cached
 if not archive.exists():urllib.request.urlretrieve('https://github.com/openssl/openssl/releases/download/openssl-3.5.4/openssl-3.5.4.tar.gz',archive)
 if sha(archive)!=OPENSSL_SHA:raise RuntimeError('OpenSSL official source digest mismatch')
 result['openssl_source_sha256']=sha(archive)
 if not(prefix/'lib/libcrypto.lib').exists():
  unpack=ROOT/'openssl-source';unpack.mkdir(exist_ok=True);need('openssl-extract',['tar','-xzf',str(archive),'-C',str(unpack)]);source=unpack/'openssl-3.5.4'
  need('openssl-configure',['perl','Configure','VC-WIN64A','no-shared','no-tests','--prefix='+prefix.as_posix(),'--openssldir='+(prefix/'ssl').as_posix(),'--libdir=lib'],source)
  need('openssl-build',['nmake','/S','build_sw'],source,1200);need('openssl-install',['nmake','/S','install_sw'],source,180);shutil.copyfile(source/'Makefile',E/'openssl-Makefile.txt');need('openssl-configdata',['perl','configdata.pm','--dump'],source)
 need('openssl-version',[str(prefix/'bin/openssl.exe'),'version','-a'])
 probe=E/'openssl_probe.c';probe.write_text((P/'openssl_probe.c').read_text());exe=E/'openssl_probe.exe'
 need('openssl-probe-build',['cl','/nologo','/MT','/O2','/I'+str(prefix/'include'),str(probe),'/Fe'+str(exe),'/Fo'+str(E/'openssl_probe.obj'),'/link','/LIBPATH:'+str(prefix/'lib'),'libssl.lib','libcrypto.lib','ws2_32.lib','gdi32.lib','advapi32.lib','crypt32.lib','user32.lib'])
 need('openssl-probe-run',[str(exe)]);need('openssl-probe-dependents',['dumpbin','/dependents',str(exe)]);deps=(E/'openssl-probe-dependents.log').read_text(errors='replace').lower()
 if any(x in deps for x in ['libcrypto-','libssl-','vcruntime']):raise RuntimeError('unexpected dynamic dependency in static OpenSSL smoke')
 result['openssl_prefix']=str(prefix);result['openssl_files']={f:sha(prefix/f)for f in ['include/openssl/opensslv.h','lib/libssl.lib','lib/libcrypto.lib','bin/openssl.exe']};result['openssl_probe_executable_sha256']=sha(exe)
 if not cached:
  shutil.copyfile(E/'openssl-Makefile.txt',prefix/'btx-Makefile.txt')
  (prefix/'btx-build-provenance.json').write_text(json.dumps({'source_sha256':OPENSSL_SHA,'toolset':os.environ.get('VCToolsVersion'),'files':result['openssl_files'],'configuration':'VC-WIN64A no-shared no-tests, libdir=lib; staticCRT per pinned OpenSSL config','makefile_sha256':sha(E/'openssl-Makefile.txt')},indent=2)+'\n')

def bootstrap():
    tool = ROOT / 'vcpkg'
    need('vcpkg-clone', ['git','clone','--no-checkout','https://github.com/microsoft/vcpkg.git',str(tool)], timeout=300)
    need('vcpkg-checkout', ['git','-C',str(tool),'checkout','--detach',VCPKG_COMMIT], timeout=120)
    assert subprocess.check_output(['git','-C',str(tool),'rev-parse','HEAD'], text=True).strip() == VCPKG_COMMIT
    assert 'VCPKG_TOOL_RELEASE_TAG=2026-10-29' in (tool/'scripts/vcpkg-tool-metadata.txt').read_text()
    url = 'https://github.com/microsoft/vcpkg-tool/releases/download/2026-10-29/vcpkg.exe'
    request = urllib.request.Request(url, headers={'User-Agent': 'btx-pinned-native-tool'})
    with urllib.request.urlopen(request, timeout=90) as response:
        binary = response.read(10 * 1024 * 1024)
    assert len(binary) == 6836024 and hashlib.sha256(binary).hexdigest() == '191ee64b0887af80aad3eff6c5e888ab733d3ef2182885ed4747b4574c201834'
    (tool/'vcpkg.exe').write_bytes(binary)
    (tool/'vcpkg.disable-metrics').write_text('')
    need('vcpkg-version', [str(tool/'vcpkg.exe'),'version'])
    result['vcpkg_commit'] = VCPKG_COMMIT
    result['vcpkg_executable_sha256'] = sha(tool/'vcpkg.exe')


def compare():
    tool, prefix, build = (ROOT / d for d in ('vcpkg','openssl-3.5.4-static','project-build'))
    os.environ.update(VCPKG_ROOT=str(tool), VCPKG_DISABLE_METRICS='1', VCPKG_MAX_CONCURRENCY='4')
    args = ['cmake','--preset','windows-clangcl-static','-S',str(SOURCE),'-B',str(build),
            '-DBUILD_TESTS=ON','-DWITH_MODELNET=ON','-DENABLE_WALLET=OFF','-DWITH_ZMQ=OFF',
            '-DVCPKG_MANIFEST_NO_DEFAULT_FEATURES=ON','-DVCPKG_MANIFEST_FEATURES=tests;sqlite',
            '-DVCPKG_INSTALLED_DIR='+str(ROOT/'vcpkg-installed'),'-DOPENSSL_ROOT_DIR='+str(prefix),
            '-DOPENSSL_USE_STATIC_LIBS=ON','-DOPENSSL_MSVC_STATIC_RT=ON',
            '-DOPENSSL_INCLUDE_DIR='+str(prefix/'include'),'-DOPENSSL_SSL_LIBRARY='+str(prefix/'lib/libssl.lib'),
            '-DOPENSSL_CRYPTO_LIBRARY='+str(prefix/'lib/libcrypto.lib'),'-DCMAKE_EXPORT_COMPILE_COMMANDS=ON']
    need('root-configure', args, SOURCE, 1500)
    need('generated-targets', ['ninja','-C',str(build),'-t','targets','all'])
    target = 'src/test/CMakeFiles/test_btx.dir/modelnet_bridge_tests.cpp.obj'
    assert target + ':' in (E/'generated-targets.log').read_text()
    db = build/'compile_commands.json'
    commands = [c for c in json.loads(db.read_text()) if c['file'].endswith('modelnet_bridge_tests.cpp')]
    assert len(commands) == 1 and 'clang-cl' in commands[0]['command']
    (E/'object-command.json').write_text(json.dumps(commands[0],indent=2)+'\n')
    result['compile_db_sha256'] = sha(db)
    control = json.loads((P/'composition.json').read_text())
    mac = json.loads((P/'mac-receipt.json').read_text())
    assert control['base'] == BASE and control == mac['inputs']
    for file,digest in control['files'].items():
        before = (P/'before.cpp' if file.startswith('src/test/') else P/'http_bridge.cpp')
        assert sha(before) == digest
        (SOURCE/file).write_bytes(before.read_bytes())
        EXPECTED_WORKING_BLOBS[file] = subprocess.check_output(['git','hash-object',str(before)],text=True).strip()
    test_path = 'src/test/modelnet_bridge_tests.cpp'
    candidate = P/'after.cpp'
    assert sha(candidate) == mac['cases']['after']['test_sha256']
    result['composition'] = control
    result['before_test_sha256'] = sha(SOURCE/test_path)
    result['after_test_sha256'] = sha(candidate)
    source_identity('baseline-composed')
    command = ['cmake','--build',str(build),'--target',target,'--verbose','--','-j','1']
    before = run('baseline-unit-object', command, SOURCE, 300)
    output = (E/'baseline-unit-object.log').read_text(errors='replace')
    result['baseline_exit'] = before
    if before == 0 or "fatal error: 'unistd.h' file not found" not in output or 'modelnet_bridge_tests.cpp(' not in output:
        raise RuntimeError('baseline did not fail on the expected bridge unistd.h include')
    (SOURCE/test_path).write_bytes(candidate.read_bytes())
    EXPECTED_WORKING_BLOBS[test_path] = subprocess.check_output(['git','hash-object',str(candidate)],text=True).strip()
    source_identity('candidate-composed')
    after = run('candidate-unit-object', command, SOURCE, 300)
    result['candidate_exit'] = after
    if after or sha(db) != result['compile_db_sha256']:
        raise RuntimeError('candidate object failed or compiler configuration changed')
    result['object_sha256'] = sha(build/target)
    result['status'] = 'PASS_NATIVE_GENERATED_OBJECT'


stage = sys.argv[1]
try:
    result['stages'][stage] = 'RUNNING'
    save()
    {'openssl': openssl, 'bootstrap': bootstrap, 'compare': compare}[stage]()
    result['stages'][stage] = 'COMPLETE'
except Exception as error:
    result.update(status='FAILED', failure_stage=stage, error=repr(error))
    print(repr(error),flush=True)
    raise
finally:
    save()
