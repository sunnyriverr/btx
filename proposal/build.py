from pathlib import Path
import os,sys,json,subprocess,tarfile,shutil,time,selectors,signal,hashlib,re
from checkpoint import sha,restore_timestamps,verify_restored,create
PIN='bd847e2b986722c1723b4cd60988d4f4908452d4';w=Path(os.environ['GITHUB_WORKSPACE']);out=w/'records';out.mkdir(exist_ok=True);r={'source':PIN,'complete':False,'commands':[]};source=w/'product';build=w/'gui-pilot-runtime/qtbuild';restored=False;execution_deadline=time.monotonic()+38*60

def save():(out/'result.json').write_text(json.dumps(r,indent=2)+'\n')
def run(cmd,label,limit=120,cwd=None,allowed=(0,)):
 limit=min(limit,max(1,execution_deadline-time.monotonic()))
 p=subprocess.Popen([str(x)for x in cmd],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,cwd=cwd,start_new_session=True);start=time.monotonic();data=[];sel=selectors.DefaultSelector();sel.register(p.stdout,selectors.EVENT_READ)
 with (out/(label+'.log')).open('wb') as f:
  while p.poll() is None or sel.get_map():
   for key,_ in sel.select(.5):
    chunk=os.read(key.fileobj.fileno(),65536)
    if not chunk:sel.unregister(key.fileobj);continue
    f.write(chunk);f.flush();data.append(chunk);sys.stdout.buffer.write(chunk);sys.stdout.flush()
    if label in ('baseline-build','candidate-build'):
     totals=re.findall(rb'\[\d+/(\d+)\] (?:Building|Linking|Generating)',b''.join(data[-3:]))
     if totals:
      actual=max(map(int,totals));r[label+'_actual_actions']=actual
      if actual>(220 if label=='baseline-build' else 60) and p.poll() is None:
       r['unexpected_rebuild_guard']=label;os.killpg(p.pid,signal.SIGTERM)
   if (time.monotonic()-start>limit or shutil.disk_usage(w).free<3*1024**3)and p.poll()is None:
    os.killpg(p.pid,signal.SIGTERM)
    try:p.wait(10)
    except subprocess.TimeoutExpired:os.killpg(p.pid,signal.SIGKILL);p.wait()
  p.wait()
 r['commands'].append({'step':label,'argv':[str(x)for x in cmd],'exit':p.returncode,'seconds':time.monotonic()-start});save()
 assert p.returncode in allowed,(label,p.returncode)
 return b''.join(data).decode(errors='replace')
