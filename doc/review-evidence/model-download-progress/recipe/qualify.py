"""Bounded exact-current-tree qualification using the retained Linux cache."""
import hashlib,json,os,selectors,shutil,signal,subprocess,sys,time
from pathlib import Path
from results import validate_suite
w=Path(os.environ['GITHUB_WORKSPACE']);out=w/'records';source=w/'product';build=w/'gui-pilot-runtime/qtbuild';p=w/'proposal';ref=w/'current-reference';pin='23ee567ea8a2d9cad8ca3264f8793e8371b3eb93'
r={'source':pin,'complete':False,'commands':[]};deadline=time.monotonic()+47*60

def sha(x):
 h=hashlib.sha256()
 with x.open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
def save():(out/'qualification.json').write_text(json.dumps(r,indent=2)+'\n')
def run(cmd,label,limit,cwd=None,allowed=None):
 assert time.monotonic()<deadline
 start=time.monotonic();parts=[];log=(out/(label+'.log')).open('wb');proc=subprocess.Popen([str(x)for x in cmd],cwd=cwd or w,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,start_new_session=True)
 sel=selectors.DefaultSelector();sel.register(proc.stdout,selectors.EVENT_READ);timed_out=False
 try:
  while sel.get_map():
   for key,_ in sel.select(1):
    b=os.read(key.fileobj.fileno(),65536)
    if not b:sel.unregister(key.fileobj);continue
    parts.append(b);log.write(b);log.flush();sys.stdout.buffer.write(b);sys.stdout.buffer.flush()
   if proc.poll() is None and (time.monotonic()-start>limit or time.monotonic()>deadline or shutil.disk_usage(w).free<3*1024**3):
    timed_out=True;os.killpg(proc.pid,signal.SIGTERM)
    try:proc.wait(10)
    except subprocess.TimeoutExpired:os.killpg(proc.pid,signal.SIGKILL);proc.wait()
  proc.wait()
 finally:sel.close();log.close()
 r['commands'].append({'label':label,'exit':proc.returncode,'seconds':time.monotonic()-start,'timed_out_or_disk_gate':timed_out});save()
 assert not timed_out,label+' exceeded bound or disk gate'
 if allowed is not None:assert proc.returncode in allowed,(label,proc.returncode)
 return proc.returncode,b''.join(parts).decode(errors='replace')
