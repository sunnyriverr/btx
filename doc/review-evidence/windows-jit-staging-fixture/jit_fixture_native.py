from pathlib import Path
import subprocess,os,json,hashlib,shutil,time
R=Path('D:/btx-native-035');B=R/'project-build';S=Path(os.environ['GITHUB_WORKSPACE'])/'btx';E=R/'unit-plan-evidence';E.mkdir(parents=True,exist_ok=True)
r={'source':'89f8f94749575fec3891bf7ea1b76f9c20169c6f','tests_run':False,'full_unit_build':False}
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def save():(E/'jit-fixture-result.json').write_text(json.dumps(r,indent=2)+'\n')
def run(n,args,cwd=S,timeout=180,shell=False):
 st=time.monotonic();p=subprocess.run(args,cwd=cwd,capture_output=True,timeout=timeout,shell=shell);(E/(n+'.log')).write_bytes(p.stdout+p.stderr);r.setdefault('commands',[]).append({'name':n,'exit':p.returncode,'seconds':round(time.monotonic()-st,2)});save();print(n,p.returncode,flush=True);return p,(p.stdout+p.stderr).decode(errors='replace')
try:
 assert shutil.disk_usage(R).free>8*1024**3
 assert sha(B/'btx-successor.json')=='eec888e7f7fae24e2e3b6eecde10334072b3e59a7038660fdf1bcd2d9d8d4ae7'
 cp=json.loads((B/'btx-successor.json').read_text());assert cp['source']==r['source'];assert cp['build_result']['status']=='UNIT_BUILD_INCOMPLETE'
 p,h=run('head',['git','rev-parse','HEAD']);assert p.returncode==0 and h.strip()==r['source']
 for n,info in cp['files'].items():assert sha(R/n)==info['sha256'],n
 for n,info in cp['source_files'].items():
  p=S/n;assert sha(p)==info['sha256'],n;os.utime(p,ns=(p.stat().st_atime_ns,info['mtime_ns']))
 r['verified_files']=len(cp['files']);r['verified_objects']=sum(n.endswith('.obj') for n in cp['files'])
 p,t=run('compiler',['clang-cl','--version']);assert p.returncode==0 and '20.1.8' in t
 assert os.environ['VCToolsVersion'].rstrip('\\')=='14.51.36231';assert os.environ['WindowsSDKVersion'].rstrip('\\')=='10.0.26100.0'
 r['toolset']=os.environ['VCToolsVersion'];r['sdk']=os.environ['WindowsSDKVersion']
 entries=json.loads((B/'compile_commands.json').read_text());entry=next(x for x in entries if x['file'].replace('\\','/').endswith('/modelnet_jit_ensure_tests.cpp'));r['exact_generated_command']=entry
 source=S/'src/test/modelnet_jit_ensure_tests.cpp';candidate=Path(__file__).parent/'modelnet_jit_ensure_tests.fixed.cpp';review=json.loads((Path(__file__).parent/'jit-fixture-review.json').read_text());assert sha(source)==review['baseline_source_sha256'];assert sha(candidate)==review['candidate_source_sha256']
 p,t=run('baseline-generated',entry['command'],cwd=entry['directory'],timeout=300,shell=True);r['baseline_exit']=p.returncode;r['baseline_errors']=[x for x in t.splitlines() if 'error:' in x];assert p.returncode!=0 and "no member named 'setenv'" in t and "no member named 'unsetenv'" in t
 shutil.copyfile(candidate,source);r['candidate_source_sha256']=sha(source)
 p,t=run('candidate-generated',entry['command'],cwd=entry['directory'],timeout=300,shell=True);r['candidate_exit']=p.returncode;assert p.returncode==0,t[-3000:]
 obj=Path(entry['output']);r['candidate_object_sha256']=sha(obj)
 p,t=run('candidate-symbols',['dumpbin','/symbols',str(obj)],cwd=B);assert p.returncode==0
 present={n:(n in t) for n in review['portable_cases_preserved']};assert all(present.values()),present;assert review['windows_excluded_case'] not in t;r['retained_case_symbols']=present;r['posix_case_absent_on_windows']=True
 for n,info in cp['files'].items():
  if n.endswith(('.obj','.exe','.lib')) and not n.replace('\\','/').endswith('/modelnet_jit_ensure_tests.cpp.obj'):assert sha(R/n)==info['sha256'],n
 r['unrelated_compiled_files_unchanged']=True;r['posix_fixture_body_unchanged']=True;r['status']='GENERATED_COMMAND_FAIL_BEFORE_PASS_AFTER'
except BaseException as e:r['status']='BLOCKED';r['error']=repr(e);raise
finally:save()
