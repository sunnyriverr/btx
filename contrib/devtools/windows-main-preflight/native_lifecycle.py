from pathlib import Path
import os,sys,json,hashlib,subprocess,shutil,zipfile,urllib.request,ctypes,time,socket,base64,urllib.error,traceback
from native_closure import prepare, qualify_openmp, loaded_modules
W=Path(os.environ['GITHUB_WORKSPACE']);R=W/'records';R.mkdir(exist_ok=True);state={'source':'074dac167c26c1e091198f691ed5727817dba88a','complete':False,'cases':[]};owned=[]
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
   modules=loaded_modules(p.pid);row['runtime_modules']=[x for x in modules if Path(x).name.lower().startswith(('python','libomp'))]
   expected_root=str(root.resolve()).lower()+os.sep
   assert row['runtime_modules'] and all(x.lower().startswith(expected_root) for x in row['runtime_modules']),row
   assert any(Path(x).name.lower()=='libomp140.x86_64.dll' for x in row['runtime_modules']),row
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
 binary=Path('D:/btx-native-035/project-build/bin');fixture=Path(__file__).parent;product=W/'btx';source=product/'scripts/release'
 runtime=W/'official runtime';runtime.mkdir();omp=prepare(fixture,runtime,R,W)
 out=W/'candidate-archive'
 # Assembly is necessary because the prior artifact retained logs but not the ZIP.
 run([sys.executable,source/'package_release_archive.py','--version','0.34.16','--platform-id','windows-x86_64','--btxd',binary/'btxd.exe','--btx-cli',binary/'btx-cli.exe','--btx-util',binary/'btx-util.exe','--source-root',product,'--output-dir',out,'--windows-python-runtime',runtime,'--windows-openmp-runtime',omp],'archive-assembly',timeout=180).check_returncode()
 archive=next(out.glob('*.zip'));state['archive']={'sha256':sha(archive.read_bytes()),'bytes':archive.stat().st_size};retained=R/'archive';retained.mkdir();shutil.copy2(archive,retained/archive.name);save()
 extracted=W/'relocated archive';extracted.mkdir()
 with zipfile.ZipFile(archive) as z:z.extractall(extracted)
 root=next(p for p in extracted.iterdir() if p.is_dir());binroot=root/'bin'
 marker=json.loads(Path('D:/btx-native-035/project-build/btx-successor.json').read_text());expected=marker['build_result']['binary_hashes'];state['selected_binary_hashes']={}
 for name,h in expected.items():
  exe=binroot/(name+'.exe');assert exe.is_file() and sha(exe.read_bytes())==h,name;state['selected_binary_hashes'][name]=h
 state['reused_passes']={'run':43688614528,'checks':['actual archive release gate','PE dependency closure','Python isolation','btx-cli version'],'same_selected_executables':True,'archive_reassembled':True};save()
 probes={'btx-open':['-help'],'btx-modeld':['-version'],'btx-tx':['-help'],'btx-util':['-version'],'btxd':['-version']}
 for name,args in probes.items():run([binroot/(name+'.exe'),*args],'tool-'+name,env=ENV).check_returncode()
 guard=subprocess.run([str(binroot/'btx-guardd.exe'),'--stdio'],input='',capture_output=True,text=True,env=ENV,timeout=15,cwd=W);(R/'guard-eof.log').write_text(guard.stdout+guard.stderr);assert guard.returncode==0 and not guard.stdout and not guard.stderr;state['guard_eof_clean']=True
 sec=run([binroot/'btx-security.exe'],'security-usage',env=ENV);assert sec.returncode==1 and 'BTX model security administrative CLI' in sec.stderr;state['security_usage_expected_exit']=1;save()
 lifecycle(binroot,'archive-default-off',enable=False);lifecycle(binroot,'archive-on');lifecycle(binroot,'archive-restart',reuse='archive-on')
 assert all(p.poll() is not None for p in owned);state['owned_nodes_exited']=True
 state['complete']=True;state['scope']='Current074 savedbuild nativeWindows: missing executable contracts and relocated defaultoff/on/samedatadirRPCrestart/cleanstop. Earlier gate/isolation results reused; no compilation or fullunits.'
try:main()
except Exception as e:state['error']=str(e);(R/'exception.txt').write_text(traceback.format_exc());print(traceback.format_exc(),flush=True)
finally:
 for p in owned:
  if p.poll() is None:p.kill();p.wait(timeout=8)
 save()
sys.exit(0 if state['complete'] else 1)