try:
 assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=w/'current-reference',text=True).strip()==PIN
 m=json.loads((w/'saved-checkpoint/manifest.json').read_text());arc=w/'saved-checkpoint/build-state.tar.gz';assert sha(arc)==m['archive_sha256'];assert len(m['archive_sha256'])==64;assert m['workspace']==str(w);assert m['identity']['source']=='371013d61dc124a363521df5b94e97f64d2464f2'
 with tarfile.open(arc)as t:t.extractall(w,filter='data')
 restore_timestamps(w,m);verify_restored(w,m);restored=True;r['checkpoint_verified']=True;save()
 reference=w/'current-reference';files=subprocess.check_output(['git','ls-files','-z'],cwd=reference,text=True).split('\0');files=[x for x in files if x];wanted=set(files);changed=[]
 for f in files:
  a=reference/f;b=source/f;b.parent.mkdir(parents=True,exist_ok=True)
  same=(b.is_symlink()and os.readlink(b)==os.readlink(a))if a.is_symlink()else(b.is_file()and not b.is_symlink()and sha(a)==sha(b))
  if same:continue
  if b.is_symlink()or b.is_file():b.unlink()
  if a.is_symlink():b.symlink_to(os.readlink(a))
  else:shutil.copy2(a,b);os.utime(b,None)
  changed.append(f)
 for p in list(source.rglob('*')):
  if (p.is_file()or p.is_symlink())and str(p.relative_to(source))not in wanted and '.git'not in p.parts:p.unlink()
 run(['git','init'],'product-git-init',cwd=source);run(['git','fetch','--depth=1','https://github.com/btxchain/btx.git',PIN],'product-git-fetch',cwd=source);run(['git','update-ref','HEAD',PIN],'product-git-head',cwd=source);run(['git','read-tree',PIN],'product-index',cwd=source)
 r['changed_from_checkpoint']=changed;save()
 assert '11.4.0'in run(['g++','-dumpfullversion'],'gcc');assert 'OpenSSL 3.5.9'in run([w/'gui-pilot-runtime/openssl/bin/openssl','version'],'openssl');os.environ['BTX_OPENSSL']=str(w/'gui-pilot-runtime/openssl/bin/openssl')
 run(['cmake','-S',source,'-B',build],'configure',180)

 targets=['btx-modeld','test_btx']
 testfile=source/'src/test/modelnet_cloud_tests.cpp'
 testfile.write_bytes((w/'proposal/modelnet_cloud_tests.cpp').read_bytes())
 run(['ninja','build.ninja'],'baseline-graph-regeneration',120,build)
 snapshot=build/'detach-plan.ninja';shutil.copy2(build/'build.ninja',snapshot)
 dry=run(['ninja','-f',snapshot,'-n',*targets],'baseline-plan',120,build);r['baseline_planned_lines']=len(dry.splitlines());assert 'Re-running CMake' not in dry and len(dry.splitlines())<230
 run(['ninja','-j2',*targets],'baseline-build',1200,build)
 test=build/'bin/test_btx';helper=build/'bin/btx-modeld';case='modelnet_cloud_tests/cloud_rpc_detach_removal_failure_preserves_origin_and_retry'
 r['baseline_hash']={n:sha(build/'bin'/n) for n in targets};save()
 run([test,'--run_test='+case,'--log_level=all','--log_format=XML','--log_sink='+str(out/'baseline-unit.xml')],'baseline-regression',120,build,allowed=(201,))
 import xml.etree.ElementTree as ET
 errors=ET.parse(out/'baseline-unit.xml').getroot().findall('.//Error')
 expected={i+1 for i,l in enumerate(testfile.read_text().splitlines()) if any(x in l for x in ['BOOST_CHECK(!call(\"removemodelstorage\"','BOOST_CHECK_EQUAL(code, \"IO_ERROR\")','BOOST_CHECK(!err.empty())','BOOST_CHECK(result[\"configured\"].get_bool())']) and i>testfile.read_text().splitlines().index('BOOST_AUTO_TEST_CASE(cloud_rpc_detach_removal_failure_preserves_origin_and_retry)')}
 actual={int(x.attrib['line']) for x in errors};assert actual==expected and len(errors)==4,{'expected':sorted(expected),'actual':sorted(actual),'errors':[ET.tostring(x).decode() for x in errors]};r['baseline_exact_assertion_lines']=sorted(actual);save()
 def native(phase,expected):
  dest=out/(phase+'-native');dest.mkdir();shutil.chown(dest,user='nobody',group='nogroup')
  run(['runuser','-u','nobody','--','env','BTX_OPENSSL='+os.environ['BTX_OPENSSL'],sys.executable,w/'proposal/native-detach.py','--helper',helper,'--out',dest],phase+'-native',180,build,allowed=(expected,))
  d=json.loads((dest/'native-result.json').read_text());assert d['complete'] and d['clean_starts']==3,d
  assert d['contract_pass']==(expected==0),d
  if expected:assert [k for k,v in d['checks'].items() if not v]==['failed_detach_reports_IO_ERROR'],d
  r[phase+'_native']=d;save()
 native('baseline',1)
 # Revert only the staged regression before applying the exact two-file patch.
 testfile.write_bytes((reference/'src/test/modelnet_cloud_tests.cpp').read_bytes())
 run(['git','apply','--check',w/'proposal/cloud-detach.patch'],'patch-check',30,source)
 run(['git','apply',w/'proposal/cloud-detach.patch'],'patch-apply',30,source)
 shutil.copy2(build/'build.ninja',snapshot);dry=run(['ninja','-f',snapshot,'-n',*targets],'candidate-plan',120,build);assert len(dry.splitlines())<70
 run(['ninja','-j2',*targets],'candidate-build',600,build)
 r['candidate_hash']={n:sha(build/'bin'/n)for n in targets};save()
 run([test,'--run_test=modelnet_cloud_tests','--log_level=test_suite'],'candidate-cloud-suite',180,build)
 native('candidate',0)
 r['same_regression_pair_pass']=True;r['complete']=True;save()
except Exception as e:r['error']=repr(e);print('QUALIFICATION ERROR',repr(e),flush=True)
finally:
 # Only records contains allowlisted text evidence; no fixture credentials or models.
 for f in out.rglob('*'):
  if f.is_symlink():continue
  f.chmod(0o755 if f.is_dir() else 0o644)
 out.chmod(0o755)
 for phase in ('baseline','candidate'):
  d=w/('runtime-'+phase)
  if d.exists():
   for log in d.rglob('*'):
    # Exact text-log allowlist excludes LevelDB *.log, wallets and identities.
    if not log.is_file() or log.is_symlink():continue
    keep=log.name=='test_framework.log' or (log.name=='debug.log' and log.parent.name=='regtest') or log.name in ('stdout','stderr')
    if not keep:continue
    dest=out/('runtime-'+phase)/log.relative_to(d);dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(log,dest);dest.chmod(0o644)
 try:
  if restored:
   # Retain compatible build state even if qualification failed. Not a release package.
   manifest=create(w,w/'retained-checkpoint',{'source':PIN,'cloud_detach_candidate':r.get('candidate_hash')is not None,'complete':r['complete']},reserve=2*1024**3);r['checkpoint_retained']=manifest
 except Exception as e:r['retention_error']=repr(e)
 save()
raise SystemExit(0 if r['complete']and not r.get('error')and not r.get('retention_error')else 1)
