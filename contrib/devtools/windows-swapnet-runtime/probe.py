from pathlib import Path
import os,sys,json,hashlib,subprocess,shutil,zipfile,urllib.request,ctypes,time,socket,base64,urllib.error,traceback
W=Path(os.environ['GITHUB_WORKSPACE']);R=W/'records';R.mkdir(exist_ok=True);state={'source':'648899223329bd962146fb4e17fcfe3516075e17','complete':False,'cases':[]};owned=[]
ctypes.windll.kernel32.SetErrorMode(0x0001|0x0002|0x8000)
def sha(b):return hashlib.sha256(b).hexdigest()
def save():(R/'result.json').write_text(json.dumps(state,indent=2)+'\n')
def run(args,label,env=None,timeout=30):
 p=subprocess.run(list(map(str,args)),capture_output=True,text=True,env=env,timeout=timeout,cwd=W)
 (R/(label+'.log')).write_text(p.stdout+p.stderr,errors='replace');state['cases'].append({'label':label,'exit':p.returncode,'unsigned_exit':p.returncode&0xffffffff});save();return p
ENV=dict(os.environ);ENV['PATH']=os.environ['SystemRoot']+'\\System32';ENV.pop('PYTHONHOME',None);ENV.pop('PYTHONPATH',None)
def rpc(d,port,method):
 auth=base64.b64encode((d/'regtest/.cookie').read_bytes().strip()).decode();q=urllib.request.Request('http://127.0.0.1:'+str(port),json.dumps({'id':'probe','method':method,'params':[]}).encode(),{'Authorization':'Basic '+auth,'Content-Type':'application/json'})
 try:r=urllib.request.urlopen(q,timeout=2)
 except urllib.error.HTTPError as e:r=e
 with r:return json.load(r)
def lifecycle(root,label,enable=True,reuse=None,expect=False):
 d=W/(reuse or label);d.mkdir(exist_ok=True)
 with socket.socket() as sock:sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
 args=[root/'btxd.exe','-datadir='+str(d),'-regtest','-server=1','-disablewallet','-modelnet=0','-autoupdate=0','-connect=0','-listen=0','-dnsseed=0','-discover=0','-rpcport='+str(port),'-rpcbind=127.0.0.1','-rpcallowip=127.0.0.1','-dbcache=16','-par=1','-nosettings','-printtoconsole=1']
 if enable:args+=['-swapnet=1']
 row={'label':label,'enabled':enable};p=None
 try:
  with (R/(label+'.log')).open('w') as log:
   p=subprocess.Popen(list(map(str,args)),stdout=log,stderr=log,env=ENV,cwd=root);owned.append(p)
   ready=False
   for _ in range(150):
    if p.poll() is not None:break
    try:
     ready=rpc(d,port,'getblockchaininfo').get('result',{}).get('chain')=='regtest'
     if ready:break
    except Exception:pass
    time.sleep(.2)
   row['rpc_ready']=ready
   if not ready:
    if p.poll() is None:raise AssertionError('Alive but RPC not ready')
    row['exit']=p.returncode
    text=(R/(label+'.log')).read_text();assert expect and ('SwapNet' in text or 'Python' in text or 'encodings' in text),text[-1500:]
    return
   assert not expect,'Unexpectedly healthy fault control'
   info=rpc(d,port,'getswapnetworkinfo');row['info']=info
   if enable:assert info['result']['in_process'] is True and info['result']['automatic_spend_atoms']=='0' and info['result']['wallet_loaded'] is False
   else:assert info['error']['code']==-1
   for _ in range(3):assert rpc(d,port,'getblockchaininfo')['result']['chain']=='regtest';time.sleep(.2)
   rpc(d,port,'stop');p.wait(timeout=15);assert p.returncode==0;row['clean_stop']=True
 finally:
  if p and p.poll() is None:
   try:rpc(d,port,'stop');p.wait(timeout=8)
   except Exception:p.kill();p.wait(timeout=8);row['forced_cleanup']=True
  state['cases'].append(row);save()
