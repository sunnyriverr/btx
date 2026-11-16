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
 def compile_object(line,src,obj,label,candidate_headers=False):
  cc=command(line);cc[cc.index('-c')+1]=str(src);cc[cc.index('-o')+1]=str(obj)
  clean=[];i=0
  while i<len(cc):
   if cc[i]in ('-MF','-MT','-MQ'):i+=2;continue
   if cc[i]in ('-MD','-MMD'):i+=1;continue
   clean.append(cc[i]);i+=1
  if candidate_headers:clean.insert(1,'-I'+str(w/'candidate/src'))
  run(clean,label,120,cwd=build)
  return clean
 main_line=next(x for x in lines if' -c 'in x and'/src/modeld.cpp'in x)
 client_line=next(x for x in lines if' -c 'in x and'/src/modelnet/s3_client.cpp'in x)
 driver=out/'driver.o';compile_object(main_line,w/'probe/client.cpp',driver,'driver-compile')
 link=command(next(x for x in lines if' -o bin/btx-modeld 'in x));mains=[i for i,x in enumerate(link)if x.endswith('/modeld.cpp.o')];assert len(mains)==1
 def link_binary(main,extra,dest,label):
  cmd=list(link);cmd[mains[0]]=str(main);cmd[cmd.index('-o')+1]=str(dest)
  if extra:cmd.insert(mains[0]+1,str(extra))
  run(cmd,label,120,cwd=build)
 before=out/'completion-before';link_binary(driver,None,before,'baseline-link');r['baseline_binary_sha256']=sha(before)
 os.environ['BTX_COMPLETION_CREDENTIALS']='aws_access_key_id=completion-test-only\naws_secret_access_key=completion-fixture-not-real\n'
 run([sys.executable,w/'qualify.py','--client',before,'--probe-dir',w/'probe','--out',out/'before'],'same-probe-before',120,expected=1)
 before_result=json.loads((out/'before/qualification.json').read_text());assert before_result['failed_cases']==['known_error200_retry','unknown_error200_retry'];r['before']=before_result;save()
 client_obj=out/'candidate-s3-client.o';compile_object(client_line,w/'candidate/src/modelnet/s3_client.cpp',client_obj,'candidate-client-compile',True)
 after=out/'completion-after';link_binary(driver,client_obj,after,'candidate-link');r['candidate_binary_sha256']=sha(after)
 run([sys.executable,w/'qualify.py','--client',after,'--probe-dir',w/'probe','--out',out/'after'],'same-probe-after',120)
 r['after']=json.loads((out/'after/qualification.json').read_text());assert r['after']['correctness_pass']and len(r['after']['passed_cases'])==6;save()
 # Candidate-only table-driven test of the new predicate; exact maintained body.
 assert (w/'regression.inc').read_text()in(w/'unit-driver.cpp').read_text()
 assert (w/'regression.inc').read_text()in(w/'candidate/src/test/modelnet_cloud_tests.cpp').read_text()
 unit_obj=out/'unit-driver.o';compile_object(main_line,w/'unit-driver.cpp',unit_obj,'unit-driver-compile',True)
 unit=out/'completion-unit';link_binary(unit_obj,client_obj,unit,'unit-link')
 run([unit,'--log_level=test_suite','--report_level=detailed'],'maintained-envelope-vectors',60)
 # Normal maintained test source syntax with its actual existing compile flags.
 tlines=(w/'build-results/test-build-commands.log').read_text().splitlines()
 test_line=next(x for x in tlines if' -c 'in x and'/src/test/modelnet_cloud_tests.cpp'in x)
 cc=command(test_line);clean=[];i=0
 while i<len(cc):
  if cc[i]in ('-MF','-MT','-MQ','-o'):i+=2;continue
  if cc[i]in ('-MD','-MMD','-c'):i+=1;continue
  clean.append(str(w/'candidate/src/test/modelnet_cloud_tests.cpp')if cc[i].endswith('/src/test/modelnet_cloud_tests.cpp')else cc[i]);i+=1
 clean.insert(1,'-I'+str(w/'candidate/src'));clean.insert(1,'-fsyntax-only');run(clean,'maintained-source-syntax',120,cwd=build)
 r['candidate_sources']={str(x.relative_to(w/'candidate')):sha(x)for x in(w/'candidate').rglob('*')if x.is_file()}
 r['same_wire_fixture_sha256']={x.name:sha(x)for x in(w/'probe').glob('*')if x.is_file()}
 r['complete']=True
except Exception as e:r['error']=repr(e);print('REPAIR ERROR',repr(e),flush=True)
finally:
 try:
  retained=w/'probe-retention';retained.mkdir(exist_ok=True)
  with tarfile.open(retained/'completion-repair-binaries.tar.gz','w:gz',compresslevel=1)as t:
   for name in ('completion-before','completion-after','completion-unit'):
    binary=out/name
    if binary.exists():t.add(binary,arcname=name);binary.unlink()
  r['retained_binaries_sha256']=sha(retained/'completion-repair-binaries.tar.gz')
 except Exception as e:r['retention_error']=repr(e)
 save()
raise SystemExit(0 if r['complete']and not r.get('error')and not r.get('retention_error')else 1)