try:
 assert json.loads((out/'staging.json').read_text())['complete']
 assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=ref,text=True).strip()==pin
 os.environ['BTX_OPENSSL']=str(w/'gui-pilot-runtime/openssl/bin/openssl')
 closure=('src/modelnet/file_stream.cpp','src/modelnet/file_stream.h','src/modelnet/store.cpp','src/modelnet/store.h','src/modelnet/direct_seed.cpp','src/modelnet/direct_seed.h','src/modelnet/types.cpp','src/modelnet/types.h','src/test/modelnet_file_stream_tests.cpp','src/test/util/setup_common.cpp','src/test/util/setup_common.h','src/crypto/sha384.cpp','src/crypto/sha384.h','src/util/readwritefile.cpp','src/util/readwritefile.h')
 r['retained_stream_source_matches']={n:sha(source/n)==sha(ref/n) for n in closure};save()
 assert all(r['retained_stream_source_matches'].values()),'retained stream control source changed'
 reuse=json.loads((out/'baseline-reuse.json').read_text());assert reuse['complete']
 prior=json.loads((out/'reused/qualification.json').read_text())
 r['retained_stream_controls']=prior['retained_stream_controls'];r['retained_stream_reused_from_run']=44198067492
 r['retained_stream_scope']='Unchanged source-matched stream/store controls reused from44198067492, not rerun and not a current rebuilt test_btx.';save()
 tracked=[n for n in subprocess.check_output(['git','ls-files','-z'],cwd=ref,text=True).split('\0')if n]
 changed=[]
 for name in tracked:
  a=ref/name;b=source/name
  same=(b.is_symlink()and os.readlink(b)==os.readlink(a))if a.is_symlink()else(b.is_file()and not b.is_symlink()and sha(a)==sha(b)and (a.stat().st_mode&0o111)==(b.stat().st_mode&0o111))
  if same:continue
  b.parent.mkdir(parents=True,exist_ok=True)
  if b.is_symlink()or b.is_file():b.unlink()
  if a.is_symlink():b.symlink_to(os.readlink(a))
  else:shutil.copy2(a,b);os.utime(b,None)
  changed.append(name)
 # Remove only tracked files explicitly deleted since the checkpoint base.
 deleted=subprocess.check_output(['git','diff','--name-only','--diff-filter=D','bd847e2b986722c1723b4cd60988d4f4908452d4',pin],cwd=ref,text=True).splitlines()
 for name in deleted:
  x=source/name
  if x.is_file()or x.is_symlink():x.unlink()
 r['current_overlay_changed']=changed;r['current_deleted']=deleted;save()
 for name in tracked:
  a=ref/name;b=source/name
  assert (b.is_symlink() and os.readlink(a)==os.readlink(b))if a.is_symlink()else sha(a)==sha(b),name
 run(['git','init'],'product-git-init',30,source,(0,))
 r['tracked_current_verified']=True
 changes=json.loads((p/'repair-changes.json').read_text())
 for name,meta in changes.items():assert sha(source/name)==meta['baseline_sha256'],name
 # Identical maintained regression in both trees; baseline differs only in helper.
 test_source=source/'test/functional/feature_modelnet_retrieve_regressions.py';shutil.copy2(p/'feature_modelnet_retrieve_regressions.py',test_source);os.utime(test_source,None)
 os.environ['BTX_OPENSSL']=str(w/'gui-pilot-runtime/openssl/bin/openssl');run([os.environ['BTX_OPENSSL'],'version'],'openssl',30,allowed=(0,));run(['g++','-dumpfullversion'],'gcc',30,allowed=(0,))
 helper=build/'bin/btx-modeld'
 def phase(name):
  snapshot=build/('cancel-'+name+'.ninja');shutil.copy2(build/'build.ninja',snapshot)
  _,dry=run(['ninja','-f',snapshot,'-n','btx-modeld'],name+'-dry',90,build,(0,))
  actions=[x for x in dry.splitlines()if x.startswith('[')];r[name+'_planned_actions']=len(actions);save();assert 0<len(actions)<=120,'rebuild exceeds120action gate'
  run(['ninja','-j2','btx-modeld'],name+'-build',900,build,(0,))
  dest=w/'retained-binaries'/name;dest.mkdir(parents=True,exist_ok=True)
  for x in (helper,):shutil.copy2(x,dest/x.name)
  r[name+'_binaries']={x.name:sha(x)for x in (helper,)};r[name+'_source']={n:sha(source/n)for n in changes};save()
  native(name,helper)
 def native(name,helper):
  assert deadline-time.monotonic()>1140,'insufficient bounded runtime plus cleanup headroom'
  run([sys.executable,p/'native.py','--helper',helper,'--sha256',sha(helper),'--expect',name,'--out',out/(name+'-native')],name+'-native',1140,allowed=(0,))
  result=json.loads((out/(name+'-native/result.json')).read_text());assert result['complete']and result['clean_cleanup'];r[name+'_native']=result;save()
 baseline=w/'baseline-helper/bin/btx-modeld';assert sha(baseline)==reuse['helper_sha256']
 r['baseline_binaries']={'btx-modeld':sha(baseline)};r['baseline_build_reused_from_run']=44198067492
 (w/'retained-binaries/baseline').mkdir(parents=True,exist_ok=True);shutil.copy2(baseline,w/'retained-binaries/baseline/btx-modeld');save()
 native('baseline',baseline)
 # Apply only the product part after using identical tests on the baseline.
 candidate=(p/'candidate.patch').read_text();product_patch=candidate.split('--- a/test/functional/feature_modelnet_retrieve_regressions.py')[0]
 (p/'product-only.patch').write_text(product_patch)
 run(['git','apply','--check',p/'product-only.patch'],'product-patch-check',30,source,(0,));run(['git','apply',p/'product-only.patch'],'product-patch',30,source,(0,))
 for n,meta in changes.items():assert sha(source/n)==meta['candidate_sha256'],n
 phase('candidate');r['complete']=True;save()
except Exception as e:r['error']=repr(e);save();raise
finally:
 r['retained_binaries']={str(x.relative_to(w/'retained-binaries')):sha(x)for x in (w/'retained-binaries').rglob('*')if x.is_file()}if(w/'retained-binaries').exists()else{}
 r['input_checkpoint_preserved_remote']=14307015983
 if r.get('candidate_binaries'):
  try:
   from checkpoint import create
   current=create(w,w/'helper-current-checkpoint',{'source':pin,'helper_progress_candidate':True,'qualification_complete':r['complete'],'test_btx_scope':'old retained binary and unchanged stream controls; current aggregate test target NOT rebuilt'},reserve=int(1.25*1024**3))
   r['updated_checkpoint']={'archive_sha256':current['archive_sha256'],'identity':current['identity']}
  except Exception as e:r['updated_checkpoint_error']=repr(e)
 save()
