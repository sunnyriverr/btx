"""One normal parallel Ninja component build, using maintained objects/link rule.
The original full test_btx graph and target are never filtered or rewritten.
"""
from pathlib import Path
import os,sys,json,hashlib,subprocess,shutil,base64,re,time
import checkpoint
import integration_support as s
P=Path(__file__).resolve().parent;ROOT=s.ROOT;SOURCE=s.SOURCE;BUILD=s.BUILD;E=s.E
I=json.loads((P/'four-inputs.json').read_text());TARGET=I['target'];BASE=I['cached_source'];s.STATE=E/'four.json';s.R=json.loads(s.STATE.read_text())if s.STATE.exists()else{'target':TARGET,'cached_source':BASE,'scope':I['scope'],'commands':[],'process_active':False,'status':'SETUP'};R=s.R;sha=s.sha

def diff(a,b,prefix=''):
 out={}
 for k in sorted(set(a)|set(b)):
  x,y=a.get(k),b.get(k)
  if isinstance(x,dict)and isinstance(y,dict):out.update(diff(x,y,prefix+k+'.'))
  elif x!=y:out[prefix+k]=[x,y]
 return out

def symbols(label):
 lib=BUILD/'lib/bitcoin_modelnet.lib';tool=Path(shutil.which('dumpbin'));t=time.monotonic();z=subprocess.run([str(tool),'/linkermember:1',str(lib)],capture_output=True,timeout=120);assert z.returncode==0
 lines=[x for x in z.stdout.decode(errors='replace').splitlines()if 'GetObject'in x and'S3PieceStore'in x];assert lines
 data={'tool':str(tool),'tool_sha256':sha(tool),'library_sha256':sha(lib),'filtered_symbols':lines,'full_stdout_sha256':hashlib.sha256(z.stdout).hexdigest(),'seconds':time.monotonic()-t};(E/(label+'.json')).write_text(json.dumps(data,indent=2)+'\n');R[label]=data;s.save();return lines

