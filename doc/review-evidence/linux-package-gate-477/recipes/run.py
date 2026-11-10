"""Bounded native packaging qualification; only maintained small fixtures compile."""
from pathlib import Path
import os,sys,json,subprocess,time,signal,shutil,hashlib,re
from result_contract import classify
BASE='dac9aee53520bd49ed320ec7a49b9072fc7d88d9'
HEAD='0ef96ff0b7cfa2dfc62e35818a67fd6f6e1dd871'
TEST_FILES=('test/util/package_release_archive_test.py','test/util/verify_release_btxd_test.py')
PRODUCT_FILES=('scripts/release/package_release_archive.py','scripts/release/verify_release_btxd.py','scripts/release/bundle_qt_gui.py')
CASES=[
 {'id':'native-valid-bundle','script':TEST_FILES[0],'class':'PackageReleaseArchiveTest','method':'test_direct_guard_and_qt_keep_shared_and_private_dependencies','failure':None},
 {'id':'refuse-glibc','script':TEST_FILES[0],'class':'PackageReleaseArchiveTest','method':'test_packaging_refuses_any_elf_above_the_glibc_floor','failure':'AssertionError: RuntimeError not raised'},
 {'id':'refuse-glibcxx','script':TEST_FILES[0],'class':'PackageReleaseArchiveTest','method':'test_packaging_refuses_a_host_glibcxx_need_above_the_floor','failure':'AssertionError: RuntimeError not raised'},
 {'id':'refuse-external-plugin','script':TEST_FILES[1],'class':'ArchiveContentGateTest','method':'test_glibc_ceiling_reads_every_elf_not_only_bin_libexec_lib','failure':'AssertionError: VerifyError not raised'},
]
def sha(f):return hashlib.sha256(f.read_bytes()).hexdigest()
def main():
 w=Path(os.environ['GITHUB_WORKSPACE']).resolve();out=w/'package-gate-records';out.mkdir(exist_ok=False);runtime=w/'package-gate-runtime';runtime.mkdir(mode=0o700)
 r={'base':BASE,'head':HEAD,'cases':[],'commands':[],'qualified':False};start=time.monotonic();env={k:v for k,v in os.environ.items() if not k.startswith('LD_') and k not in ('BTX_RELEASE_GLIBC_CEILING','PYTHONPATH')};env['TMPDIR']=str(runtime)
 def save():(out/'result.json').write_text(json.dumps(r,indent=2)+'\n')
 def command(args,label,cwd=None,limit=90):
  print('START',label,flush=True)
  with (out/(label+'.log')).open('wb') as log:
   child=subprocess.Popen(list(map(str,args)),cwd=cwd,env=env,stdout=log,stderr=subprocess.STDOUT,start_new_session=True);began=time.monotonic();stop=None
   while child.poll() is None:
    if time.monotonic()-began>limit or time.monotonic()-start>600:stop='timeout'
    if shutil.disk_usage(w).free<2*1024**3:stop='disk_reserve'
    if stop:
     os.killpg(child.pid,signal.SIGTERM)
     try:child.wait(10)
     except subprocess.TimeoutExpired:os.killpg(child.pid,signal.SIGKILL);child.wait()
     break
    time.sleep(.2)
  row={'label':label,'args':list(map(str,args)),'exit':child.returncode,'stop':stop,'seconds':time.monotonic()-began};r['commands'].append(row);save();print('END',label,child.returncode,flush=True)
  return row,(out/(label+'.log')).read_text(errors='replace')
 def checked(args,label,cwd=None):
  row,text=command(args,label,cwd);assert row['exit']==0 and not row['stop'],label;return text
 try:
  assert sys.platform.startswith('linux') and sys.version_info>=(3,10)
  for tool in ('cc','ldd','patchelf','objdump','readelf'):
   assert shutil.which(tool),tool
   checked([tool,'--version'],'tool-'+tool)
  r['abi_override_absent']='BTX_RELEASE_GLIBC_CEILING' not in env
  r['source_before']={};r['test_hashes']={}
  for name,commit in [('base-source',BASE),('candidate-source',HEAD)]:
   source=w/name;assert checked(['git','rev-parse','HEAD'],name+'-head',source).strip()==commit
   assert not checked(['git','status','--porcelain'],name+'-clean',source).strip()
   r['source_before'][name]={f:sha(source/f) for f in PRODUCT_FILES}
  for f in TEST_FILES:
   shutil.copy2(w/'candidate-source'/f,w/'base-source'/f)
   assert sha(w/'candidate-source'/f)==sha(w/'base-source'/f)
   r['test_hashes'][f]=sha(w/'candidate-source'/f)
  dirty=checked(['git','diff','--name-only'],'baseline-test-overlay',w/'base-source').splitlines();assert set(dirty)==set(TEST_FILES)
  for phase,source_name in [('baseline','base-source'),('candidate','candidate-source')]:
   for case in CASES:
    label=phase+'-'+case['id'];row,text=command(['python3','-I',case['script'],'-v',case['class']+'.'+case['method']],label,w/source_name)
    verdict=classify(case,phase,row['exit'],text,row['stop'])
    gate_count=None
    if phase=='candidate' and case['id']=='native-valid-bundle':
     observed=re.search(r'read the version needs of ([1-9][0-9]*) packaged ELF files; none is above the documented floor',text)
     if not observed:verdict='INCOMPLETE'
     else:gate_count=int(observed.group(1))
    r['cases'].append({'phase':phase,'case':case['id'],'method':case['method'],'exit':row['exit'],'verdict':verdict,'gate_elf_count':gate_count,'log':label+'.log'});save()
    assert verdict in ('PASS','EXPECTED_BASELINE_FAILURE'),label
  r['source_after']={name:{f:sha(w/name/f) for f in PRODUCT_FILES} for name in ('base-source','candidate-source')}
  r['product_unchanged']=r['source_before']==r['source_after'];assert r['product_unchanged']
  for f,h in r['test_hashes'].items():assert sha(w/'candidate-source'/f)==sha(w/'base-source'/f)==h
  assert not checked(['git','status','--porcelain'],'candidate-final-clean',w/'candidate-source').strip()
  r['native_tools_executed']=True
 except Exception as e:r['error']=repr(e)
 finally:
  # Failed fixtures leave only owned temporary data. Do not remove other paths.
  r['leftover_processes']=[]
  for pid in Path('/proc').iterdir():
   if not pid.name.isdigit():continue
   try:
    executable=Path(os.readlink(pid/'exe'))
    if executable.is_relative_to(runtime):r['leftover_processes'].append(int(pid.name))
   except (OSError,PermissionError):pass
  r['cleanup_signals']=[]
  for pid in r['leftover_processes']:
   try:os.kill(pid,signal.SIGTERM);r['cleanup_signals'].append(pid)
   except ProcessLookupError:pass
  if not r['leftover_processes']:shutil.rmtree(runtime)
  r['runtime_removed']=not runtime.exists()
  r['qualified']=len(r['cases'])==8 and not r.get('error') and r.get('product_unchanged') is True and not r['leftover_processes'] and r['runtime_removed'] and r['abi_override_absent']
  r['seconds']=time.monotonic()-start;save()
 return 0 if r['qualified'] else 1
if __name__=='__main__':sys.exit(main())
