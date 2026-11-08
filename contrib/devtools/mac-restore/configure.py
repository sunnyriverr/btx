"""Bounded setup/configuration only. Never compile BTX, run a node or publish."""
from pathlib import Path
import os,subprocess,json,hashlib,platform,shutil,sys,signal
w=Path(os.environ['GITHUB_WORKSPACE']);out=w/'mac-config-records';out.mkdir(exist_ok=True);src=w/'product';build=w/'mac-config-build';state={'expected_source':'ff5f3f04ea11f044594987fc6be043ff68b136ad','expected_image':'20261104.0514.1','openssl_version':'3.5.9','btx_compiled':False,'node_started':False,'commands':[]}
def save():(out/'result.json').write_text(json.dumps(state,indent=2)+'\n')
def command(argv,label,limit=60,env=None,cwd=None):
 print('START '+label,flush=True);save()
 p=subprocess.Popen(list(map(str,argv)),cwd=cwd,env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,start_new_session=True)
 timed=False
 try:stdout,stderr=p.communicate(timeout=limit)
 except subprocess.TimeoutExpired:
  timed=True
  try:os.killpg(p.pid,signal.SIGTERM)
  except ProcessLookupError:pass
  try:stdout,stderr=p.communicate(timeout=5)
  except subprocess.TimeoutExpired:
   try:os.killpg(p.pid,signal.SIGKILL)
   except ProcessLookupError:pass
   stdout,stderr=p.communicate()
 (out/(label+'.log')).write_text(stdout+stderr);state['commands'].append({'label':label,'args':list(map(str,argv)),'exit':p.returncode,'timed_out':timed});save()
 if timed:raise RuntimeError(label+' timed out; owned process group stopped')
 if p.returncode:raise RuntimeError(label+' failed; inspect retained log')
 return stdout