def prepare():
 setup=json.loads((E/'result.json').read_text());assert setup['stages']['profile']=='COMPLETE';marker=BUILD/'btx-checkpoint.json';assert sha(marker)==I['checkpoint_sha256'];cp=json.loads(marker.read_text());assert cp['profile']['source']==BASE
 current=setup['profile'];expected=cp['profile']['actual_current_profile'];d=diff(expected,current);allowed=json.loads((P/'profile-transition.json').read_text())['allowed_differences'];assert not d or d==allowed,d
 assert subprocess.check_output(['ninja','--version'],text=True).strip()=='1.13.2'
 bundle=E/'four-source.bundle';bundle.write_bytes(base64.b64decode((P/'four-source.bundle.base64').read_text()));assert sha(bundle)==I['bundle_sha256']
 s.need('four-prerequisite-fetch',['git','-C',str(SOURCE),'fetch','--no-tags','--depth=2','https://github.com/sunnyriverr/btx.git',I['published_source']],120)
 s.need('four-bundle-verify',['git','bundle','verify',str(bundle)],60);s.need('four-bundle-fetch',['git','fetch',str(bundle),I['bundle_ref']],60);s.need('four-cache-source',['git','checkout','--detach',BASE],60)
 cat=s.catalog(BASE,'four-cached');assert cat==cp['source_catalog'];R['restore']=checkpoint.restore(ROOT,SOURCE,cp['profile'],cat);assert R['restore']['restored'];R['cached_profile']=cp['profile'];R['actual_profile']=current;R['host_transition']=d
 R['original_config']={n:sha(BUILD/n)for n in ['build.ninja','CMakeFiles/rules.ninja','CMakeCache.txt','compile_commands.json']}
 cmds=json.loads((BUILD/'compile_commands.json').read_text());rows={}
 for r in I['baseline']:
  found=[c for c in cmds if c['file'].replace('\\','/').endswith('/src/test/'+r['file'])and'/test_btx.dir/'in c['output'].replace('\\','/')];assert found==[r['command']];rows[r['file']]=found[0]
 R['same_generated_compile_entries']=rows
 for r in I['baseline']:
  log=P/'four-baseline'/r['log'];assert sha(log)==r['log_sha256'];shutil.copyfile(log,E/('baseline-'+r['log']))
 for f in ['WITH_MODELNET:BOOL=ON','BUILD_TESTS:BOOL=ON','ENABLE_WALLET:BOOL=ON','WITH_ZMQ:BOOL=ON']:assert f in(BUILD/'CMakeCache.txt').read_text()
 before=symbols('four-before-library');assert any('?GetObject@S3PieceStore@modelnet@@'in x for x in before) and not any('?GetObjectW@S3PieceStore@modelnet@@'in x for x in before),'Expected qualified canonical library from prior run'
 s.need('four-index-refresh',['git','update-index','--refresh'],30);s.need('four-candidate-checkout',['git','checkout','--detach',TARGET],60)
 cat=s.catalog(TARGET,'four-before');R['source_catalog']=cat;changed=subprocess.check_output(['git','diff','--name-only',BASE,TARGET],cwd=SOURCE,text=True).splitlines();assert changed==I['changed'];R['source_delta']=changed
 original=(BUILD/'build.ninja').read_bytes();text=original.decode().replace('\r\n','\n');a=text.index('build bin\\test_btx.exe:');b=text.index('\n\n',a);block=text[a:b];lines=block.splitlines();rule='CXX_EXECUTABLE_LINKER__test_btx_Release';old=lines[0];_,tail=old.split(' | ',1)
 objects=['src\\test\\CMakeFiles\\test_btx.dir\\main.cpp.obj']+['src\\test\\CMakeFiles\\test_btx.dir\\'+r['file']+'.obj'for r in I['baseline']]
 # Keep production implementation objects that the maintained unit link includes
 # outside src/test (e.g. lightwatch); these are not extra test suites.
 explicit=old.split(': '+rule+' ',1)[1].split(' | ',1)[0].split();objects += [x for x in explicit if x.endswith('\\__\\lightwatch.cpp.obj') or x.endswith('\\wallet\\test\\init_test_fixture.cpp.obj') or x.endswith('\\wallet\\test\\wallet_test_fixture.cpp.obj')]
 assert all(x in explicit for x in objects);lines[0]='build bin\\windows_fixture_controls.exe: '+rule+' '+' '.join(objects)+' | '+tail
 for n in range(1,len(lines)):
  lines[n]=lines[n].replace('bin/test_btx.exe','bin/windows_fixture_controls.exe').replace('bin\\test_btx.exe','bin\\windows_fixture_controls.exe').replace('lib\\test_btx.lib','lib\\windows_fixture_controls.lib').replace('bin\\test_btx.pdb','bin\\windows_fixture_controls.pdb').replace('CMakeFiles\\test_btx.rsp','CMakeFiles\\windows_fixture_controls.rsp')
 graph=E/'four.ninja';graph.write_bytes(original+b'\n# Explicit scoped executable; original full unit target unchanged.\n'+'\n'.join(lines).encode()+b'\n');assert graph.read_bytes().startswith(original)
 R['component_objects']=objects;R['component_link_block']='\n'.join(lines);R['graph_sha256']=sha(graph);R['status']='FOCUSED_READY';s.save()