def main():
 assert shutil.disk_usage(W).free>8*1024**3
 url='https://api.github.com/repos/Jpp-matata/btx/actions/artifacts/14117861282/zip'
 class Safe(urllib.request.HTTPRedirectHandler):
  def redirect_request(self,req,fp,code,msg,headers,newurl):
   r=super().redirect_request(req,fp,code,msg,headers,newurl)
   if r:r.remove_header('Authorization')
   return r
 req=urllib.request.Request(url,headers={'Authorization':'Bearer '+os.environ['GH_TOKEN'],'User-Agent':'BTX-runtime-test'})
 with urllib.request.build_opener(Safe).open(req,timeout=60) as r:b=r.read()
 expected=json.loads((Path(__file__).parent/'artifact.json').read_text());assert 'sha256:'+sha(b)==expected['digest']
 binary=W/'saved-binaries';binary.mkdir()
 with zipfile.ZipFile(__import__('io').BytesIO(b)) as z:
  for n in z.namelist():
   assert Path(n).name==n; (binary/n).write_bytes(z.read(n))
 hashes={}
 for line in (binary/'SHA256SUMS.txt').read_text().splitlines():
  h,n=line.split(maxsplit=1);n=n.lstrip('*').removeprefix('./');assert sha((binary/n).read_bytes())==h;hashes[n]=h
 assert hashes['btxd.exe']=='d8bd7dda90ab42e92882bd02005d919185a0cac4331af007a9ef78a0a9af16ab';state['binary_hashes']=hashes;save()

 product=W/'product';source=product/'scripts/release';fixture=Path(__file__).parent
 runtime=W/'official runtime';runtime.mkdir()
 url='https://www.python.org/ftp/python/3.12.10/python-3.12.10-embed-amd64.zip'
 with urllib.request.urlopen(url,timeout=60) as r:payload=r.read()
 state['embeddable']={'url':url,'sha256':sha(payload)};save()
 with zipfile.ZipFile(__import__('io').BytesIO(payload)) as z:
  for n in z.namelist():
   assert not Path(n).is_absolute() and '..' not in Path(n).parts
   p=runtime/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(z.read(n))
 run([sys.executable,'-m','pip','install','--only-binary=:all:','--target',runtime/'Lib/site-packages','cryptography==46.0.4'],'stage-pinned-wheels',timeout=180).check_returncode()
 baseargs=[sys.executable,source/'package_release_archive.py','--version','0.34.16','--platform-id','windows-x86_64','--btxd',binary/'btxd.exe','--btx-cli',binary/'btx-cli.exe','--btx-util',binary/'btx-util.exe','--source-root',product]
 def unpack(out,label):
  archives=list(out.glob('*.zip'));assert len(archives)==1;archive=archives[0];state.setdefault('archives',{})[label]={'sha256':sha(archive.read_bytes()),'bytes':archive.stat().st_size}
  root=W/('extracted '+label)
  with zipfile.ZipFile(archive) as z:z.extractall(root)
  return next(p for p in root.iterdir() if p.is_dir())
 out=W/'baseline-archive';run(baseargs+['--output-dir',out],'stock-archive-assembly',timeout=180).check_returncode();baseline=unpack(out,'stock')
 q=run([baseline/'bin/btxd.exe','-version'],'stock-archive-loader',ENV);assert q.returncode&0xffffffff==0xc0000135
 for name in ('package_release_archive.py','bundle_windows_python_runtime.py'):shutil.copy2(fixture/name,source/name)
 shutil.copy2(fixture/'bundle_windows_python_runtime_test.py',product/'test/util/bundle_windows_python_runtime_test.py')
 run([sys.executable,product/'test/util/bundle_windows_python_runtime_test.py'],'maintained-windows-runtime-tests').check_returncode()
 out=W/'candidate-archive';run(baseargs+['--output-dir',out,'--windows-python-runtime',runtime],'candidate-archive-assembly',timeout=180).check_returncode();candidate=unpack(out,'candidate')
 assert sha((candidate/'bin/btxd.exe').read_bytes())==state['binary_hashes']['btxd.exe']
 spec=__import__('importlib.util',fromlist=['util']).spec_from_file_location('verify',source/'verify_release_btxd.py');v=__import__('importlib.util',fromlist=['util']).module_from_spec(spec);spec.loader.exec_module(v)
 images=[p for p in candidate.rglob('*') if p.is_file() and v.classify(p)=='pe'];problems=v.pe_problems(candidate,images);state['full_archive_dependency_problems']=problems
 assert problems and all('libomp140.x86_64.dll' in p for p in problems),problems
 state['full_archive_portable_gate']='REJECTED: OpenMP remains unresolved; not suppressed'
 lifecycle(candidate/'bin','actual-archive-on');lifecycle(candidate/'bin','actual-archive-restart',reuse='actual-archive-on');lifecycle(candidate/'bin','actual-archive-default-off',enable=False)
 state['complete']=True;state['scope']='Python packaging/actual ZIP native lifecycle qualified on hosted Windows with host OpenMP. Full portable archive correctly rejected for missing OpenMP. No release qualification.'
try:main()
except Exception as e:state['error']=str(e);(R/'exception.txt').write_text(traceback.format_exc())
finally:
 for p in owned:
  if p.poll() is None:p.kill();p.wait(timeout=8)
 save()
sys.exit(0 if state['complete'] else 1)
