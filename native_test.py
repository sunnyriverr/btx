from pathlib import Path
import subprocess,os,socket,time,json,threading,hashlib,select,signal
from validate_result import qualifies
w=Path(os.environ['GITHUB_WORKSPACE']);out=w/'records';openssl=w/'gui-pilot-runtime/openssl/bin/openssl';CAP=32*1024**2
summary={'cases':[],'network':'Docker --network none; TEST-NET203.0.113.1 on isolated loopback','cap':CAP,'complete':False}
def save():(out/'native-result.json').write_text(json.dumps(summary,indent=2)+'\n')
def require(x,m):
 if not x:raise AssertionError(m)
def rpc(path):
 with socket.socket(socket.AF_UNIX) as s:
  s.settimeout(5);s.connect(str(path));s.sendall(b'{"id":1,"method":"getmodelnetworkinfo","params":[]}\n');data=b''
  while True:
   b=s.recv(65536)
   if not b:break
   data+=b
  obj=json.loads(data);require(not obj.get('error'),str(obj));return obj['result']
class Client:
 def __init__(self,root,name):
  self.log=(root/(name+'-tls.log')).open('wb');self.p=subprocess.Popen([str(openssl),'s_client','-connect','127.0.0.1:29448','-bind','203.0.113.1:0','-cert',str(root/'model/tls/cert.pem'),'-key',str(root/'model/tls/key.pem'),'-quiet','-ign_eof','-tls1_3','-groups','MLKEM768','-sigalgs','mldsa44','-ciphersuites','TLS_AES_256_GCM_SHA384'],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=self.log)
 def request(self,route,body=None):
  raw=b'' if body is None else json.dumps(body).encode();method='GET' if body is None else 'POST'
  head=f'{method} /btx-model/2/{route} HTTP/1.1\r\nHost: fixture\r\nContent-Length: {len(raw)}\r\n\r\n'.encode();self.p.stdin.write(head+raw);self.p.stdin.flush();data=b'';deadline=time.monotonic()+15;end=None
  while time.monotonic()<deadline:
   if select.select([self.p.stdout],[],[],.2)[0]:
    b=os.read(self.p.stdout.fileno(),65536)
    if not b:raise RuntimeError('TLS closed before complete HTTP response')
    data+=b
    if b'\r\n\r\n' in data:
     h,payload=data.split(b'\r\n\r\n',1);lines=h.decode().split('\r\n');status=int(lines[0].split()[1]);headers=dict(x.split(':',1) for x in lines[1:]);size=int(next(v for k,v in headers.items() if k.lower()=='content-length'))
     if len(payload)>=size:return status,json.loads(payload[:size])
  raise TimeoutError('HTTP response timeout')
 def feed(self,n):
  chunk=b'x'*65536;sent=0
  try:
   while sent<n:
    part=chunk[:min(len(chunk),n-sent)];self.p.stdin.write(part);self.p.stdin.flush();sent+=len(part)
  except (BrokenPipeError,OSError):pass
  finally:
   try:self.p.stdin.close()
   except OSError:pass
 def close(self):
  if self.p.poll() is None:self.p.terminate()
  try:self.p.wait(3)
  except subprocess.TimeoutExpired:self.p.kill();self.p.wait()
  self.log.close()
class Sink:
 def __init__(self):
  self.s=socket.socket();self.s.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1);self.s.bind(('203.0.113.1',29447));self.s.listen();self.s.settimeout(.2);self.rows=[];self.workers=[];self.stop=False
  def worker(c,row):
   h=hashlib.sha256();c.settimeout(10)
   try:
    while True:
     b=c.recv(65536)
     if not b:break
     row['bytes']+=len(b);h.update(b)
   except Exception as e:row['error']=repr(e)
   finally:row['sha256']=h.hexdigest();row['done']=True;c.close()
  def accept():
   while not self.stop:
    try:c,_=self.s.accept()
    except socket.timeout:continue
    except OSError:break
    row={'bytes':0,'done':False};self.rows.append(row);t=threading.Thread(target=worker,args=(c,row),daemon=True);self.workers.append(t);t.start()
  self.thread=threading.Thread(target=accept,daemon=True);self.thread.start()
 def wait(self,n):
  deadline=time.monotonic()+20
  while time.monotonic()<deadline:
   if len(self.rows)>=n and all(x['done'] for x in self.rows[:n]):return
   time.sleep(.05)
  raise TimeoutError('target stream completion')
 def close(self):
  self.stop=True;self.s.close();self.thread.join(1)
  for t in self.workers:t.join(1)
