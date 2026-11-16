"""Matched native governor regressions through the normal generated test target."""
from pathlib import Path
import os, sys, json, hashlib, subprocess, shutil, time, re, urllib.request
P=Path(__file__).resolve().parent; R=Path('D:/btx-native-035'); B=R/'project-build'; S=Path(os.environ['GITHUB_WORKSPACE'])/'btx'; E=R/'governor-repair-evidence'; E.mkdir(exist_ok=True)
sys.path.insert(0,str(P.parent/'governor-helper-control'))
from batch_results import classify
from job_tree import ProcessTree
m=json.loads((P/'source-manifest.json').read_text());cp=json.loads((B/'btx-successor.json').read_text());result={'source':m['source'],'scope':'Native Windows seed consumer; POSIX preservation remains separate','commands':[],'phases':{},'status':'PREPARING'}
def save(): (E/'result.json').write_text(json.dumps(result,indent=2)+'\n')
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def run(label,args,cap=180,cwd=B,check=True):
 st=time.monotonic();log=E/(label+'.log')
 with log.open('wb') as out:
  proc=subprocess.Popen(args,cwd=cwd,stdout=out,stderr=subprocess.STDOUT)
  try:
   while proc.poll() is None:
    time.sleep(1)
    assert shutil.disk_usage(R).free>1342177280,'disk reserve'
    if time.monotonic()-st>cap:raise TimeoutError(label)
  finally:
   if proc.poll() is None:subprocess.run(['taskkill','/PID',str(proc.pid),'/T','/F'],capture_output=True);proc.wait()
 text=log.read_text(errors='replace');result['commands'].append({'label':label,'exit':proc.returncode,'seconds':round(time.monotonic()-st,3),'sha256':sha(log)});save()
 print(label,proc.returncode,text[-1200:],flush=True)
 if check:assert proc.returncode==0,label
 return proc.returncode,text

def tools():
 assert '20.1.8' in run('compiler',['clang-cl','--version'])[1]
 assert os.environ['VCToolsVersion'].rstrip('\\')=='14.51.36231'
 assert os.environ['WindowsSDKVersion'].rstrip('\\')=='10.0.26100.0'
 V=R/'vcpkg';V.mkdir(exist_ok=False)
 run('vcpkg-init',['git','init',str(V)],cwd=R)
 run('vcpkg-fetch',['git','-C',str(V),'fetch','--depth=1','https://github.com/microsoft/vcpkg.git','afa249f12f52ed8a3b919f195495ba8b330288d1'],cap=300,cwd=R)
 run('vcpkg-checkout',['git','-C',str(V),'checkout','--detach','FETCH_HEAD'],cwd=R)
 req=urllib.request.Request('https://api.github.com/repos/microsoft/vcpkg-tool/releases/assets/690264732',headers={'Accept':'application/octet-stream','User-Agent':'BTX verification','Authorization':'Bearer '+os.environ['GH_TOKEN']})
 class Redirect(urllib.request.HTTPRedirectHandler):
  def redirect_request(self,req,fp,code,msg,headers,url):
   q=super().redirect_request(req,fp,code,msg,headers,url)
   if q and urllib.parse.urlparse(url).netloc!='api.github.com':q.remove_header('Authorization')
   return q
 with urllib.request.build_opener(Redirect).open(req,timeout=90) as f:data=f.read(10*1024**2)
 assert hashlib.sha256(data).hexdigest()=='191ee64b0887af80aad3eff6c5e888ab733d3ef2182885ed4747b4574c201834'
 (V/'vcpkg.exe').write_bytes(data);(V/'vcpkg.disable-metrics').write_text('')
 assert (V/'scripts/buildsystems/msbuild/applocal.ps1').exists()
 assert (R/'openssl-3.5.4-static/btx-build-provenance.json').exists()
 run('python-dependencies',[sys.executable,'-I','-c','import cryptography,sqlite3;from cryptography.hazmat.primitives.ciphers.aead import AESGCM'])

