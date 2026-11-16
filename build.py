from pathlib import Path
import os,sys,json,subprocess,tarfile,shutil,time,selectors,signal,hashlib
from checkpoint import sha,restore_timestamps,verify_restored,create
HEAD='1e2f8b5f12295002334d3390c12cac0bb4ae2aff';OLD=HEAD;ARCHIVE='214c4b13426bf50fbe17a8dd64d1a7f108a96eb8b8162fcfa2f147a35c98880e'
w=Path(os.environ['GITHUB_WORKSPACE']);out=w/'records';out.mkdir(exist_ok=True);r={'source':HEAD,'checkpoint_source':OLD,'complete':False,'commands':[]};restored=False

def save():(out/'build-result.json').write_text(json.dumps(r,indent=2)+'\n')
def run(cmd,label,limit=120,cwd=None,expected=0):
 p=subprocess.Popen([str(x) for x in cmd],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,cwd=cwd,start_new_session=True);start=time.monotonic();data=[];sel=selectors.DefaultSelector();sel.register(p.stdout,selectors.EVENT_READ)
 with (out/(label+'.log')).open('wb') as f:
  while p.poll() is None or sel.get_map():
   for key,_ in sel.select(.5):
    chunk=os.read(key.fileobj.fileno(),65536)
    if not chunk:sel.unregister(key.fileobj);continue
    f.write(chunk);f.flush();data.append(chunk);sys.stdout.buffer.write(chunk);sys.stdout.flush()
   if (time.monotonic()-start>limit or shutil.disk_usage(w).free<2*1024**3) and p.poll() is None:
    os.killpg(p.pid,signal.SIGTERM)
    try:p.wait(10)
    except subprocess.TimeoutExpired:os.killpg(p.pid,signal.SIGKILL);p.wait()
  p.wait()
 r['commands'].append({'step':label,'exit':p.returncode,'seconds':time.monotonic()-start});save()
 if p.returncode!=expected:raise RuntimeError(label+' exit '+str(p.returncode))
 return b''.join(data).decode(errors='replace')
try:
 prior=json.loads((w/'build-results/build-result.json').read_text());assert prior['complete']and prior['paired_cases_complete']
 m=json.loads((w/'saved-checkpoint/manifest.json').read_text());arc=w/'saved-checkpoint/build-state.tar.gz'
 assert sha(arc)==prior['retained_checkpoint_sha256']==m['archive_sha256']
 assert m['workspace']==str(w)and m['identity']['source']==HEAD
 with tarfile.open(arc)as t:t.extractall(w,filter='data')
 restore_timestamps(w,m);verify_restored(w,m);restored=True;r['checkpoint_verified']=True;save()
 source=w/'product';build=w/'gui-pilot-runtime/qtbuild'
 applicability=json.loads((w/'s3-current-applicability.json').read_text())
 import hashlib
 for name,row in applicability['files'].items():
  raw=(source/name).read_bytes();assert hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()==row['current_blob']
 r['current_source_applicability']=applicability;r['s3_source_unchanged']=True
 assert 'OpenSSL 3.5.9'in run([w/'gui-pilot-runtime/openssl/bin/openssl','version'],'openssl')
 assert run(['g++','-dumpfullversion'],'gcc').strip()=='11.4.0'
 assert '3.31.6'in run(['cmake','--version'],'cmake')
 import shlex
 def command(line):
  xs=shlex.split(line)
  if xs[:2]==[':','&&']:xs=xs[2:]
  if xs[-2:]==['&&',':']:xs=xs[:-2]
  assert '&&'not in xs and ';'not in xs
  return xs
 lines=(w/'build-results/modeld-build-commands.log').read_text().splitlines()
 cc=command(next(x for x in lines if' -c 'in x and'/src/modeld.cpp'in x));obj=out/'completion-client.o'
 cc[cc.index('-c')+1]=str(w/'probe/client.cpp');cc[cc.index('-o')+1]=str(obj)
 clean=[];i=0
 while i<len(cc):
  if cc[i]in ('-MF','-MT','-MQ'):i+=2;continue
  if cc[i]in ('-MD','-MMD'):i+=1;continue
  clean.append(cc[i]);i+=1
 run(clean,'probe-compile',120,cwd=build)
 link=command(next(x for x in lines if' -o bin/btx-modeld 'in x));mains=[i for i,x in enumerate(link)if x.endswith('/modeld.cpp.o')];assert len(mains)==1
 link[mains[0]]=str(obj);binary=out/'completion-client';link[link.index('-o')+1]=str(binary)
 run(link,'probe-link',120,cwd=build);r['probe_sha256']=sha(binary)
 os.environ['BTX_COMPLETION_CREDENTIALS']='aws_access_key_id=completion-test-only\naws_secret_access_key=completion-fixture-not-real\n'
 run([sys.executable,w/'probe/run.py','--client',binary,'--out',out/'probe'],'bounded-probe',120)
 result=json.loads((out/'probe/result.json').read_text());assert result['complete'];r['probe_result']=result;r['complete']=True
except Exception as e:r['error']=repr(e);print('PROBE ERROR',repr(e),flush=True)
finally:
 try:
  binary=out/'completion-client'
  if binary.exists():
   retained=w/'probe-retention';retained.mkdir(exist_ok=True)
   with tarfile.open(retained/'completion-client.tar.gz','w:gz',compresslevel=1)as t:t.add(binary,arcname='completion-client')
   r['retained_probe_sha256']=sha(retained/'completion-client.tar.gz');binary.unlink()
 except Exception as e:r['retention_error']=repr(e)
 save()
raise SystemExit(0 if r['complete']and not r.get('error')and not r.get('retention_error')else 1)
