from pathlib import Path
import os,sys,json,subprocess,shutil,time,signal,hashlib,selectors,re
w=Path(os.environ['GITHUB_WORKSPACE']);out=w/'records';source=w/'product';build=w/'gui-pilot-runtime/qtbuild';p=w/'proposal';pin='bd847e2b986722c1723b4cd60988d4f4908452d4'
r={'source':pin,'complete':False,'commands':[]};deadline=time.monotonic()+35*60

def sha(path):
 h=hashlib.sha256()
 with path.open('rb') as f:
  for b in iter(lambda:f.read(1024**2),b''):h.update(b)
 return h.hexdigest()
def save():(out/'qualification.json').write_text(json.dumps(r,indent=2)+'\n')
def run(cmd,label,limit,cwd=None,allowed=(0,)):
 assert time.monotonic()<deadline
 start=time.monotonic();data=[];log=(out/(label+'.log')).open('wb')
 proc=subprocess.Popen([str(x)for x in cmd],cwd=cwd or w,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,start_new_session=True)
 sel=selectors.DefaultSelector();sel.register(proc.stdout,selectors.EVENT_READ)
 try:
  while sel.get_map():
   for key,_ in sel.select(1):
    b=os.read(key.fileobj.fileno(),65536)
    if not b:sel.unregister(key.fileobj);continue
    data.append(b);log.write(b);log.flush();sys.stdout.buffer.write(b);sys.stdout.buffer.flush()
   if proc.poll()is None and (time.monotonic()-start>limit or time.monotonic()>deadline or shutil.disk_usage(w).free<3*1024**3):
    os.killpg(proc.pid,signal.SIGTERM)
    try:proc.wait(10)
    except subprocess.TimeoutExpired:os.killpg(proc.pid,signal.SIGKILL);proc.wait()
  proc.wait()
 finally:sel.close();log.close()
 r['commands'].append({'label':label,'exit':proc.returncode,'seconds':time.monotonic()-start});save()
 assert proc.returncode in allowed,(label,proc.returncode)
 return b''.join(data).decode(errors='replace')
try:
 assert json.loads((out/'staging.json').read_text())['complete']
 ref=w/'current-reference';assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=ref,text=True).strip()==pin
 tracked=subprocess.check_output(['git','ls-files','-z'],cwd=ref,text=True).split('\0');tracked=[x for x in tracked if x]
 changed=[]
 for name in tracked:
  a=ref/name;b=source/name
  same=(b.is_symlink()and os.readlink(b)==os.readlink(a))if a.is_symlink()else(b.is_file()and not b.is_symlink()and sha(a)==sha(b))
  if same:continue
  b.parent.mkdir(parents=True,exist_ok=True)
  if b.is_symlink()or b.is_file():b.unlink()
  if a.is_symlink():b.symlink_to(os.readlink(a))
  else:shutil.copy2(a,b);os.utime(b,None)
  changed.append(name)
 r['baseline_changes_from_checkpoint']=changed;save()
 run(['git','init'],'git-init',30,source);run(['git','fetch','--depth=1','https://github.com/btxchain/btx.git',pin],'git-fetch',90,source);run(['git','update-ref','HEAD',pin],'git-head',30,source);run(['git','read-tree',pin],'git-index',30,source)
 for name in tracked:
  a=ref/name;b=source/name
  assert (os.readlink(a)==os.readlink(b))if a.is_symlink()else sha(a)==sha(b),name
 r['baseline_tracked_source_verified']=True;save()
 os.environ['BTX_OPENSSL']=str(w/'gui-pilot-runtime/openssl/bin/openssl');run([os.environ['BTX_OPENSSL'],'version'],'openssl',30)
 run(['g++','-dumpfullversion'],'gcc',30)
 helper=build/'bin/btx-modeld';test=build/'bin/test_btx'
 def compile_phase(phase):
  snapshot=build/('qualification-'+phase+'.ninja');shutil.copy2(build/'build.ninja',snapshot)
  dry=run(['ninja','-f',snapshot,'-n','btx-modeld','test_btx'],phase+'-dry',90,build)
  actions=len(dry.splitlines());r[phase+'_planned_lines']=actions;save();assert actions<=220,(phase,'unbounded rebuild',actions)
  run(['ninja','-j2','btx-modeld','test_btx'],phase+'-build',15*60,build)
  r[phase+'_helper_sha256']=sha(helper);save()
  dest=w/'retained-binaries'/phase;dest.mkdir(parents=True,exist_ok=True)
  for binary in (helper,test):shutil.copy2(binary,dest/binary.name)
 def native(phase):
  run([sys.executable,p/'native.py','--helper',helper,'--helper-sha256',sha(helper),'--expect',phase,'--out',out/(phase+'-native')],phase+'-native',300,allowed=(2,)if phase=='baseline'else(0,))
  result=json.loads((out/(phase+'-native/result.json')).read_text());assert result['complete'];assert len(result['contract_failures'])==(2 if phase=='baseline' else 0)
  r[phase+'_native_result']=result;save()
 prior=json.loads((p/'baseline-evidence.json').read_text())
 assert prior['source']==pin and prior['native_script_sha256']==sha(p/'native.py')
 assert prior['baseline_native_result']['complete'] and len(prior['baseline_native_result']['contract_failures'])==2
 r['baseline_reused_from']=prior['run'];r['baseline_native_result']=prior['baseline_native_result'];r['baseline_helper_sha256']=prior['baseline_helper_sha256'];save()
 patch=p/'candidate.patch';run(['git','apply','--check',patch],'patch-check',30,source);run(['git','apply',patch],'patch',30,source)
 changes=json.loads((p/'changes.json').read_text())
 for name,v in changes.items():assert sha(source/name)==v['candidate_sha256'],name
 r['candidate_payload_verified']=True;save()
 compile_phase('candidate')
 run([test,'--run_test=modelnet_cloud_tests','--log_level=test_suite','--logger=JUNIT,all,'+str(out/'cloud-suite.xml')],'candidate-cloud-suite',240,build)
 import xml.etree.ElementTree as ET
 root=ET.parse(out/'cloud-suite.xml').getroot();assert not list(root.iter('failure')) and not list(root.iter('error')) and not list(root.iter('skipped'))
 names={x.attrib.get('name')for x in root.iter('testcase')};required={'cloud_verified_upload_ignores_external_source_changes','cloud_verified_reader_withholds_invalid_last_piece_and_retries','cloud_verified_reader_exact_lengths_and_corrupt_piece','cloud_verified_reader_empty_identity'};assert required<=names,(required-names,names)
 r['candidate_cloud_cases']=len(names);r['new_cases_verified']=sorted(required);save()
 native('candidate');r['complete']=True;save()
except Exception as e:r['error']=repr(e);save();raise
finally:
 # Existing immutable remote checkpoint remains retained. Upload only binaries and text records.
 try:
  from checkpoint import create
  checkpoint=create(w,w/'qualified-checkpoint',{'source':pin,'upload_candidate':r.get('candidate_payload_verified',False),'complete':r['complete']},reserve=int(1.25*1024**3))
  r['checkpoint_retained']={'archive_sha256':checkpoint['archive_sha256'],'identity':checkpoint['identity']}
 except Exception as e:r['checkpoint_retention_error']=repr(e)
 r['retained_binaries']={str(x.relative_to(w/'retained-binaries')):sha(x)for x in (w/'retained-binaries').rglob('*')if x.is_file()}if(w/'retained-binaries').exists()else{};save()
