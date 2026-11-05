"""Resume the exact unfiltered maintained test_btx target; retain normal progress."""
from pathlib import Path
import os,sys,json,hashlib,subprocess,shutil,base64,re
import checkpoint
import integration_support as s
P=Path(__file__).resolve().parent;ROOT=s.ROOT;SOURCE=s.SOURCE;BUILD=s.BUILD;E=s.E
I=json.loads((P/'full-inputs.json').read_text());TARGET=I['target'];s.STATE=E/'full-unit.json';s.R=json.loads(s.STATE.read_text())if s.STATE.exists()else{'target':TARGET,'scope':I['scope'],'commands':[],'process_active':False,'unit_built':False,'unit_invoked':False,'status':'SETUP'};R=s.R;sha=s.sha

def diff(a,b,p=''):
 out={}
 for k in sorted(set(a)|set(b)):
  x,y=a.get(k),b.get(k)
  if isinstance(x,dict)and isinstance(y,dict):out.update(diff(x,y,p+k+'.'))
  elif x!=y:out[p+k]=[x,y]
 return out

def prepare():
 setup=json.loads((E/'result.json').read_text());assert setup['stages']['profile']=='COMPLETE'
 marker=BUILD/'btx-checkpoint.json';assert sha(marker)==I['checkpoint_sha256'];cp=json.loads(marker.read_text());assert cp['profile']['source']==TARGET
 actual=setup['profile'];expected=cp['profile']['actual_current_profile'];d=diff(expected,actual);allowed=json.loads((P/'profile-transition.json').read_text())['allowed_differences'];reverse={k:list(reversed(v))for k,v in allowed.items()};assert d in [{},allowed,reverse],d
 assert subprocess.check_output(['ninja','--version'],text=True).strip()=='1.13.2'
 bundle=E/'full-source.bundle';bundle.write_bytes(base64.b64decode((P/'full-source.bundle.base64').read_text()));assert sha(bundle)==I['bundle_sha256']
 s.need('full-prerequisite-fetch',['git','fetch','--no-tags','--depth=2','https://github.com/sunnyriverr/btx.git',I['published_source']],120)
 s.need('full-bundle-verify',['git','bundle','verify',str(bundle)],60);s.need('full-bundle-fetch',['git','fetch',str(bundle),I['bundle_ref']],60);s.need('full-source-checkout',['git','checkout','--detach',TARGET],60)
 cat=s.catalog(TARGET,'full-before');assert cat==cp['source_catalog'];R['restore']=checkpoint.restore(ROOT,SOURCE,cp['profile'],cat);assert R['restore']['restored']
 R['source_catalog']=cat;R['actual_profile']=actual;R['input_profile']=cp['profile'];R['host_transition']=d;R['original_config']=cp['profile']['configuration'];assert all(sha(BUILD/n)==h for n,h in R['original_config'].items())
 config=(BUILD/'CMakeCache.txt').read_text()
 for flag in ['WITH_MODELNET:BOOL=ON','BUILD_TESTS:BOOL=ON','ENABLE_WALLET:BOOL=ON','WITH_ZMQ:BOOL=ON']:assert flag in config
 commands=json.loads((BUILD/'compile_commands.json').read_text());R['maintained_test_compile_entries']=sum('/test_btx.dir/'in c['output'].replace('\\','/')for c in commands);assert R['maintained_test_compile_entries']==2606
 R['source_changes_from_checkpoint']=[];R['profile']={'source':TARGET,'actual_current_profile':actual,'input_checkpoint_sha256':I['checkpoint_sha256'],'source_bundle_sha256':I['bundle_sha256'],'controls_sha256':sha(P/'full.py'),'scope':I['scope'],'normal_ninja_dependencies':True,'configuration':R['original_config']};R['status']='FULL_READY';s.save()

