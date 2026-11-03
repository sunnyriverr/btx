#!/usr/bin/env python3
"""Build/run the four exact repository tests through a fixture-only native adapter.
No checkout, Git mutation, node, GPU, network or installation. Prerequisites are
identified existing native archives/headers in inputs.json. One compile process.
"""
from pathlib import Path
import argparse,hashlib,json,os,platform,shlex,shutil,signal,subprocess,time
ROOT=Path(__file__).resolve().parent
p=argparse.ArgumentParser();p.add_argument('variant',choices=['baseline','baseline-fields','candidate']);args=p.parse_args()
manifest=json.loads((ROOT/'inputs.json').read_text());reuse=Path(manifest['reused_build']);src=ROOT/'source/src';out=ROOT/'build'/args.variant;out.mkdir(parents=True,exist_ok=True)
product_source = ROOT/'baseline-compute_qualification.cpp' if args.variant.startswith('baseline') else src/'matmul/compute_qualification.cpp'
LIMIT=250*1024**2;FLOOR=int(1.25*1024**3)
record={'variant':args.variant,'platform':platform.platform(),'machine':platform.machine(),'started':time.time(),'commands':[],'resource':{'minimum_free_bytes':shutil.disk_usage(ROOT).free,'maximum_owned_bytes':0},'inputs':[]}
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def check_resources():
 free=shutil.disk_usage(ROOT).free;owned=sum(p.stat().st_size for p in ROOT.rglob('*') if p.is_file());record['resource']['minimum_free_bytes']=min(record['resource']['minimum_free_bytes'],free);record['resource']['maximum_owned_bytes']=max(record['resource']['maximum_owned_bytes'],owned)
 if free<FLOOR or owned>LIMIT:raise RuntimeError('resource stop: free='+str(free)+' owned='+str(owned))
def command(argv,name,timeout=120,env=None):
 check_resources();entry={'argv':[str(x) for x in argv],'log':str((out/(name+'.log')).relative_to(ROOT)),'start':time.time()};record['commands'].append(entry)
 with (out/(name+'.log')).open('wb') as f:
  proc=subprocess.Popen([str(x) for x in argv],cwd=ROOT,env=env,stdout=f,stderr=subprocess.STDOUT,start_new_session=True)
  try:
   while proc.poll() is None:
    check_resources()
    if time.time()-entry['start']>timeout:raise RuntimeError('timeout: '+name)
    time.sleep(.1)
   entry['returncode']=proc.wait()
  except BaseException:
   os.killpg(proc.pid,signal.SIGTERM)
   try:proc.wait(timeout=5)
   except subprocess.TimeoutExpired:os.killpg(proc.pid,signal.SIGKILL);proc.wait()
   raise
 entry['elapsed_s']=time.time()-entry['start'];entry['log_sha256']=digest(out/(name+'.log'));return entry['returncode']
try:
 for x in manifest['reused_inputs']:
  path=Path(x['path']);assert digest(path)==x['sha256'],path;record['inputs'].append({'path':str(path),'sha256':x['sha256']})
 record['qualification_tu_sha256']=digest(product_source);assert not args.variant.startswith('baseline') or record['qualification_tu_sha256']==manifest['source_tu_sha256'];record['native_test_sha256']=digest(src/'test/compute_profile_tests.cpp');record['component_sha256']=digest(ROOT/'component.cpp');assert record['component_sha256']==manifest['component_sha256'];assert record['native_test_sha256']==manifest['native_test_sha256']
 original=shlex.split(manifest['original_compile_command']['command']);flags=original[1:original.index('-o')]
 oldroot=str(reuse.parent/'source/src');buildroot=str(reuse/'src');flags=[x.replace(oldroot,str(src)) for x in flags]
 for source,name in [(product_source,'qualification'),(ROOT/'component.cpp','tests')]:
  rc=command(['/usr/bin/c++',*flags,'-MMD','-MF',out/(name+'.d'),'-o',out/(name+'.o'),'-c',source],'compile-'+name,180)
  if rc:raise RuntimeError('compile failed: '+name)
 # Full production qualification TU plus real retained native dependencies; no symbol adapters.
 libs=[x['path'] for x in manifest['reused_inputs'] if x['path'].endswith('.a') and 'libomp' not in x['path']]
 link=['/usr/bin/c++','-O2','-arch','arm64','-isysroot','/Library/Developer/CommandLineTools/SDKs/MacOSX.sdk','-Wl,-dead_strip','-Wl,-map,'+str(out/'link.map'),out/'tests.o',out/'qualification.o',*libs,'-framework','Accelerate','/opt/homebrew/opt/libomp/lib/libomp.a','-framework','Foundation','-framework','IOKit','-framework','Metal','-o',out/'registry-tests']
 if command(link,'link',180):raise RuntimeError('link failed')
 record['binary_sha256']=digest(out/'registry-tests')
 names=['toy_qualification_solves_verifies_and_rejects_replay','qualification_rejects_bounds_expiry_and_corrupt_registry','qualification_quarantines_non_object_rows_and_recovers_empty','qualification_quarantine_failure_preserves_source_and_reports_error']
 names.append('qualification_quarantines_invalid_field_types_and_schema_overflow')
 if args.variant == 'baseline-fields': names = names[-1:]
 record['tests']=[]
 for name in names:
  fixture=ROOT/'tmp'/args.variant/name;fixture.mkdir(parents=True,exist_ok=True);env=dict(os.environ,BTX_REGISTRY_COMPONENT_TMP=str(fixture));rc=command([out/'registry-tests','--run_test=compute_profile_tests/'+name,'--log_level=test_suite','--report_level=detailed','--catch_system_errors=no'],name,120,env);record['tests'].append({'name':name,'exit_code':rc})
 record['all_passed']=all(x['exit_code']==0 for x in record['tests'])
 for x in manifest['reused_inputs']:assert digest(Path(x['path']))==x['sha256']
 record['dependency_hashes_unchanged']=True
finally:
 tmp=ROOT/'tmp'/args.variant
 if tmp.exists():shutil.rmtree(tmp)
 record['finished']=time.time();check_resources();(ROOT/(args.variant+'-run.json')).write_text(json.dumps(record,indent=2)+'\n')
print(json.dumps({'variant':args.variant,'tests':record.get('tests'),'resource':record['resource']},indent=2))