try:
 assert platform.machine()=='arm64';assert os.environ.get('ImageVersion')==state['expected_image'],'Image changed: recheck prerequisites before setup'
 assert command(['git','-C',src,'rev-parse','HEAD'],'source').strip()==state['expected_source']
 assert not command(['git','-C',src,'status','--porcelain'],'clean-source').strip()
 assert shutil.disk_usage(w).free>25*1024**3
 assert 'Xcode 16.4' in command(['xcodebuild','-version'],'xcode-version')
 assert command(['xcrun','--sdk','macosx','--show-sdk-version'],'sdk-version').strip()=='15.5'
 assert 'Apple clang version 17.0.0' in command(['xcrun','clang++','--version'],'compiler-version')
 assert command(['xcode-select','-p'],'selected-developer').strip()=='/Applications/Xcode_16.4.app/Contents/Developer'
 env=dict(os.environ,HOMEBREW_NO_AUTO_UPDATE='1',HOMEBREW_NO_INSTALL_UPGRADE='1',HOMEBREW_NO_INSTALL_CLEANUP='1')
 ssl=Path(command(['brew','--prefix','openssl@3'],'ssl-prefix',env=env).strip())
 assert command([ssl/'bin/openssl','version'],'ssl-version',env=env).startswith('OpenSSL 3.5.9 ')
 for file in [ssl/'lib/libssl.a',ssl/'lib/libcrypto.a',ssl/'include/openssl/ssl.h']:
  assert file.is_file();state.setdefault('ssl_files',{})[str(file)]={'sha256':hashlib.sha256(file.read_bytes()).hexdigest(),'bytes':file.stat().st_size}
 assert 'arm64' in command(['lipo','-archs',ssl/'lib/libssl.a'],'ssl-architecture',env=env)
 for kind,algo in [('kem','ML-KEM-768'),('signature','ML-DSA-44')]:
  text=command([ssl/'bin/openssl','list','-'+kind+'-algorithms'],'ssl-'+kind,env=env);assert algo.replace('-','').lower() in text.replace('-','').lower()
 expected_ssl=json.loads((Path(__file__).with_name('pins.json')).read_text())['ssl_files']
 assert {Path(k).name:v['sha256'] for k,v in state['ssl_files'].items()}==expected_ssl
 # Verify selected headers and static libraries together, not just the CLI.
 tiny=out/'ssl-admission.cpp';tiny.write_text('#include <openssl/crypto.h>\n#include <openssl/opensslv.h>\n#include <cstdio>\nint main(){printf("%s\\n%s\\n", OPENSSL_VERSION_TEXT, OpenSSL_version(OPENSSL_VERSION));}\n')
 command(['xcrun','clang++',tiny,'-I'+str(ssl/'include'),ssl/'lib/libssl.a',ssl/'lib/libcrypto.a','-o',out/'ssl-admission'],'ssl-static-link',60,env)
 versions=command([out/'ssl-admission'],'ssl-static-versions',30,env).splitlines()
 assert len(versions)==2 and all(x.startswith('OpenSSL 3.5.9 ') for x in versions)
 links=command(['otool','-L',out/'ssl-admission'],'ssl-static-dependencies',30,env)
 assert 'libssl.3.dylib' not in links and 'libcrypto.3.dylib' not in links
 deps=['boost@1.85' ,'libevent','zeromq','libomp','qt','qrencode','librsvg','libicns']
 names=command(['brew','deps','--union','--formula',*deps],'dependency-closure',120,env).splitlines()
 metadata=json.loads(command(['brew','info','--json=v2',*sorted(set(names+deps))],'dependency-metadata',180,env))
 expected=json.loads(Path(__file__).with_name('pins.json').read_text())['installed_versions']
 for formula in metadata['formulae']:
  version=formula['versions']['stable'];revision=formula.get('revision',0)
  full=version+('_'+str(revision) if revision else '')
  assert full in expected.get(formula['name'],[]),(formula['name'],full,'dependency closure drift; no installation admitted')
 command(['brew','install','--force-bottle',*deps],'install-bottles',1200,env)
 command(['brew','list','--versions'],'installed-versions',env=env)
 for tool in ['rsvg-convert','png2icns']:
  assert shutil.which(tool),tool+' missing before configure'
 # Never let a dependency operation silently change the pinned SSL identity.
 for file,meta in state['ssl_files'].items():assert hashlib.sha256(Path(file).read_bytes()).hexdigest()==meta['sha256']
 boost=command(['brew','--prefix','boost@1.85'],'boost-prefix',env=env).strip()
 env.update(BTX_OPENSSL=str(ssl/'bin/openssl'),PATH=str(ssl/'bin')+':'+env['PATH'])
 args=['cmake','-S',src,'-B',build,'-G','Ninja','-DCMAKE_BUILD_TYPE=Release','-DCMAKE_PREFIX_PATH=/opt/homebrew','-DCMAKE_OSX_ARCHITECTURES=arm64','-DBoost_INCLUDE_DIR='+boost+'/include','-DOPENSSL_ROOT_DIR='+str(ssl),'-DOPENSSL_INCLUDE_DIR='+str(ssl/'include'),'-DOPENSSL_SSL_LIBRARY='+str(ssl/'lib/libssl.a'),'-DOPENSSL_CRYPTO_LIBRARY='+str(ssl/'lib/libcrypto.a'),'-DOPENSSL_USE_STATIC_LIBS=ON','-DWITH_ZMQ=ON','-DBTX_ENABLE_METAL=ON','-DBTX_MATMUL_METAL_PRECOMPILE_KERNELS=ON','-DWITH_MODELNET=ON','-DBUILD_GUI=ON','-DWITH_QT_VERSION=6','-DENABLE_WALLET=ON','-DWITH_SQLITE=ON','-DBUILD_BENCH=OFF','-DCMAKE_EXPORT_COMPILE_COMMANDS=ON']
 command(args,'configure',300,env)
 shutil.copy2(build/'CMakeCache.txt',out/'CMakeCache.txt');shutil.copy2(build/'compile_commands.json',out/'compile_commands.json')
 cache=(build/'CMakeCache.txt').read_text()
 for name,value in [('OPENSSL_SSL_LIBRARY',str(ssl/'lib/libssl.a')),('OPENSSL_CRYPTO_LIBRARY',str(ssl/'lib/libcrypto.a'))]:assert any(line.startswith(name+':') and line.endswith('='+value) for line in cache.splitlines()),name
 command(['ninja','-C',build,'-t','targets','all'],'all-targets',120,env)
 targets=['btxd', 'btx-cli', 'btx-util', 'btx-modeld', 'btx-hcpd', 'btx-hosted', 'btx-open', 'btx-capability', 'btx-capabilityd', 'btx-modelcheck', 'btx-matmul-backend-info', 'btx-qt', 'btx-security', 'btx-guardd', 'btx-tx', 'btx-wallet', 'btx-native-qualify']
 plan=command(['ninja','-C',build,'-n',*targets],'actual-dry-plan',120,env);state['plan_steps']=len([x for x in plan.splitlines() if x.startswith('[')])
 command(['ninja','-C',build,'-t','commands',*targets],'generated-build-commands',120,env)
 state['atlas_toolchain_file']=(src/'gui/atlas/rust-toolchain.toml').read_text();assert '1.95.0' in state['atlas_toolchain_file']
 command(['rustup','toolchain','list'],'installed-rust-toolchains',60,env)
 for tool in ['macdeployqt','rsvg-convert','png2icns']:
  found=shutil.which(tool)
  if not found:
   for formula in ['qttools','qtbase']:
    prefix=command(['brew','--prefix',formula],'tool-prefix-'+formula+'-'+tool,30,env).strip()
    candidate=Path(prefix)/'bin'/tool
    if candidate.is_file():found=str(candidate);break
  assert found,tool+' absent'
  state.setdefault('packaging_tools',{})[tool]={'path':found,'sha256':hashlib.sha256(Path(found).read_bytes()).hexdigest()}
 state['atlas_built']=False;state['atlas_scope']='Separate Cargo producer needs exact pinned1.95.0; not covered by CMake plan.'
 assert not command(['git','-C',src,'status','--porcelain'],'final-source-status').strip()
 state['complete']=True
except Exception as e:state['error']=repr(e)
finally:
 for name in ['CMakeCache.txt','compile_commands.json']:
  if (build/name).exists():shutil.copy2(build/name,out/name)
 save()
sys.exit(0 if state.get('complete') else 1)
