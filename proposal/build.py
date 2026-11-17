from pathlib import Path
import os,sys,json,subprocess,tarfile,shutil,time,selectors,signal,hashlib,re
from checkpoint import sha,restore_timestamps,verify_restored,create
PIN='371013d61dc124a363521df5b94e97f64d2464f2';w=Path(os.environ['GITHUB_WORKSPACE']);out=w/'records';out.mkdir(exist_ok=True);r={'source':PIN,'complete':False,'commands':[]};source=w/'product';build=w/'gui-pilot-runtime/qtbuild';restored=False;execution_deadline=time.monotonic()+42*60

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
      if actual>(350 if label=='baseline-build' else 100) and p.poll() is None:
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
 m=json.loads((w/'saved-checkpoint/manifest.json').read_text());arc=w/'saved-checkpoint/build-state.tar.gz';assert sha(arc)==m['archive_sha256']=='1ad855549dd086926439131b777d64aa2d1e00eff0f84688d17492953d049054';assert m['workspace']==str(w)
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
 targets=['btxd','btx-cli','btx-modeld','test_btx'];run(['ninja','build.ninja'],'baseline-graph-regeneration',120,build)
 # Snapshot is for read-only planning only. The actual build retains CMake's
 # normal CONFIGURE_DEPENDS verification and unmodified build.ninja.
 snapshot=build/'profile-plan.ninja';shutil.copy2(build/'build.ninja',snapshot)
 dry=run(['ninja','-f',snapshot,'-n',*targets],'baseline-plan',120,build);r['baseline_actions']=len(dry.splitlines());assert 'Re-running CMake' not in dry;assert r['baseline_actions']<350;r['rebuild_admitted']=True;save()
 run(['ninja','-j2',*targets],'baseline-build',1500,build)
 test_script=source/'test/functional/feature_swarm_profile_overrides.py';unit=source/'src/test/modelnet_infra_tests.cpp';test_script.write_bytes((w/'proposal/feature_swarm_profile_overrides.py').read_bytes())
 baseline_hash={n:sha(build/'bin'/n)for n in targets};r['baseline_hash']=baseline_hash;save()
 for name in ('btxd','btx-modeld'):
  deps=run(['ldd',build/'bin'/name],'baseline-ldd-'+name,30);assert 'not found' not in deps
 run([build/'bin/test_btx','--run_test=modelnet_infra_tests','--log_level=test_suite'],'baseline-infra-suite',120,build)
 # Run same maintained functional entrypoint; expected baseline assertion on helper restart.
 txt=run([sys.executable,test_script,'--configfile='+str(build/'test/config.ini'),'--tmpdir='+str(w/'runtime-baseline'),'--nocleanup'],'baseline-native',240,build,allowed=(1,))
 debug=(w/'runtime-baseline/test_framework.log').read_text();assert 'AssertionError: not(1073741824 == 8388608)' in debug
 baseline_lines=test_script.read_text().splitlines();anchor=next(i+2 for i,l in enumerate(baseline_lines) if l.strip()=='self.restart_managed_helper()')
 assert f'line {anchor}, in run_test' in debug and 'assert_equal(node.getmodelnetworkinfo()["quota_bytes"], 8 * 1024 ** 2)' in debug;r['baseline_expected_restart_failure']=True;save()
 # Restore the functional file so the exact five-file patch applies.
 test_script.write_bytes((reference/'test/functional/feature_swarm_profile_overrides.py').read_bytes())
 run(['git','apply','--check',w/'proposal/restart-profile.patch'],'patch-check',30,source);run(['git','apply',w/'proposal/restart-profile.patch'],'patch-apply',30,source)
 shutil.copy2(build/'build.ninja',snapshot);dry=run(['ninja','-f',snapshot,'-n',*targets],'candidate-plan',120,build);r['candidate_actions']=len(dry.splitlines());assert r['candidate_actions']<100
 run(['ninja','-j2',*targets],'candidate-build',600,build)
 r['candidate_hash']={n:sha(build/'bin'/n)for n in targets};save()
 run([build/'bin/test_btx','--run_test=modelnet_infra_tests','--log_level=test_suite'],'candidate-infra-suite',120,build)
 run([sys.executable,test_script,'--configfile='+str(build/'test/config.ini'),'--tmpdir='+str(w/'runtime-candidate'),'--nocleanup'],'candidate-native',300,build)
 assert 'Tests successful'in (w/'runtime-candidate/test_framework.log').read_text();r['native_pair_pass']=True;r['complete']=True;save()
except Exception as e:r['error']=repr(e);print('QUALIFICATION ERROR',repr(e),flush=True)
finally:
 for phase in ('baseline','candidate'):
  d=w/('runtime-'+phase)
  if d.exists():
   for log in d.rglob('*.log'):
    # Evidence allowlist: never upload generated helper identities or cookie data.
    dest=out/('runtime-'+phase)/log.relative_to(d);dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(log,dest)
 try:
  if restored:
   # Retain compatible build state even if qualification failed. Not a release package.
   manifest=create(w,w/'retained-checkpoint',{'source':PIN,'profile_restart_candidate':r.get('candidate_hash')is not None,'complete':r['complete']},reserve=2*1024**3);r['checkpoint_retained']=manifest
 except Exception as e:r['retention_error']=repr(e)
 save()
raise SystemExit(0 if r['complete']and not r.get('error')and not r.get('retention_error')else 1)
