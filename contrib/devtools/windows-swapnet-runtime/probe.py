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
 omp=Path('C:/Program Files/LLVM/bin/libomp140.x86_64.dll');assert omp.is_file()
 roots={}
 for name in ('raw','omp-only','dll-no-stdlib','no-crypto','healthy'):
  root=W/('relocated '+name);root.mkdir();shutil.copy2(binary/'btxd.exe',root/'btxd.exe');roots[name]=root
  if name!='raw':shutil.copy2(omp,root/omp.name)
 for name in ('raw','omp-only'):
  p=run([roots[name]/'btxd.exe','-version'],name,ENV);assert p.returncode&0xffffffff==0xc0000135,(name,p.returncode)
 pyroot=Path(sys.base_prefix);dll=pyroot/'python312.dll';assert dll.is_file();state['runtime']={'python':sys.version,'root':str(pyroot),'python_dll_sha256':sha(dll.read_bytes()),'omp_sha256':sha(omp.read_bytes())};save()
 root=roots['dll-no-stdlib'];shutil.copy2(dll,root/dll.name);(root/'python312._pth').write_text('.\nLib\nDLLs\nLib/site-packages\n');lifecycle(root,'missing-stdlib',expect=True)
 for name in ('no-crypto','healthy'):
  root=roots[name]
  for item in ('python312.dll','python3.dll','DLLs','Lib'):
   src=pyroot/item
   if src.is_dir():shutil.copytree(src,root/item,ignore=shutil.ignore_patterns('site-packages','__pycache__','test','tests'))
   elif src.is_file():shutil.copy2(src,root/item)
  (root/'python312._pth').write_text('.\nLib\nDLLs\nLib/site-packages\n')
 lifecycle(roots['no-crypto'],'missing-crypto',expect=True)
 run([sys.executable,'-m','pip','install','--only-binary=:all:','--target',roots['healthy']/'Lib/site-packages','cryptography==46.0.4'],'healthy-crypto-install',timeout=180).check_returncode()
 lifecycle(roots['healthy'],'healthy-on');lifecycle(roots['healthy'],'healthy-restart',reuse='healthy-on');lifecycle(roots['healthy'],'healthy-default-off',enable=False)
 assert all(p.poll() is not None for p in owned);state['complete']=True;state['scope']='Saved JPP binary, controlled application-local runtime with explicit ._pth; not stock-package fix/current-source or full-release qualification'
try:main()
except Exception as e:state['error']=str(e);(R/'exception.txt').write_text(traceback.format_exc())
finally:
 for p in owned:
  if p.poll() is None:p.kill();p.wait(timeout=8)
 save()
sys.exit(0 if state['complete'] else 1)