def build():
 assert R['status']=='FULL_READY';common=['ninja','-C',str(BUILD)]
 s.need('full-unit-plan',common+['-d','explain','-n','test_btx'],120);text=(E/'full-unit-plan.log').read_text(errors='replace');steps=re.findall(r'^\[(\d+)/(\d+)\]',text,re.M);R['planned_steps']=int(steps[-1][1])if steps else 0
 assert 0<R['planned_steps']<=3000,R['planned_steps'];assert 'command line changed for'not in text,'Unexpected command identity invalidation'
 R['initial_resources']=s.resources();assert R['initial_resources']['disk_free']>6*1024**3 and R['initial_resources']['available_ram']>3*1024**3
 R['status']='FULL_UNIT_BUILDING';s.save();code=s.run('candidate-unit-build',common+['--verbose','-j','4','-k','1','test_btx'],1800);R['unit_build_exit']=code
 if code:
  R['status']='FULL_UNIT_BUILD_FAILURE';s.save();raise RuntimeError('Actual maintained target compiler/link blocker; unrun stages explicit')
 exe=BUILD/'bin/test_btx.exe';R['unit_binary_sha256']=sha(exe);R['unit_built']=True;R['build_info']=(BUILD/'src/bitcoin-build-info.h').read_text();assert TARGET in R['build_info']and re.search(r'BUILD_GIT_DIRTY\s+0',R['build_info'])
 s.need('full-unit-imports',['dumpbin','/dependents',str(exe)],60);s.need('full-unit-inventory',[str(exe),'--list_content'],120);R['status']='FULL_UNIT_LINKED';s.save()

def run():
 assert R['status']=='FULL_UNIT_LINKED';exe=BUILD/'bin/test_btx.exe';assert sha(exe)==R['unit_binary_sha256'];data=Path('D:/bu'+os.environ['GITHUB_RUN_ID']);assert not data.exists();data.mkdir();R['unit_data']=str(data);R['unit_launch_attempted']=True;R['status']='FULL_UNIT_RUNNING';s.save()
 try:code=s.run('candidate-unit-run',[str(exe),'--log_level=error','--report_level=detailed','--catch_system_errors=yes','--','-testdatadir='+str(data)],1200)
 finally:R['unit_invoked']=any(x['label']=='candidate-unit-run'for x in R['commands']);s.save()
 R['unit_exit']=code;text=(E/'candidate-unit-run.log').read_text(errors='replace');m=re.search(r'Running (\d+) test cases?',text);R['unit_cases_started']=int(m.group(1))if m else 0
 assert sha(exe)==R['unit_binary_sha256'];R['status']='FULL_UNIT_PASS'if code==0 and R['unit_cases_started']>0 else'FULL_UNIT_RUN_FAILURE';s.quiesce()
 if R['status']!='FULL_UNIT_PASS':raise RuntimeError('Full maintained unit invocation did not pass')

def retain():
 assert not R['process_active']and R.get('cleanup_confirmed',True);assert R.get('source_catalog',{}).get('head')==TARGET;s.quiesce();cat=s.catalog(TARGET,'full-retained');assert cat==R['source_catalog']
 assert all(sha(BUILD/n)==h for n,h in R['original_config'].items()),'Original CMake graph/config changed'
 R['checkpoint_capture']=checkpoint.capture(ROOT,SOURCE,R['profile'],cat,{'status':R['status'],'unit_build_exit':R.get('unit_build_exit'),'unit_exit':R.get('unit_exit'),'unit_built':R['unit_built'],'unit_invoked':R['unit_invoked']});shutil.copyfile(BUILD/'btx-checkpoint.json',E/'full-checkpoint.json');cp=json.loads((BUILD/'btx-checkpoint.json').read_text());R['objects_retained']=sum(k.endswith('.obj')for k in cp['files']);R['checkpoint_key']=hashlib.sha256(json.dumps(R['profile'],sort_keys=True).encode()).hexdigest();s.save()
 with open(os.environ['GITHUB_OUTPUT'],'a')as f:f.write('checkpoint_valid=true\ncheckpoint_key='+R['checkpoint_key']+'\n')

stage=sys.argv[1];failed=False
try:{'prepare':prepare,'build':build,'run':run,'retain':retain}[stage]()
except BaseException as e:
 failed=True;R.setdefault('failures',[]).append({'stage':stage,'error':str(e),'type':type(e).__name__})
 if R['status']in ['FULL_UNIT_BUILDING','FULL_UNIT_RUNNING']:R['status']+='_' + ('BUDGET_STOP'if 'stopped:'in str(e)else'ERROR')
 print(type(e).__name__,str(e),flush=True)
finally:s.save();print(json.dumps({k:R.get(k)for k in ['status','planned_steps','unit_built','unit_invoked','unit_build_exit','unit_exit','failures']},indent=2),flush=True)
raise SystemExit(1 if failed else 0)