def run_case(variant,case):
 root=out/('runtime-'+variant+'-'+case);root.mkdir();(root/'model').mkdir(mode=0o700)
 log=(root/'helper.log').open('wb');binary=w/'binaries'/variant/'btx-modeld'
 args=[str(binary),'-modeldir='+str(root/'model'),'-modelbind=127.0.0.1:29448','-modelrelay','-modelstorage=0','-modelseed=off','-modelfollowpeers=0','-modellandiscovery=0','-modelnatpmp=0','-modelhost=0','-pwcchain=regtest']
 proc=subprocess.Popen(args,stdout=log,stderr=subprocess.STDOUT);clients=[];sink=None
 row={'variant':variant,'case':case,'helper_sha256':hashlib.sha256(binary.read_bytes()).hexdigest()}
 try:
  deadline=time.monotonic()+40
  while time.monotonic()<deadline:
   if proc.poll() is not None:raise RuntimeError('helper exited '+str(proc.returncode))
   if (root/'model/modeld.sock').exists() and (root/'model/tls/cert.pem').exists():
    try:rpc(root/'model/modeld.sock');break
    except (OSError,ValueError):pass
   time.sleep(.1)
  else:raise TimeoutError('helper readiness')
  sink=Sink()
  control=Client(root,'reserve');clients.append(control)
  status,hello=control.request('hello');require(status==200 and hello.get('suite')=='pq1' and hello.get('group')=='MLKEM768' and hello.get('sigalg')=='mldsa44','real strict PQ1 hello')
  status,res=control.request('ext/relay/reserve',{'relay_endpoint':'203.0.113.1:29447'});require(status==200 and res['byte_ceiling']==CAP,'native reservation failed '+str(res));rid=res['reservation_id'];control.close()
  def connect(name):
   c=Client(root,name);clients.append(c);status,obj=c.request('ext/relay/connect',{'endpoint':'203.0.113.1:29447','reservation_id':rid});return c,status,obj
  if case=='shared':
   a,sa,_=connect('A');b,sb,_=connect('B');require(sa==sb==200,'both connections admitted before payload')
   threads=[threading.Thread(target=c.feed,args=(20*1024**2,),daemon=True) for c in (a,b)]
   for t in threads:t.start()
   for t in threads:t.join(20);require(not t.is_alive(),'sender bounded completion')
   sink.wait(2);total=sum(x['bytes'] for x in sink.rows);row['observed_bytes']=total;row['contract_pass']=total==CAP
   require(total==(40*1024**2 if variant=='baseline' else CAP),'unexpected shared byte count '+str(total))
  elif case=='exhausted':
   a,sa,_=connect('fill');require(sa==200,'initial admission');t=threading.Thread(target=a.feed,args=(CAP,),daemon=True);t.start();t.join(20);require(not t.is_alive(),'initial sender completion');sink.wait(1);require(sink.rows[0]['bytes']==CAP,'exactly exhaust budget')
   deadline=time.monotonic()+10
   while time.monotonic()<deadline:
    info=rpc(root/'model/modeld.sock')
    if info['relay_reservations']['active_forwarded']==0:break
    time.sleep(.05)
   b,sb,obj=connect('reopen');row['reopen_status']=sb
   if sb==200:
    b.feed(1024);sink.wait(2)
   total=sum(x['bytes'] for x in sink.rows);row['observed_bytes']=total;row['contract_pass']=sb==403 and total==CAP
   require((sb==200 and total==CAP+1024) if variant=='baseline' else (sb==403 and total==CAP),'unexpected exhausted outcome '+str((sb,total,obj)))
  else:
   a,sa,_=connect('valid');require(sa==200,'valid admission');a.feed(65536);sink.wait(1);total=sum(x['bytes'] for x in sink.rows);require(total==65536,'valid bytes');row['observed_bytes']=total;row['contract_pass']=True
  for x in sink.rows:require(not x.get('error') and x['sha256']==hashlib.sha256(b'x'*x['bytes']).hexdigest(),'exact target bytes')
  deadline=time.monotonic()+10
  while time.monotonic()<deadline:
   info=rpc(root/'model/modeld.sock')
   if info['relay_reservations']['active_forwarded']==0:break
   time.sleep(.05)
  require(info['relay_reservations']['active_forwarded']==0,'active relay slots returned')
  require(info['relay_reservations']['forwarded_bytes']==sum(x['bytes'] for x in sink.rows),'counter matches actual target bytes')
  row['relay_after']=info['relay_reservations'];row['streams']=sink.rows;row['completed']=True
 except Exception as e:row['error']=repr(e);raise
 finally:
  for c in clients:c.close()
  if sink:sink.close()
  proc.terminate()
  try:proc.wait(10)
  except subprocess.TimeoutExpired:proc.kill();proc.wait(5)
  log.close();row['helper_exit']=proc.returncode;summary['cases'].append(row);save()
try:
 build=json.loads((out/'build-result.json').read_text());require(build['complete'],'full helper build gate')
 for variant in ('baseline','candidate'):
  for case in ('valid','shared','exhausted'):run_case(variant,case)
 summary['complete']=True
 require(qualifies(summary),"strict six-case result validation")
except Exception as e:summary['error']=repr(e);print('NATIVE ERROR',repr(e),flush=True)
finally:save()
raise SystemExit(0 if summary['complete'] and not summary.get('error') else 1)
