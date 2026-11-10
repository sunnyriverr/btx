"""Bounded consumer compile/link against immutable retained production libraries."""
from pathlib import Path
import hashlib,json,os,re,shlex,shutil,signal,subprocess,tarfile,time
from checkpoint import sha,restore_timestamps,verify_restored
ARCHIVE='c4b58e4ef14e93f8b257c18bc855a7d9e4079a4659c9e3266fd25acad50d66df'
HERE=Path(__file__).resolve().parent

def main():
 w=Path(os.environ['GITHUB_WORKSPACE']);out=w/'cloud-native-records';out.mkdir(exist_ok=True);bins=w/'cloud-native-binaries';bins.mkdir(exist_ok=True)
 r={'product_modified':False,'production_recompiled':False,'consumer_compiled':False,'product_executed':False,'commands':[]}
 def run(cmd,label,cwd=w,limit=180,allow_error=False):
  start=time.monotonic()
  with (out/(label+'.log')).open('wb') as f:
   p=subprocess.Popen(list(map(str,cmd)),cwd=cwd,stdout=f,stderr=subprocess.STDOUT,start_new_session=True)
   try:
    while p.poll() is None:
     if time.monotonic()-start>limit or shutil.disk_usage(w).free<2*1024**3:raise RuntimeError(label+' resource limit')
     time.sleep(.25)
   except BaseException:
    os.killpg(p.pid,signal.SIGTERM)
    try:p.wait(10)
    except subprocess.TimeoutExpired:os.killpg(p.pid,signal.SIGKILL);p.wait()
    raise
  r['commands'].append({'label':label,'exit':p.returncode,'seconds':time.monotonic()-start})
  assert allow_error or p.returncode==0,label
  return p.returncode,(out/(label+'.log')).read_text(errors='replace')
 try:
  assert shutil.disk_usage(w).free>6*1024**3
  saved=w/'saved-checkpoint';m=json.loads((saved/'manifest.json').read_text());a=saved/'build-state.tar.gz'
  assert sha(a)==ARCHIVE==m['archive_sha256'] and m['identity']['integration_tree']=='ed72649dc18f4eaf55c9a6d1a2b171e587b482dd'
  assert Path(m['workspace'])==w and not (w/'product').exists()
  with tarfile.open(a) as t:t.extractall(w,filter='data')
  restore_timestamps(w,m);verify_restored(w,m);r['restore_verified']=True;r['cached_identity']=m['identity'];r['archive_sha256']=ARCHIVE
  src=w/'product';build=w/'gui-pilot-runtime/qtbuild'
  hashes=json.loads((HERE/'source-hashes.json').read_text());assert all(sha(src/p)==h for p,h in hashes.items());r['cloud_source_sha256']=hashes
  assert run(['g++','-dumpfullversion'],'compiler')[1].strip()=='11.4.0'
  assert 'OpenSSL 3.5.9' in run([w/'gui-pilot-runtime/openssl/bin/openssl','version'],'openssl')[1]
  commands=run(['ninja','-C',build,'-t','commands','btx-modeld'],'cached-commands')[1].splitlines()
  cc=[shlex.split(l) for l in commands if l.rstrip().endswith('-c '+str(src/'src/modelnet/s3_store.cpp'))];assert len(cc)==1
  cc=cc[0];flags=[];i=1
  while i<len(cc):
   x=cc[i]
   if x in ('-MT','-MF','-o','-c'):i+=2;continue
   if x=='-MD':i+=1;continue
   flags.append(x);i+=1
  link=shlex.split(commands[-1]);assert link[:3]==[':', '&&','/usr/bin/g++'] and link[-2:]==['&&',':'];link=link[2:-2]
  original='src/modelnet/CMakeFiles/btx-modeld.dir/__/modeld.cpp.o';assert link.count(original)==1
  obj=bins/'consumer.o';binary=bins/'cloud-budget-consumer';link[link.index(original)]=str(obj);link[link.index('-o')+1]=str(binary)
  # Keep ordinary symbol checking: no relaxed shared-library resolution.
  link.remove('-Wl,--unresolved-symbols=ignore-in-shared-libs')
  compile=[cc[0],*flags,'-o',str(obj),'-c',str(HERE/'consumer.cpp')]
  r['admitted_actions']={'compile':compile,'link':link};r['action_count']=2
  assert len(r['admitted_actions'])<=20 and not any('helper.cpp' in x for x in compile+link)
  for x in link:
   if x.endswith(('.a','.so')) and not x.startswith('-'):assert (build/x).is_file(),x
  (out/'build-plan.json').write_text(json.dumps(r['admitted_actions'],indent=2)+'\n')
  r['consumer_compiled']=True;run(compile,'consumer-compile',build,limit=300);run(link,'consumer-link',build,limit=300)
  run(['ldd',binary],'ldd');assert 'not found' not in (out/'ldd.log').read_text()
  identity={'source_tree':m['identity']['integration_tree'],'binary_sha256':sha(binary),'harness_sha256':sha(HERE/'consumer.cpp')}
  (out/'identity.json').write_text(json.dumps(identity,indent=2)+'\n');r['identity']=identity
  # Native process records observations. Product contract classification is separate.
  runtime=w/'cloud-native-runtime';raw=out/'raw.json';trace=out/'syscalls.log'
  r['product_executed']=True
  code,_=run(['strace','-f','-yy','-s','512','-e','trace=openat,write,writev,close,rename,renameat,renameat2','-o',trace,binary,runtime,raw],'native-observation',limit=90,allow_error=True)
  assert raw.is_file(),'native report absent';obs=json.loads(raw.read_text());obs.update(identity);obs['process_exit']=code
  budget=str(runtime/'budget.json');text=trace.read_text();lines=[l for l in text.splitlines() if budget in l and 'EFBIG' in l and re.search(r'\bwrite(v)?\(',l)]
  (out/'fault-write-evidence.log').write_text('\n'.join(lines)+'\n')
  if isinstance(obs.get('fault'),dict):obs['fault'].update(path=budget,trace_verified=bool(lines),write_failure='EFBIG' if lines else '')
  (out/'observations.json').write_text(json.dumps(obs,indent=2)+'\n')
  code,verdict=run(['python3',HERE/'classify.py',out/'observations.json',out/'identity.json'],'classification',allow_error=True)
  r['verdict']=verdict.strip();r['classifier_exit']=code
  assert r['verdict'] in ('PASS','REPRODUCED'),r['verdict']
  r['observation_complete']=True;r['safety_contract_pass']=r['verdict']=='PASS'
  assert sha(a)==ARCHIVE;r['original_archive_unchanged']=True
  # Only the consumer is new. No CMake or Ninja build target was executed.
  assert all(sha(src/p)==h for p,h in hashes.items());r['pass']=True
 except Exception as e:r['pass']=False;r['error']=repr(e)
 finally:
  for name in ['consumer.cpp','startup-regression.patch','classify.py']:
   shutil.copy2(HERE/name,out/name)
  (out/'result.json').write_text(json.dumps(r,indent=2)+'\n')
 return 0 if r['pass'] else 1
if __name__=='__main__':raise SystemExit(main())
