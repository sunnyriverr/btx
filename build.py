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
 prior=json.loads((w/'build-results/build-result.json').read_text());assert prior['complete'] and prior['paired_cases_complete'] and not prior.get('error')
 m=json.loads((w/'saved-checkpoint/manifest.json').read_text());arc=w/'saved-checkpoint/build-state.tar.gz'
 assert sha(arc)==prior['retained_checkpoint_sha256']==m['archive_sha256']
 assert m['identity']['source']==HEAD and m['identity']['composition']==prior['composition']
 assert m['workspace']==str(w) and shutil.disk_usage(w).free>10*1024**3
 with tarfile.open(arc)as t:t.extractall(w,filter='data')
 restore_timestamps(w,m);verify_restored(w,m);r['checkpoint_verified']=True;restored=True;save()
 source=w/'product';build=w/'gui-pilot-runtime/qtbuild'
 for name,expected in prior['composition']['files'].items():assert sha(source/name)==expected
 bundle=w/'saved-binaries/settings-binaries.tar.gz';assert sha(bundle)==prior['binary_archive_sha256']
 with tarfile.open(bundle)as t:
  assert all(x.name.startswith('qualified-binaries')for x in t.getmembers())
  assert all(x.isdir()or x.isfile()for x in t.getmembers())
  t.extractall(w,filter='data')
 for phase in ('baseline','candidate'):
  for name,expected in prior[phase+'_binaries'].items():assert sha(w/'qualified-binaries'/phase/name)==expected
 r['binaries_verified']=True;r['prior_binary_hashes']={p:prior[p+'_binaries']for p in ('baseline','candidate')};save()
 assert 'OpenSSL 3.5.9'in run([w/'gui-pilot-runtime/openssl/bin/openssl','version'],'openssl')
 assert run(['g++','-dumpfullversion'],'gcc').strip()=='11.4.0'
 assert '3.31.6'in run(['cmake','--version'],'cmake')
 import shlex
 def command(line):
  xs=shlex.split(line)
  if xs[:2]==[':','&&']:xs=xs[2:]
  if xs[-2:]==['&&',':']:xs=xs[:-2]
  assert '&&'not in xs and ';'not in xs,line
  return xs
 lines=(w/'build-results/modeld-build-commands.log').read_text().splitlines()
 comp=[line for line in lines if ' -c 'in line and '/src/modeld.cpp'in line];assert len(comp)==1
 cc=command(comp[0]);obj=out/'channel-fixture.o';fixture=w/'fixture/channel-fixture.cpp'
 cc[cc.index('-c')+1]=str(fixture);cc[cc.index('-o')+1]=str(obj)
 i=0;clean=[]
 while i<len(cc):
  if cc[i]in ('-MF','-MT','-MQ'):i+=2;continue
  if cc[i]in ('-MD','-MMD'):i+=1;continue
  clean.append(cc[i]);i+=1
 run(clean,'channel-fixture-compile',120,cwd=build)
 links=[line for line in lines if ' -o bin/btx-modeld 'in line];assert len(links)==1
 link=command(links[0]);mains=[i for i,x in enumerate(link)if x.endswith('/modeld.cpp.o')];assert len(mains)==1
 link[mains[0]]=str(obj);utility=out/'channel-fixture';link[link.index('-o')+1]=str(utility)
 run(link,'channel-fixture-link',120,cwd=build)
 r['fixture_utility_sha256']=sha(utility)
 os.environ['BTX_OPENSSL']=str(w/'gui-pilot-runtime/openssl/bin/openssl')
 # The runner helper inherits this pinned executable; no system OpenSSL substitution.
 payload=run([utility],'channel-fixture-payloads',60,cwd=build)
 records=json.loads(payload);assert len(records)==4 and all(x.get('pubkey')and x.get('signature')for x in records.values())
 payload_path=out/'channel-payloads.json';payload_path.write_text(payload)
 for phase in ('baseline','candidate'):
  run([sys.executable,w/'fixture/helper-retry-restart.py','--helper',w/'qualified-binaries'/phase/'btx-modeld','--channel-fixture',payload_path,'--out',out/phase,'--expect',phase],phase+'-native-helper',300)
  rr=json.loads((out/phase/'native-result.json').read_text());assert rr['complete']and rr['expected_observation']and rr['scratch_removed']
  assert len(rr['cases'])==5 and all(x['helper_clean_starts']==2 for x in rr['cases'].values())
  r[phase+'_native']=rr;save()
 r['complete']=True;r['no_product_rebuild']=True
except Exception as e:r['error']=repr(e);print('NATIVE ERROR',repr(e),flush=True)
finally:
 try:
  utility=out/'channel-fixture'
  if utility.exists():
   retained=w/'fixture-retention';retained.mkdir(exist_ok=True)
   with tarfile.open(retained/'channel-fixture.tar.gz','w:gz',compresslevel=1)as t:t.add(utility,arcname='channel-fixture')
   r['retained_fixture_archive_sha256']=sha(retained/'channel-fixture.tar.gz');utility.unlink()
 except Exception as e:r['fixture_retention_error']=repr(e)
 save()
raise SystemExit(0 if r['complete']and not r.get('error')and not r.get('fixture_retention_error')else 1)
