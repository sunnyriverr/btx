"""Resume the exact unfiltered maintained test_btx target; retain normal progress."""
from pathlib import Path
import os,sys,json,hashlib,subprocess,shutil,base64,re
import checkpoint
import integration_support as s
P=Path(__file__).resolve().parent;ROOT=s.ROOT;SOURCE=s.SOURCE;BUILD=s.BUILD;E=s.E
I=json.loads((P/'cohort-inputs.json').read_text());TARGET=I['target'];s.STATE=E/'cohort.json';s.R=json.loads(s.STATE.read_text())if s.STATE.exists()else{'target':TARGET,'scope':I['scope'],'commands':[],'process_active':False,'unit_built':False,'unit_invoked':False,'status':'SETUP'};R=s.R;sha=s.sha

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
 manifest=E/'full-unit.ninja';shutil.copyfile(BUILD/'build.ninja',manifest);assert sha(manifest)==R['original_config']['build.ninja'];R['manifest_sha256']=sha(manifest)
 R['expected_missing_unit_objects']=sum('/test_btx.dir/'in c['output'].replace('\\','/')and 'project-build\\'+c['output'].replace('\\','/').split('/project-build/',1)[1].replace('/','\\')not in cp['files']for c in commands)
 R['target_rows']=[]
 for name in I['files']:
  found=[c for c in commands if c['file'].replace('\\','/').endswith('/src/test/'+name)and'/test_btx.dir/'in c['output'].replace('\\','/')];assert len(found)==1
  c=found[0];target=c['output'].replace('\\','/').split('/project-build/',1)[1];key='project-build\\'+target.replace('/','\\');R['target_rows'].append({'file':name,'target':target,'command':c,'present_before':key in cp['files']})
 R['source_changes_from_checkpoint']=[];R['profile']={'source':TARGET,'actual_current_profile':actual,'input_checkpoint_sha256':I['checkpoint_sha256'],'source_bundle_sha256':I['bundle_sha256'],'controls_sha256':sha(P/'cohort.py'),'support_sha256':sha(P/'integration_support.py'),'scope':I['scope'],'normal_ninja_dependencies':True,'configuration':R['original_config']};R['status']='FULL_READY';s.save()

def build():
 assert R['status']=='FULL_READY';common=['ninja','-C',str(BUILD),'-f',str(E/'full-unit.ninja')];targets=[x['target']for x in R['target_rows']]
 s.need('cohort-plan',common+['-d','explain','-n',*targets],120);text=(E/'cohort-plan.log').read_text(errors='replace');steps=re.findall(r'^\[(\d+)/(\d+)\]',text,re.M);R['planned_steps']=int(steps[-1][1])if steps else 0
 assert 'Re-running CMake'not in text and 'Re-checking globbed directories'not in text and 'command line changed for'not in text
 assert 0<R['planned_steps']<=60,R['planned_steps'];assert sha(E/'full-unit.ninja')==R['original_config']['build.ninja']
 R['status']='COHORT_BUILDING';s.save();code=s.run('candidate-unit-build',common+['--verbose','-j','4','-k','0',*targets],600);R['compile_exit']=code;text=(E/'candidate-unit-build.log').read_text(errors='replace');failed=re.findall(r'^FAILED: (.+)$',text,re.M);R['failed_target_lines']=failed;R['results']=[]
 for row in R['target_rows']:
  output=BUILD/row['target'];is_failed=any(row['file']+'.obj'in x for x in failed);assert is_failed or output.is_file(),row['file']
  R['results'].append({'file':row['file'],'target':row['target'],'compile_ok':not is_failed,'present_before':row['present_before'],'object_sha256':sha(output)if not is_failed else None})
 assert bool(code)==any(not x['compile_ok']for x in R['results']);R['status']='COHORT_DIAGNOSTIC_COMPLETE';s.save()

def retain():
 assert not R['process_active']and R.get('cleanup_confirmed',True);assert R.get('source_catalog',{}).get('head')==TARGET;s.quiesce();cat=s.catalog(TARGET,'full-retained');assert cat==R['source_catalog']
 assert all(sha(BUILD/n)==h for n,h in R['original_config'].items()),'Original CMake graph/config changed'
 R['checkpoint_capture']=checkpoint.capture(ROOT,SOURCE,R['profile'],cat,{'status':R['status'],'unit_build_exit':R.get('unit_build_exit'),'unit_exit':R.get('unit_exit'),'unit_built':R['unit_built'],'unit_invoked':R['unit_invoked']});shutil.copyfile(BUILD/'btx-checkpoint.json',E/'full-checkpoint.json');cp=json.loads((BUILD/'btx-checkpoint.json').read_text());R['objects_retained']=sum(k.endswith('.obj')for k in cp['files']);R['checkpoint_key']=hashlib.sha256(json.dumps(R['profile'],sort_keys=True).encode()).hexdigest();s.save()
 with open(os.environ['GITHUB_OUTPUT'],'a')as f:f.write('checkpoint_valid=true\ncheckpoint_key='+R['checkpoint_key']+'\n')

stage=sys.argv[1];failed=False
try:{'prepare':prepare,'build':build,'retain':retain}[stage]()
except BaseException as e:
 failed=True;R.setdefault('failures',[]).append({'stage':stage,'error':str(e),'type':type(e).__name__})
 if R['status']in ['FULL_UNIT_BUILDING','FULL_UNIT_RUNNING','COHORT_BUILDING']:R['status']+='_' + ('BUDGET_STOP'if 'stopped:'in str(e)else'ERROR')
 print(type(e).__name__,str(e),flush=True)
finally:s.save();print(json.dumps({k:R.get(k)for k in ['status','planned_steps','unit_built','unit_invoked','unit_build_exit','unit_exit','failures']},indent=2),flush=True)
raise SystemExit(1 if failed else 0)
