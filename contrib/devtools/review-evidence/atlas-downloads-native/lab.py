from pathlib import Path
import socket,json,subprocess,time,tempfile,os,sys,base64,urllib.request
ROOT=Path(__file__).resolve().parent
STATE=ROOT/'lab-state.json'
def rpc_helper(path,method,params=[]):
 with socket.socket(socket.AF_UNIX,socket.SOCK_STREAM) as s:
  s.settimeout(20);s.connect(str(path));s.sendall((json.dumps({'id':1,'method':method,'params':params})+'\n').encode());s.shutdown(socket.SHUT_WR)
  data=b''
  while b'\n' not in data:
   part=s.recv(65536)
   if not part:break
   data+=part
  d=json.loads(data)
  if d.get('error'):raise RuntimeError(d['error'])
  return d['result']
def rpc_node(method,params=[]):
 st=json.load(open(STATE));cookie=(Path(st['scratch'])/'node/regtest/.cookie').read_text().strip()
 req=urllib.request.Request('http://127.0.0.1:'+str(st['rpc_port']),data=json.dumps({'jsonrpc':'1.0','id':'atlas-downloads-native','method':method,'params':params}).encode(),headers={'Authorization':'Basic '+base64.b64encode(cookie.encode()).decode(),'Content-Type':'application/json'})
 with urllib.request.urlopen(req,timeout=20) as r:d=json.load(r)
 if d.get('error'):raise RuntimeError(d['error'])
 return d['result']
def freeport():
 with socket.socket() as s:s.bind(('127.0.0.1',0));return s.getsockname()[1]
def start():
 if STATE.exists():raise RuntimeError('Existing state; inspect before restart')
 scratch=Path(tempfile.mkdtemp(prefix='atlas-download-',dir='/tmp'));scratch.chmod(0o700)
 st={'scratch':str(scratch),'rpc_port':freeport(),'processes':{}}
 def launch(name,args):
  with (ROOT/(name+'.log')).open('w') as log:proc=subprocess.Popen(args,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
  st['processes'][name]={'pid':proc.pid,'argv':args};STATE.write_text(json.dumps(st,indent=2));return proc
 for role in ['seed','buyer']:
  model=scratch/role;model.mkdir();port=freeport();st[role+'_port']=port;st[role+'_socket']=str(scratch/(role+'.sock'))
  args=[str(ROOT.parent.parent/'btx-atlas-test2/bin/btx-modeld'),'-modeldir='+str(model),'-modelrpcsocket='+st[role+'_socket'],'-modelbind=127.0.0.1:'+str(port),'-modelstorage=64MiB','-modelhost='+('1' if role=='seed' else '0'),'-modelseed=off','-modelfollowpeers=0','-modellandiscovery=0','-modelnatpmp=0','-pwcchain=regtest']
  if role=='buyer':args+=['-modelpeer=127.0.0.1:'+str(st['seed_port'])]
  proc=launch(role,args)
  deadline=time.monotonic()+25
  while time.monotonic()<deadline:
   if proc.poll() is not None:raise RuntimeError(role+' exited; inspect log')
   try:
    info=rpc_helper(st[role+'_socket'],'getmodelnetworkinfo')
    if info.get('pq1_ready'):break
   except (OSError,ValueError):pass
   time.sleep(.1)
  else:raise RuntimeError(role+' not ready')
  (ROOT/(role+'-ready.json')).write_text(json.dumps(info,indent=2))
 node=scratch/'node';node.mkdir()
 args=[str(ROOT.parent.parent/'btx-atlas-test2/bin/btxd'),'-regtest','-datadir='+str(node),'-server=1','-rpcbind=127.0.0.1','-rpcallowip=127.0.0.1','-rpcport='+str(st['rpc_port']),'-listen=0','-connect=0','-dnsseed=0','-discover=0','-natpmp=0','-disablewallet=1','-modelnet=1','-modelrpcsocket='+st['buyer_socket'],'-modeldir='+str(scratch/'buyer'),'-modelseed=off','-modelfollowpeers=0','-modellandiscovery=0','-modelhost=0','-modelrelay=0','-modelbind=off','-printtoconsole=1']
 proc=launch('node',args)
 for _ in range(150):
  if proc.poll() is not None:raise RuntimeError('node exited; inspect log')
  try:
   d=rpc_node('getblockchaininfo');break
  except Exception:time.sleep(.1)
 else:raise RuntimeError('node not ready')
 print(json.dumps({'scratch':str(scratch),'rpc_port':st['rpc_port'],'chain':d['chain'],'height':d['blocks']}))
if __name__=='__main__':
 if sys.argv[1]=='start':start()
 elif sys.argv[1]=='node':print(json.dumps(rpc_node(sys.argv[2],json.loads(sys.argv[3]) if len(sys.argv)>3 else []),indent=2))
 elif sys.argv[1] in ['seed','buyer']:
  st=json.load(open(STATE));print(json.dumps(rpc_helper(st[sys.argv[1]+'_socket'],sys.argv[2],json.loads(sys.argv[3]) if len(sys.argv)>3 else []),indent=2))
