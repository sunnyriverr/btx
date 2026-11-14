"""Exact supplied backports, bounded native compilation, durable platform evidence."""
from pathlib import Path
import os,sys,json,subprocess,time,hashlib,shutil,platform,tarfile,io,zipfile,urllib.request,urllib.error,signal,traceback,resource
resource.setrlimit(resource.RLIMIT_CORE,(0,0))
W=Path(os.environ['GITHUB_WORKSPACE']);R=W/'records';R.mkdir(exist_ok=True);S=W/'product';B=W/'mac-config-build';F=Path(__file__).resolve().parent
BEGAN=time.monotonic()
EXECUTION_LIMIT=4800
STATE={'base':'a5d1637facc925ff176507fae87fc2042940829d','producer_source':'c6f9678dd225572528d06c456c16eb4c78bc637c','commands':[],'tests':[],'complete':False}
ENV=dict(os.environ);ENV['NINJA_STATUS']='[%f/%t %es] '
def save(): (R/'result.json').write_text(json.dumps(STATE,indent=2)+'\n')
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def cmd(args,label,limit=120,cwd=W,check=True):
 assert time.monotonic()-BEGAN<EXECUTION_LIMIT,'Global execution budget reached; preserve state'
 print('START '+label,flush=True);start=time.monotonic();limit=min(limit,EXECUTION_LIMIT-(start-BEGAN));save()
 with (R/(label+'.log')).open('w') as log:
  p=subprocess.Popen(list(map(str,args)),cwd=cwd,env=ENV,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
  timeout=False;last=0
  while p.poll() is None:
   elapsed=time.monotonic()-start
   if elapsed>limit or shutil.disk_usage(W).free<10*1024**3:
    timeout=True;os.killpg(p.pid,signal.SIGTERM)
    try:p.wait(timeout=10)
    except subprocess.TimeoutExpired:os.killpg(p.pid,signal.SIGKILL);p.wait()
    break
   if elapsed-last>=30:
    last=elapsed;tail=(R/(label+'.log')).read_text(errors='replace')[-400:];print(label+f' {elapsed:.0f}s '+tail.replace('\n',' | '),flush=True)
   time.sleep(.5)
 text=(R/(label+'.log')).read_text(errors='replace');row={'label':label,'args':list(map(str,args)),'returncode':p.returncode,'seconds':round(time.monotonic()-start,2),'bounded_stop':timeout};STATE['commands'].append(row);save();print('END '+label+' '+json.dumps(row),flush=True)
 if check and (p.returncode or timeout):raise RuntimeError(label+' failed; exact log retained')
 return p.returncode,text

def restore():
 class NR(urllib.request.HTTPRedirectHandler):
  def redirect_request(self,*args):return None
 req=urllib.request.Request('https://api.github.com/repos/sunnyriverr/btx/actions/artifacts/13868692030/zip',headers={'Authorization':'Bearer '+os.environ['GH_TOKEN'],'User-Agent':'BTX-native-acceptance'})
 try:urllib.request.build_opener(NR).open(req,timeout=30);raise RuntimeError('Missing artifact redirect')
 except urllib.error.HTTPError as e:
  if e.code!=302:raise RuntimeError('Artifact request failed '+str(e.code)) from None
  url=e.headers['Location']
 size=1281923727
 class Remote(io.RawIOBase):
  def __init__(self):self.pos=0;self.count=0
  def readable(self):return True
  def seekable(self):return True
  def tell(self):return self.pos
  def seek(self,n,whence=0):self.pos=n if whence==0 else self.pos+n if whence==1 else size+n;return self.pos
  def read(self,n=-1):
   n=min(size-self.pos,n if n>=0 else size-self.pos)
   if n<=0:return b''
   assert n<=4*1024**2
   for attempt in range(3):
    try:
     with urllib.request.urlopen(urllib.request.Request(url,headers={'Range':f'bytes={self.pos}-{self.pos+n-1}'}),timeout=90) as r:
      assert r.status==206;b=r.read();assert len(b)==n
     self.pos+=n;self.count+=n;return b
    except Exception:
     if attempt==2:raise RuntimeError('Bounded artifact range failed; signed URL omitted') from None
     time.sleep(2)
 remote=Remote();payload=W/'producer';payload.mkdir()
 with zipfile.ZipFile(remote) as z:
  for name,digest in [('inventory.json','a059f0bf9d9115ba1baf802a7f0193e39a9b5c4ac398215e31d746d28690c290'),('checkpoint.tar.gz','54dc4a0566e034c5bd977fdf29e23baec2c93fa6ec67dbc0f46cc4b5dc42e4b7')]:
   dest=payload/name
   with z.open('cmake-chunk-checkpoint/after/'+name) as f,dest.open('wb') as out:
    while b:=f.read(1024**2):out.write(b)
   assert sha(dest)==digest,(name,'checkpoint hash mismatch')
 inv=json.loads((payload/'inventory.json').read_text());count=0
 with tarfile.open(payload/'checkpoint.tar.gz') as t:
  for m in t:
   if not m.name.startswith('mac-config-build/'):continue
   assert '..' not in Path(m.name).parts and not Path(m.name).is_absolute()
   dest=W/m.name;meta=inv[m.name]
   assert dest.parent.resolve().is_relative_to(W.resolve()),'Archive parent escapes workspace'
   if m.isdir():dest.mkdir(parents=True,exist_ok=True);continue
   dest.parent.mkdir(parents=True,exist_ok=True)
   if m.issym():
    assert m.linkname==meta.get('archive_target',meta.get('target')),('Symlink differs from verified manifest',m.name)
    resolved=(dest.parent/m.linkname).resolve()
    assert resolved.is_relative_to(W.resolve()),('Symlink escapes task workspace',m.name)
    assert '.git' not in resolved.relative_to(W.resolve()).parts
    dest.symlink_to(m.linkname);continue
   assert m.isfile();data=t.extractfile(m).read();assert hashlib.sha256(data).hexdigest()==meta['sha256'];dest.write_bytes(data);dest.chmod(meta['mode']);os.utime(dest,ns=(meta['mtime_ns'],meta['mtime_ns']));count+=m.name.endswith('.o')
 matched=0;changed=0
 for name,meta in inv.items():
  if not name.startswith('product/') or meta['type']!='file':continue
  dest=W/name
  if dest.is_file() and not dest.is_symlink() and sha(dest)==meta['sha256']:
   os.utime(dest,ns=(meta['mtime_ns'],meta['mtime_ns']));matched+=1
  else:changed+=1
 STATE['restore']={'objects':count,'matched_source_mtimes_restored':matched,'different_or_missing_source_files':changed,'range_bytes':remote.count};save();print('RESTORE '+json.dumps(STATE['restore']),flush=True)

def apply(kind,reverse=False,only=None):
 for n in ([699] if only else [697,698,699,700]):
  args=['git','-C',S,'apply',*(['--reverse'] if reverse else []),F/f'{n}-{kind}.patch'];cmd(args,f'patch-{kind}-{n}'+('-reverse' if reverse else ''),30)

def plan(targets,label,cap):
 _,text=cmd(['ninja','-C',B,'-n',*targets],label,120)
 edges=sum(x.startswith('[') for x in text.splitlines());STATE.setdefault('plans',{})[label]={'edges':edges,'cap':cap,'targets':targets};save();print('PLAN '+label+': '+str(edges)+' edges',flush=True);return edges<=cap

def tests(stage):
 # Exact new RPC method in the supplied file; avoid its known unrelated mining test.
 wrapper=S/'test/functional/backport_rpc_focus.py'
 wrapper.write_text('from interface_rpc import RPCInterfaceTest\nRPCInterfaceTest.run_test = RPCInterfaceTest.test_batch_invalid_element_reply\nRPCInterfaceTest(__file__).main()\n')
 for tag,file,args in [('700','backport_rpc_focus.py',[]),('697','wallet_descriptor_range_bounds.py',['--descriptors']),('698-bloom','p2p_nobloomfilter_messages.py',[]),('698-empty','p2p_getblocktxn_empty.py',[])]:
  root=W/'test-data'/(stage+'-'+tag);root.parent.mkdir(exist_ok=True)
  code,text=cmd([ENV['TEST_PYTHON'],S/'test/functional'/file,'--configfile='+str(B/'test/config.ini'),'--tmpdir='+str(root),'--nocleanup','--timeout-factor=1',*args],stage+'-test-'+tag,240,check=False)
  facts=[]
  for i,log in enumerate(root.rglob('*.log')):
   if log.name in ['test_framework.log','debug.log']:
    dest=R/(stage+'-'+tag+'-runtime-'+str(i)+'.log');dest.write_bytes(log.read_bytes()[-2*1024**2:]);facts.append(dest.name)
  STATE['tests'].append({'stage':stage,'case':tag,'exit':code,'log':stage+'-test-'+tag+'.log','runtime_logs':facts,'verdict':'passed' if code==0 else 'skipped' if code==77 else 'failure_needs_signature_review'});save()

def main():
 assert platform.machine()=='arm64';assert shutil.disk_usage(W).free>25*1024**3
 _,head=cmd(['git','-C',S,'rev-parse','HEAD'],'source');assert head.strip()==STATE['base']
 cmd(['xcodebuild','-version'],'xcode');_,cc=cmd(['xcrun','clang++','--version'],'clang');assert 'Apple clang version 17.0.0' in cc
 _,sdk=cmd(['xcrun','--sdk','macosx','--show-sdk-version'],'sdk');assert sdk.strip()=='15.5'
 STATE['image']=os.environ.get('ImageVersion');restore()
 cmd(['brew','install','--force-bottle','boost@1.85','libevent','zeromq','libomp','qt','qrencode','librsvg','libicns','python@3.12'],'dependencies',1200)
 _,ssl=cmd(['brew','--prefix','openssl@3'],'ssl-prefix');ssl=Path(ssl.strip())
 for name,digest in [('libssl.a','b1a96521d10e2ce59ece360814915ed33c0e65aa60f7a9844b8b94c5d048cc56'),('libcrypto.a','76304e70825b4522b15461ad29c9106db1eeb8d421a12a641c210dabb11ed375')]:assert sha(ssl/'lib'/name)==digest,(name,'static dependency identity changed')
 _,boost=cmd(['brew','--prefix','boost@1.85'],'boost-prefix');_,py=cmd(['brew','--prefix','python@3.12'],'python-prefix');python=Path(py.strip())/'bin/python3.12';ENV['TEST_PYTHON']=str(python)
 cmd([python,'-m','venv',W/'test-env'],'python-env');ENV['TEST_PYTHON']=str(W/'test-env/bin/python');cmd([ENV['TEST_PYTHON'],'-m','pip','install','cryptography==46.0.4'],'python-crypto',240)
 ENV.update(BTX_OPENSSL=str(ssl/'bin/openssl'),PATH=str(W/'test-env/bin')+':'+str(ssl/'bin')+':'+ENV['PATH'])
 args=['cmake','-S',S,'-B',B,'-G','Ninja','-DCMAKE_BUILD_TYPE=Release','-DCMAKE_PREFIX_PATH=/opt/homebrew','-DCMAKE_OSX_ARCHITECTURES=arm64','-DBoost_INCLUDE_DIR='+boost.strip()+'/include','-DOPENSSL_ROOT_DIR='+str(ssl),'-DOPENSSL_INCLUDE_DIR='+str(ssl/'include'),'-DOPENSSL_SSL_LIBRARY='+str(ssl/'lib/libssl.a'),'-DOPENSSL_CRYPTO_LIBRARY='+str(ssl/'lib/libcrypto.a'),'-DOPENSSL_USE_STATIC_LIBS=ON','-DWITH_ZMQ=ON','-DBTX_ENABLE_METAL=ON','-DBTX_MATMUL_METAL_PRECOMPILE_KERNELS=ON','-DWITH_MODELNET=ON','-DBUILD_GUI=ON','-DWITH_QT_VERSION=6','-DENABLE_WALLET=ON','-DWITH_SQLITE=ON','-DBUILD_BENCH=OFF','-DCMAKE_EXPORT_COMPILE_COMMANDS=ON','-DPython3_EXECUTABLE='+ENV['TEST_PYTHON']]
 apply('tests');cmd(args,'configure',300)
 cmd(['ninja','-C',B,'-d','explain','-n','btxd','btx-cli'],'baseline-dirty-explanation',120)
 if not plan(['btxd','btx-cli'],'baseline-node-plan',1500):raise RuntimeError('Node plan exceeds agreed bounded scope; checkpoint retained')
 cmd(['ninja','-C',B,'-j3','btxd','btx-cli'],'baseline-node-build',2100)
 keep=W/'retained-baseline';keep.mkdir()
 STATE['baseline_binary']={}
 for n in ['btxd','btx-cli']:
  f=B/'bin'/n;shutil.copy2(f,keep/n);STATE['baseline_binary'][n]=sha(f)
 save();tests('baseline');apply('product')
 cmd(['git','-C',S,'diff','--stat'],'candidate-diff');cmd(['git','-C',S,'diff','--binary'],'candidate-exact-diff')
 assert plan(['btxd','btx-cli'],'candidate-node-plan',100)
 cmd(['ninja','-C',B,'-j3','btxd','btx-cli'],'candidate-node-build',1200)
 STATE['candidate_binary']={n:sha(B/'bin'/n) for n in ['btxd','btx-cli']};save();tests('candidate')
 if plan(['test_btx'],'candidate-unit-plan',900) and time.monotonic()-BEGAN<3600:
  cmd(['ninja','-C',B,'-j3','test_btx'],'candidate-unit-build',1200)
  for label,selector in [('699-suite','denialofservice_tests')]:
   code,_=cmd([B/'bin/test_btx','--run_test='+selector,'--log_level=test_suite','--report_level=detailed'],'candidate-'+label,240,check=False);STATE['tests'].append({'stage':'candidate','case':label,'exit':code});save()
  apply('product',reverse=True,only=699);cmd(['ninja','-C',B,'-j3','test_btx'],'without699-unit-build',480)
  code,_=cmd([B/'bin/test_btx','--run_test=denialofservice_tests/orphan_reconsideration_interruptible','--log_level=test_suite','--report_level=detailed'],'without699-focused',240,check=False);STATE['tests'].append({'stage':'without699','case':'699-focused','exit':code});save();STATE['without699_binary_sha256']=sha(B/'bin/test_btx');apply('product',only=699);cmd(['ninja','-C',B,'-j3','test_btx'],'restore-final-candidate-unit',480);STATE['final_candidate_unit_sha256']=sha(B/'bin/test_btx');save()
 else:STATE['unit_gate']='Measured unit plan exceeds900edges or60minute job budget already used; deferred without losing functional results';save()
 STATE['execution_finished']=True
 candidate=[x for x in STATE['tests'] if x['stage']=='candidate']
 STATE['complete']=len(candidate)>=4 and all(x['exit']==0 for x in candidate)
 STATE['acceptance']='Candidate executions pass; baseline signatures require exact log review' if STATE['complete'] else 'Incomplete or failed candidate; no acceptance claim'
 save()
if __name__ == '__main__':
 try:main()
 except Exception as e:STATE['error']=str(e);(R/'exception.txt').write_text(traceback.format_exc())
 finally:save()
 sys.exit(0 if STATE['complete'] else 1)
