from pathlib import Path
import os,sys,json,hashlib,subprocess,shutil,zipfile,urllib.request,ctypes,time,socket,base64,urllib.error,traceback
sys.path.insert(0,str(Path(__file__).parent))
from native_closure import loaded_modules
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
def job_create():
 k=ctypes.WinDLL('kernel32',use_last_error=True);k.CreateJobObjectW.argtypes=[ctypes.c_void_p,ctypes.c_wchar_p];k.CreateJobObjectW.restype=ctypes.c_void_p
 k.AssignProcessToJobObject.argtypes=[ctypes.c_void_p,ctypes.c_void_p];k.AssignProcessToJobObject.restype=ctypes.c_int
 k.QueryInformationJobObject.argtypes=[ctypes.c_void_p,ctypes.c_int,ctypes.c_void_p,ctypes.c_ulong,ctypes.c_void_p];k.QueryInformationJobObject.restype=ctypes.c_int
 k.CloseHandle.argtypes=[ctypes.c_void_p];k.TerminateJobObject.argtypes=[ctypes.c_void_p,ctypes.c_uint]
 h=k.CreateJobObjectW(None,None);assert h,ctypes.get_last_error();return k,h

def members(k,h):
 b=ctypes.create_string_buffer(65536);assert k.QueryInformationJobObject(h,3,b,len(b),None),ctypes.get_last_error()
 n=int.from_bytes(b.raw[4:8],'little');assert n<4096
 return [int.from_bytes(b.raw[8+i*8:16+i*8],'little') for i in range(n)]

def start_owned(k,h,args,**kwargs):
 p=subprocess.Popen(list(map(str,args)),creationflags=4,**kwargs);owned.append(p)
 try:
  assert k.AssignProcessToJobObject(h,int(p._handle)),ctypes.get_last_error()
  nt=ctypes.WinDLL('ntdll');nt.NtResumeProcess.argtypes=[ctypes.c_void_p];nt.NtResumeProcess.restype=ctypes.c_long;assert nt.NtResumeProcess(int(p._handle))==0
  return p
 except:
  p.kill();p.wait();raise

def main():
 root=W/'relocated archive';binroot=next(p for p in root.iterdir() if p.is_dir())/'bin'
 assert not Path(os.environ['BTX_PRODUCER_PATH']).exists(),'Producer must be physically unavailable'
 state['producer_absent_before']=True;state['archive_sha256']=os.environ['BTX_ARCHIVE_SHA'];save()
 k,h=job_create();p=None
 try:
  guard=start_owned(k,h,[binroot/'btx-guardd.exe','--stdio'],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,env=ENV,cwd=W)
  out,err=guard.communicate(input=b'',timeout=15);assert guard.returncode==0 and not out and not err
  state['guard_eof_clean']=True;assert not members(k,h)
  d=W/'hidden-producer-node';d.mkdir()
  with socket.socket() as sock:sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
  args=[binroot/'btxd.exe','-datadir='+str(d),'-regtest','-server=1','-disablewallet','-modelnet=0','-autoupdate=0','-connect=0','-listen=0','-dnsseed=0','-discover=0','-rpcport='+str(port),'-rpcbind=127.0.0.1','-rpcallowip=127.0.0.1','-dbcache=16','-par=1','-nosettings','-printtoconsole=1','-swapnet=1']
  with (R/'producer-unavailable-node.log').open('w') as log:
   p=start_owned(k,h,args,stdout=log,stderr=log,env=ENV,cwd=binroot)
   deadline=time.monotonic()+40
   while True:
    assert p.poll() is None,'Node exited before RPC'
    try:
     if rpc(d,port,'getblockchaininfo').get('result',{}).get('chain')=='regtest':break
    except Exception:pass
    assert time.monotonic()<deadline,'RPC timeout';time.sleep(.2)
   info=rpc(d,port,'getswapnetworkinfo');assert info['result']['in_process'] and info['result']['automatic_spend_atoms']=='0' and not info['result']['wallet_loaded'];state['info']=info
   paths=loaded_modules(p.pid);mods=[x for x in paths if Path(x).name.lower().startswith(('python','libomp'))];assert mods and all(Path(x).resolve().is_relative_to(binroot.resolve()) for x in mods);state['runtime_modules']=mods
   state['job_members_before_stop']=members(k,h);assert p.pid in state['job_members_before_stop'];rpc(d,port,'stop');p.wait(timeout=20);assert p.returncode==0
   observations=[]
   for i in range(5):
    ids=members(k,h);observations.append(ids);assert not ids,'Surviving owned descendants';time.sleep(.25)
   state['job_members_after_stop']=observations;state['clean_stop']=True
  assert not Path(os.environ['BTX_PRODUCER_PATH']).exists();state['producer_absent_after']=True;state['complete']=True
 finally:
  remaining=members(k,h);state['remaining_before_cleanup']=remaining
  if remaining:k.TerminateJobObject(h,1);state['forced_cleanup']=True
  k.CloseHandle(h)
try:main()
except Exception as e:state['error']=repr(e);(R/'exception.txt').write_text(traceback.format_exc());print(traceback.format_exc(),flush=True)
finally:save()
sys.exit(0 if state['complete'] else 1)
