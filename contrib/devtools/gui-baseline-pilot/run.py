from pathlib import Path
import os,sys,subprocess,time,signal,shutil,json,hashlib,tarfile,urllib.request
w=Path(os.environ['GITHUB_WORKSPACE']);src=w/'product';out=w/'gui-pilot-results';out.mkdir();r=w/'gui-pilot-runtime';r.mkdir();prefix=r/'openssl';build=r/'qtbuild'
s={'fixture':os.environ['GITHUB_SHA'],'source':'ff5f3f04ea11f044594987fc6be043ff68b136ad','commands':[],'qt_compiled':False,'working_package_accessed':False,'shipped_openssl_modified':False}
def save():(out/'result.json').write_text(json.dumps(s,indent=2)+'\n')
def run(args,label,cwd=None,env=None,limit=120):
 s['phase']=label;save();start=time.monotonic()
 with (out/(label+'.log')).open('wb') as f:
  p=subprocess.Popen(list(map(str,args)),cwd=cwd,env=env,stdout=f,stderr=subprocess.STDOUT,start_new_session=True)
  stop=None
  while p.poll() is None:
   if time.monotonic()-start>limit:stop='timeout'
   if shutil.disk_usage(w).free<2*1024**3:stop='disk reserve'
   if stop:
    os.killpg(p.pid,signal.SIGTERM)
    try:p.wait(timeout=10)
    except subprocess.TimeoutExpired:os.killpg(p.pid,signal.SIGKILL);p.wait(timeout=5)
    break
   time.sleep(.5)
 s['commands'].append({'label':label,'args':list(map(str,args)),'exit':p.returncode,'seconds':time.monotonic()-start,'stop':stop});save()
 assert not stop and p.returncode==0,label
 return (out/(label+'.log')).read_text(errors='replace')
try:
 assert shutil.disk_usage(w).free>=8*1024**3
 assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=src,text=True).strip()==s['source']
 assert not subprocess.check_output(['git','status','--porcelain','--untracked-files=no'],cwd=src)
 run(['getconf','GNU_LIBC_VERSION'],'libc');run(['g++','--version'],'compiler');run(['cmake','--version'],'cmake')
 run(['dpkg-query','-W'],'installed-packages')
 run(['pkg-config','--modversion','webkit2gtk-4.1','gtk+-3.0'],'gui-versions')
 probe=r/'qt-probe';probe.mkdir();(probe/'CMakeLists.txt').write_text('cmake_minimum_required(VERSION 3.22)\nproject(QtProbe LANGUAGES CXX)\nfind_package(Qt6 6.2 REQUIRED COMPONENTS Core Gui Widgets Network DBus LinguistTools)\nmessage(STATUS \"Resolved Qt ${Qt6_VERSION}\")\n')
 run(['cmake','-S',probe,'-B',r/'qt-probe-build'],'qt-package-discovery')
 tool=next((str(x) for x in [Path('/usr/bin/qtpaths6'),Path('/usr/lib/qt6/bin/qtpaths'),Path('/usr/lib/qt6/bin/qtpaths6')] if x.is_file()),None)
 assert tool,'Qt paths tool unavailable'
 plugin=run([tool,'--query','QT_INSTALL_PLUGINS'],'qt-plugin-root').strip()
 assert (Path(plugin)/'platforms/libqxcb.so').is_file(),'Qt XCB platform plugin unavailable'
 a=r/'openssl.tar.gz'
 with urllib.request.urlopen('https://github.com/openssl/openssl/releases/download/openssl-3.5.9/openssl-3.5.9.tar.gz',timeout=60) as f,a.open('wb') as dst:shutil.copyfileobj(f,dst)
 h=hashlib.sha256(a.read_bytes()).hexdigest();assert h=='603f5602e2eef00d77fbd429d34dcd5822bb301757a1bc9cdb24c670f1eb859a';s['private_openssl_source_sha256']=h
 with tarfile.open(a) as t:t.extractall(r,filter='data')
 ssl=r/'openssl-3.5.9'
 run(['perl','Configure','linux-x86_64','--prefix='+str(prefix),'--libdir=lib','no-shared','no-tests','no-docs','-fPIC'],'openssl-configure',ssl)
 run(['make','-j2'],'openssl-build',ssl,limit=900)
 run(['make','install_sw'],'openssl-install',ssl,limit=180)
 run([prefix/'bin/openssl','version','-a'],'private-openssl-version')
 assert 'ML-KEM-768' in run([prefix/'bin/openssl','list','-kem-algorithms'],'private-kem')
 assert 'ML-DSA-44' in run([prefix/'bin/openssl','list','-signature-algorithms'],'private-dsa')
 env=dict(os.environ,BTX_GUI_SOURCE=str(src),BTX_GUI_BUILD=str(build),BTX_GUI_SSL=str(prefix))
 run(['sh',Path(__file__).with_name('configure-qt.sh')],'qt-configure-and-plan',env=env,limit=300)
 for name in ['CMakeCache.txt','build.ninja','compile_commands.json']:
  if (build/name).exists():shutil.copyfile(build/name,out/name)
 run(['ninja','-C',build,'-t','commands','btx-qt'],'qt-planned-commands',limit=30)
 s['configuration_pass']=True
except Exception as e:s['error']=repr(e);s['configuration_pass']=False
finally:
 s['source_clean']=not bool(subprocess.check_output(['git','status','--porcelain','--untracked-files=no'],cwd=src))
 # Capture partial configure diagnostics too.
 if build.exists():
  for name in ['CMakeCache.txt','build.ninja','compile_commands.json']:
   if (build/name).exists():shutil.copyfile(build/name,out/name)
 shutil.rmtree(r);s['runtime_removed']=not r.exists();save()
raise SystemExit(0 if s.get('configuration_pass') and s['source_clean'] else 1)