def build(phase):
 _,text=run(phase+'-dry-run',['ninja','-C',str(B),'-n','test_btx'])
 actions=[line for line in text.splitlines() if re.match(r'^\[\d+/\d+\]',line)]
 result['phases'][phase]={'actions':actions};save()
 assert len(actions)<=30,actions
 for line in actions:
  if 'Building CXX object' in line:
   assert any(n in line for n in ['resource_governor_tests.cpp.obj','helper.cpp.obj']),line
 assert not any('Re-running CMake' in a for a in actions),actions
 run(phase+'-normal-build',['ninja','-C',str(B),'-j2','test_btx'],cap=1200)
 result['phases'][phase]['binary_sha256']=sha(B/'bin/test_btx.exe');save()

def tests(phase):
 names=m['tests']['selectors'];sels=['resource_governor_tests/'+n for n in names]
 report=E/(phase+'.xml');args=[str(B/'bin/test_btx.exe'),'--run_test=resource_governor_tests/'+','.join(names),'--log_level=test_suite','--report_level=detailed','--report_format=XML','--report_sink='+str(report),'--catch_system_errors=yes','--','-testdatadir=S:/'+phase]
 code,log=run(phase+'-tests',args,cap=180,check=False)
 out=classify(sels,log,report.read_text(errors='replace') if report.exists() else '',code)
 cases=out.pop('cases');out['cases']={n:cases[n] for n in sels if n in cases};result['phases'][phase]['tests']=out;save()
 assert len(out['cases'])==4 and out['announced']==4,out
 assert all(int(row.get('assertions_passed','0'))>0 for row in out['cases'].values()),out
 assert not any(row.get('result')=='skipped' for row in out['cases'].values())
 if phase=='baseline':
  assert out['cases'][sels[0]]['result']=='passed',out
  assert out['cases'][sels[1]]['result']=='failed' and out['cases'][sels[2]]['result']=='failed',out
 else:assert out['state']=='passed' and code==0,out

D=R/('gov-runtime-'+os.environ['GITHUB_RUN_ID']);tree=None
try:
 assert sha(B/'btx-successor.json')=='d980ca1fae8a45385fc5ca9777fc89ffb3ae977f5af7b841dde18f3352e0d515'
 assert cp['source']==m['source']
 assert sha(S/'src/modelnet/helper.cpp')==m['baseline_sha256']
 assert sha(S/'src/test/resource_governor_tests.cpp')==m['tests']['baseline_sha256']
 assert sha(P/'helper.cpp')==m['candidate_sha256'] and sha(P/'resource_governor_tests.cpp')==m['tests']['candidate_sha256']
 for n,v in cp['source_files'].items():
  path=S/n;assert sha(path)==v['sha256'];os.utime(path,ns=(path.stat().st_atime_ns,v['mtime_ns']))
 tools();tree=ProcessTree();assert tree.active()==1
 assert not D.exists() and not Path('S:/').exists();D.mkdir();(D/'tmp').mkdir();run('short-root',['subst','S:',str(D)],cwd=R)
 for key in ['TEMP','TMP','TMPDIR']:os.environ[key]='S:/tmp'
 shutil.copyfile(P/'resource_governor_tests.cpp',S/'src/test/resource_governor_tests.cpp')
 build('baseline');tests('baseline');assert tree.active()==1
 shutil.copyfile(P/'helper.cpp',S/'src/modelnet/helper.cpp')
 build('candidate');tests('candidate');assert tree.active()==1
 shutil.copy2(B/'bin/test_btx.exe',E/'test_btx.exe')
 shutil.copy2(P/'candidate.patch',E/'candidate.patch');shutil.copy2(P/'source-manifest.json',E/'source-manifest.json')
 result['status']='WINDOWS_SEED_BEFORE_AFTER_PASS';result['normal_target']='ninja -j2 test_btx; unchanged generated graph/post-link hooks';save()
except BaseException as ex:
 result['status']='INCOMPLETE';result['error']=repr(ex);save();raise
finally:
 if Path('S:/').exists():run('remove-short-root',['subst','S:','/D'],cwd=R)
 if D.exists():shutil.rmtree(D)
 result['runtime_removed']=not D.exists() and not Path('S:/').exists();result['original_remote_cache_saved_over']=False;save()
