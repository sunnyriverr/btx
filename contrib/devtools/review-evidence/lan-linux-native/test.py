from pathlib import Path
import json,socket,struct,subprocess,time,tempfile,shutil,hashlib,sys,os
R=Path('/tmp/btx-lan-linux');binary=Path(sys.argv[1]);variant=sys.argv[2];out=R/(variant+'-results.json');rows=[]
info=json.loads(subprocess.check_output(['ip','-j','addr'],text=True));eth=next(x for x in info if x['ifname']=='eth0');ip=next(x['local'] for x in eth['addr_info'] if x['family']=='inet');group='239.192.0.35'
def rpc(path):
 with socket.socket(socket.AF_UNIX,socket.SOCK_STREAM) as s:
  s.settimeout(3);s.connect(str(path));s.sendall(b'{"id":1,"method":"getmodelnetworkinfo","params":[]}\n');data=b''
  while b'\n' not in data:
   b=s.recv(65536)
   if not b:break
   data+=b
  x=json.loads(data);assert not x.get('error');return x['result']
def packet(port,chain='regtest',bad=False):
 b=bytearray(b'BTXLAN\1\0'+chain.encode().ljust(16,b'\0')+struct.pack('!H',port)+b'\0'*6+b'\xa5'*16)
 if bad:b[26]=1
 assert len(b)==48;return b
def emit(port,multicast=False,chain='regtest',bad=False):
 with socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as s:
  s.bind((ip,0));s.setsockopt(socket.IPPROTO_IP,socket.IP_MULTICAST_IF,socket.inet_aton(ip));s.setsockopt(socket.IPPROTO_IP,socket.IP_MULTICAST_TTL,0);s.setsockopt(socket.IPPROTO_IP,socket.IP_MULTICAST_LOOP,1)
  s.sendto(packet(port,chain,bad),(group if multicast else '127.0.0.1',29448))
def accept(s,seconds):
 s.settimeout(seconds)
 try:c,addr=s.accept()
 except socket.timeout:return None
 with c:
  c.settimeout(3);hello=c.recv(8192)
 assert addr[0]==ip;assert len(hello)>=6 and hello[0]==22 and hello[1]==3 and hello[5]==1
 return {'tls_client_hello':True,'source_is_own_ip':True}
def record():out.write_text(json.dumps({'variant':variant,'binary_sha256':hashlib.sha256(binary.read_bytes()).hexdigest(),'cases':rows},indent=2)+'\n')
for kind in ['off_scope']*3+['valid_recovery']*3+['disabled']:
 with tempfile.TemporaryDirectory(prefix='btx-lan-test-') as td,socket.socket() as listener,socket.socket() as reserve,socket.socket() as invalid_listener:
  td=Path(td);invalid_listener.bind((ip,0));invalid_listener.listen(8);invalid_port=invalid_listener.getsockname()[1];listener.bind((ip,0));listener.listen(8);port=listener.getsockname()[1];reserve.bind((ip,0));helper_port=reserve.getsockname()[1];reserve.close();sp=td/'rpc.sock'
  enabled=kind!='disabled';args=[str(binary),'-modeldir='+str(td/'model'),'-modelrpcsocket='+str(sp),'-modelbind='+ip+':'+str(helper_port),'-modelstorage=0','-modelnatpmp=0','-modelhost=0','-modelseed=off','-modelfollowpeers=1','-pwcchain=regtest','-modellandiscovery='+str(int(enabled))]
  case={'kind':kind};rows.append(case);start=time.monotonic()
  with (td/'helper.log').open('w') as log:
   p=subprocess.Popen(args,stdout=log,stderr=log)
   try:
    deadline=time.monotonic()+15
    while time.monotonic()<deadline:
     assert p.poll() is None
     try:
      state=rpc(sp)
      if state.get('pq1_ready'):break
     except (OSError,ValueError):pass
     time.sleep(.1)
    else:raise RuntimeError('readiness')
    native=state['native_participation'];assert native['lan_enabled']==enabled and native['hint_count']==0;assert state['quota_bytes']==0 and state['automatic_spend_atoms'] in [0,'0']
    assert accept(listener,2) is None
    if kind=='valid_recovery':
     emit(invalid_port,True,'main');assert accept(invalid_listener,6) is None;assert accept(listener,.1) is None
     emit(invalid_port,True,bad=True);assert accept(invalid_listener,6) is None;assert accept(listener,.1) is None
     case['wrong_network_and_malformed_no_dial']=True
    t=time.monotonic();emit(port,kind!='off_scope');seen=accept(listener,9 if kind=='valid_recovery' else 6)
    case.update(connected=seen is not None,observation=seen,elapsed_s=time.monotonic()-t)
    case['regression_pass']=(seen is None) if kind in ['off_scope','disabled'] else seen is not None
    assert accept(invalid_listener,.2) is None
    case['invalid_endpoint_distinct']=True
    case['rpc_responsive_after']=rpc(sp)['pq1_ready'];case['pass']=case['rpc_responsive_after'] and (seen is not None if kind=='valid_recovery' else (seen is None if kind=='disabled' else True))
   finally:
    p.terminate()
    try:p.wait(timeout=5)
    except subprocess.TimeoutExpired:p.kill();p.wait()
    case['exit']=p.returncode;case['total_s']=time.monotonic()-start;record()
  assert case.get('pass') and case['exit']==0,case
  print(variant,kind,case.get('connected'),case.get('regression_pass'),flush=True)
assert len(rows)==7 and all(x['pass'] for x in rows)
assert all(x['regression_pass']==(variant=='candidate') for x in rows if x['kind']=='off_scope')
assert all(x['regression_pass'] for x in rows if x['kind']!='off_scope')
