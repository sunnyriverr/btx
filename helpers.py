# Copyright (c) 2026 The BTX developers
# Distributed under the MIT software license, see COPYING.
"""Bounded real-helper/PQ1 observation; reuses maintained retrieve fixture shapes."""
from pathlib import Path
import hashlib, json, os, signal, socket, subprocess, time

def require(x,msg):
 if not x:raise RuntimeError(msg)
def digest(path,alg='sha256'):
 h=hashlib.new(alg)
 with Path(path).open('rb') as f:
  for b in iter(lambda:f.read(1<<20),b''):h.update(b)
 return h.hexdigest()
class Helper:
 def __init__(self,binary,root,out,label,cap,peer=None,hostport=None):
  self.binary=binary;self.root=root;self.out=out;self.label=label;self.cap=cap;self.peer=peer;self.hostport=hostport
  self.store=root/'modeldir';self.sock=root/'rpc.sock';self.proc=None;self.log=None;self.seq=0;self.starts=0;self.calls=[];self.forced=False;self.cleanup_error=None;self.start_info=[]
  self.store.mkdir(parents=True)
 def rpc(self,method,params=None):
  self.seq+=1
  with socket.socket(socket.AF_UNIX) as s:
   s.settimeout(45);s.connect(str(self.sock));s.sendall((json.dumps({'jsonrpc':'1.0','id':self.seq,'method':method,'params':params or []})+'\n').encode());s.shutdown(socket.SHUT_WR)
   with s.makefile('rb') as f:raw=f.readline(2*1024*1024)
  require(len(raw)<2*1024*1024,'RPC size');reply=json.loads(raw);require(reply['id']==self.seq,'RPC id')
  self.calls.append({'at':time.time(),'method':method,'params':params or [],'reply':reply});return reply
 def ok(self,method,params=None):
  r=self.rpc(method,params);require(not r.get('error'),method+': '+str(r.get('error')));return r['result']
 def info(self):return self.ok('getmodelnetworkinfo')
 def start(self):
  require(self.proc is None and not self.sock.exists(),'helper not cleanly stopped');self.starts+=1
  home=self.root/'home';home.mkdir(exist_ok=True)
  args=[str(self.binary),'-modeldir='+str(self.store),'-modelrpcsocket='+str(self.sock),'-modelstorage='+str(self.cap),'-modelfollowpeers=0','-modellandiscovery=0','-modelnatpmp=0','-modelseed='+('auto' if self.hostport else 'off'),'-pwcchain=regtest']
  if self.hostport:args+=['-modelhost','-modelbind=127.0.0.1:'+str(self.hostport)]
  else:args+=['-modelhost=0', *['-modelpeer='+x for x in (self.peer if isinstance(self.peer,list) else [self.peer])]]
  if getattr(self,'trace',None):args=['strace','-D','-f','-ttt','-e','trace=connect,clone,clone3','-o',str(self.trace),*args]
  self.log=(self.out/(self.label+'-'+str(self.starts)+'.log')).open('wb')
  self.proc=subprocess.Popen(args,stdout=self.log,stderr=subprocess.STDOUT,start_new_session=True,env=dict(os.environ,HOME=str(home),XDG_DATA_HOME=str(home/'data'),XDG_RUNTIME_DIR=str(self.root)))
  end=time.monotonic()+25
  while not self.sock.exists():
   require(self.proc.poll() is None and time.monotonic()<end,'helper startup');time.sleep(.1)
  require(Path('/proc/'+str(self.proc.pid)+'/exe').resolve()==self.binary.parent.parent/'libexec/btx-modeld.real','process binary')
  while True:
   info=self.info()
   if info.get('helper_ready') and info.get('pq1_ready'):break
   require(time.monotonic()<end,'helper/PQ1 readiness');time.sleep(.1)
  require(info.get('automatic_spend_atoms',0)==0,'automatic spend');self.start_info.append(info)
 def stop(self):
  if self.proc is None:return
  require(self.proc.poll() is None,'unexpected helper exit');self.proc.send_signal(signal.SIGTERM);self.proc.wait(25)
  require(self.proc.returncode==0 and not self.sock.exists(),'unclean helper shutdown');self.proc=None;self.log.close();self.log=None
 def cleanup(self):
  try:self.stop()
  except Exception as e:
   self.cleanup_error=str(e)
   if self.proc and self.proc.poll() is None:
    self.forced=True;os.killpg(self.proc.pid,signal.SIGKILL);self.proc.wait(10)
  if self.log:self.log.close()
  (self.out/(self.label+'-rpc.json')).write_text(json.dumps(self.calls,indent=2)+'\n')
 def job(self,jid):
  x=self.ok('getmodeljob',[jid])
  if 'jobs' in x:return next((j for j in x['jobs'] if str(j.get('job_id'))==str(jid)),{})
  return x
 def request(self,uri):
  r=self.ok('getmodel',[uri,'FREE_ONLY']);return r.get('job_id'),r
 def settled(self,jid,limit):
  end=time.monotonic()+limit
  while True:
   j=self.job(jid)
   if j.get('status') in ('done','failed','cancelled'):return j
   require(time.monotonic()<end,'job did not settle');time.sleep(.2)

