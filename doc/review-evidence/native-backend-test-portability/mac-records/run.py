from pathlib import Path
import subprocess,os,json,hashlib,shutil
P=Path(__file__).resolve().parent
result={'scope':'macOS exact extracted guard plus identical new in-tree cases; not full BTX build','commands':[]}
for variant in ['baseline','candidate']:
 source=P/(variant+'.cpp');exe=P/(variant+'-component')
 commands=[('build',['/usr/bin/clang++','-std=c++20','-O0','-I/opt/homebrew/include',str(source),'-o',str(exe)],None)]
 for label,value in [('absent',None),('preexisting','before-test'),('empty','')]:
  env=dict(os.environ)
  if value is None:env.pop('BTX_TEST_BACKEND_SCOPED_ENV',None)
  else:env['BTX_TEST_BACKEND_SCOPED_ENV']=value
  commands.append((label,[str(exe),'--log_level=test_suite'],env))
 for label,command,env in commands:
  p=subprocess.run(command,capture_output=True,env=env,timeout=180);log=P/(variant+'-'+label+'.log');log.write_bytes(p.stdout+p.stderr);result['commands'].append({'variant':variant,'label':label,'command':command,'exit':p.returncode,'log_sha256':hashlib.sha256(log.read_bytes()).hexdigest()});(P/'result.json').write_text(json.dumps(result,indent=2)+'\n');assert p.returncode==0,(variant,label,p.stdout.decode(errors='replace'),p.stderr.decode(errors='replace'))
 result[variant+'_source_sha256']=hashlib.sha256(source.read_bytes()).hexdigest();result[variant+'_exe_sha256']=hashlib.sha256(exe.read_bytes()).hexdigest()
result['free_gib']=shutil.disk_usage(P).free/2**30;result['pass']=True;(P/'result.json').write_text(json.dumps(result,indent=2)+'\n');print('Mac exact-helper baseline/candidate cases pass with absent, existing and POSIX empty initial states')