def build():
 assert R['status']=='FOCUSED_READY';common=['ninja','-C',str(BUILD),'-f',str(E/'four.ninja')]
 s.need('four-plan',common+['-d','explain','-n','bin/windows_fixture_controls.exe'],120);t=(E/'four-plan.log').read_text(errors='replace');steps=re.findall(r'^\[(\d+)/(\d+)\]',t,re.M);R['planned_steps']=int(steps[-1][1])if steps else 0;assert 0<R['planned_steps']<=220,R['planned_steps'];assert 'command line changed for'not in t
 R['initial_resources']=s.resources();assert R['initial_resources']['disk_free']>4*1024**3 and R['initial_resources']['available_ram']>2*1024**3;R['status']='FOCUSED_BUILDING';s.save()
 code=s.run('focused-build',common+['--verbose','-j','4','-k','1','bin/windows_fixture_controls.exe'],1500);R['build_exit']=code
 if code:R['status']='FOCUSED_BUILD_FAILURE';raise RuntimeError('Actual scoped compiler/link barrier; original log retained')
 exe=BUILD/'bin/windows_fixture_controls.exe';R['binary_sha256']=sha(exe);R['build_info']=(BUILD/'src/bitcoin-build-info.h').read_text();assert TARGET[:12]in R['build_info'] and re.search(r'BUILD_GIT_DIRTY\s+0',R['build_info'])
 after=symbols('four-after-library');assert any('?GetObject@S3PieceStore@modelnet@@'in x for x in after) and not any('?GetObjectW@S3PieceStore@modelnet@@'in x for x in after),'Store API not normalized across native library/header'
 s.need('four-component-inventory',[str(exe),'--list_content'],60);R['status']='FOCUSED_LINKED';s.save()

def run():
 assert R['status']=='FOCUSED_LINKED';exe=BUILD/'bin/windows_fixture_controls.exe';data=Path('D:/f4'+os.environ['GITHUB_RUN_ID']);assert not data.exists();data.mkdir();R['unit_data']=str(data);R['cases']=[]
 for n,case in enumerate(I['runtime_cases']):
  code=s.run('four-case-'+str(n),[str(exe),'--run_test='+case,'--report_level=detailed','--log_level=test_suite','--','-testdatadir='+str(data)],150);R['cases'].append({'case':case,'exit':code});s.save()
  if code:R['status']='FOCUSED_CONTROL_FAILURE'
 assert all(x['exit']==0 for x in R['cases']), 'One or more selected maintained controls failed; all results retained'
 assert sha(exe)==R['binary_sha256'];s.quiesce();R['status']='FOCUSED_PASS';s.save()

def retain():
 assert not R['process_active']and R.get('cleanup_confirmed',True);assert R.get('source_catalog',{}).get('head')==TARGET;s.quiesce();cat=s.catalog(TARGET,'four-retained');assert cat==R['source_catalog']
 assert all(sha(BUILD/n)==h for n,h in R['original_config'].items()),'Original CMake graph/config changed'
 R['profile']={'source':TARGET,'actual_current_profile':R['actual_profile'],'input_checkpoint_sha256':I['checkpoint_sha256'],'cached_input_profile':R['cached_profile'],'source_bundle_sha256':I['bundle_sha256'],'controls_sha256':sha(P/'four.py'),'scope':I['scope'],'normal_ninja_dependencies':True,'configuration':R['original_config']};R['checkpoint_capture']=checkpoint.capture(ROOT,SOURCE,R['profile'],cat,{'status':R['status'],'component_build_exit':R.get('build_exit'),'full_test_btx_built':False});shutil.copyfile(BUILD/'btx-checkpoint.json',E/'four-checkpoint.json');cp=json.loads((BUILD/'btx-checkpoint.json').read_text());R['objects_retained']=sum(k.endswith('.obj')for k in cp['files']);key=hashlib.sha256(json.dumps(R['profile'],sort_keys=True).encode()).hexdigest();R['checkpoint_key']=key;s.save()
 with open(os.environ['GITHUB_OUTPUT'],'a')as f:f.write('checkpoint_valid=true\ncheckpoint_key='+key+'\n')

stage=sys.argv[1];failed=False
try:{'prepare':prepare,'build':build,'run':run,'retain':retain}[stage]()
except BaseException as e:failed=True;R.setdefault('failures',[]).append({'stage':stage,'error':str(e),'type':type(e).__name__});print(type(e).__name__,str(e),flush=True)
finally:s.save();print(json.dumps({k:R.get(k)for k in ['status','build_exit','planned_steps','cases','failures']},indent=2),flush=True)
raise SystemExit(1 if failed else 0)
