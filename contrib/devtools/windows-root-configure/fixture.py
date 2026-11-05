"""One normal parallel Ninja component build, using maintained objects/link rule.
The original full test_btx graph and target are never filtered or rewritten.
"""
from pathlib import Path
import os,sys,json,hashlib,subprocess,shutil,base64,re,time
import checkpoint
import integration_support as s
P=Path(__file__).resolve().parent;ROOT=s.ROOT;SOURCE=s.SOURCE;BUILD=s.BUILD;E=s.E
I=json.loads((P/'fixture-inputs.json').read_text());TARGET=I['target'];BASE=I['cached_source'];s.STATE=E/'sdk.json';s.R=json.loads(s.STATE.read_text())if s.STATE.exists()else{'target':TARGET,'cached_source':BASE,'scope':I['scope'],'commands':[],'process_active':False,'status':'SETUP'};R=s.R;sha=s.sha

def diff(a,b,prefix=''):
 out={}
 for k in sorted(set(a)|set(b)):
  x,y=a.get(k),b.get(k)
  if isinstance(x,dict)and isinstance(y,dict):out.update(diff(x,y,prefix+k+'.'))
  elif x!=y:out[prefix+k]=[x,y]
 return out

def prepare():
 setup=json.loads((E/'result.json').read_text());assert setup['stages']['profile']=='COMPLETE';marker=BUILD/'btx-checkpoint.json';assert sha(marker)==I['checkpoint_sha256'];cp=json.loads(marker.read_text());assert cp['profile']['source']==BASE
 current=setup['profile'];expected=cp['profile']['actual_current_profile'];d=diff(expected,current);allowed=json.loads((P/'profile-transition.json').read_text())['allowed_differences'];reverse={k:list(reversed(v))for k,v in allowed.items()};assert d in [{},allowed,reverse],d
 assert subprocess.check_output(['ninja','--version'],text=True).strip()=='1.13.2'
 bundle=E/'four-source.bundle';bundle.write_bytes(base64.b64decode((P/'fixture-source.bundle.base64').read_text()));assert sha(bundle)==I['bundle_sha256']
 s.need('four-prerequisite-fetch',['git','-C',str(SOURCE),'fetch','--no-tags','--depth=2','https://github.com/sunnyriverr/btx.git',BASE],120)
 s.need('four-bundle-verify',['git','bundle','verify',str(bundle)],60);s.need('four-bundle-fetch',['git','fetch',str(bundle),I['bundle_ref']],60);s.need('four-cache-source',['git','checkout','--detach',BASE],60)
 cat=s.catalog(BASE,'four-cached');assert cat==cp['source_catalog'];R['restore']=checkpoint.restore(ROOT,SOURCE,cp['profile'],cat);assert R['restore']['restored'];R['cached_profile']=cp['profile'];R['actual_profile']=current;R['host_transition']=d
 R['original_config']={n:sha(BUILD/n)for n in ['build.ninja','CMakeFiles/rules.ninja','CMakeCache.txt','compile_commands.json']}
 cmds=json.loads((BUILD/'compile_commands.json').read_text());rows={}
 for r in I['baseline']:
  found=[c for c in cmds if c['file'].replace('\\','/').endswith('/src/test/'+r['file'])and'/test_btx.dir/'in c['output'].replace('\\','/')];assert found==[r['command']];rows[r['file']]=found[0]
 R['same_generated_compile_entries']=rows
 for f in ['WITH_MODELNET:BOOL=ON','BUILD_TESTS:BOOL=ON','ENABLE_WALLET:BOOL=ON','WITH_ZMQ:BOOL=ON']:assert f in(BUILD/'CMakeCache.txt').read_text()
 R['modelnet_library_sha256']=sha(BUILD/'lib/bitcoin_modelnet.lib');assert R['modelnet_library_sha256']=='4c924f0731642e0b8aedece02ba8a3229a59b254c0da20637aaea39db5fb529c'
 s.need('four-index-refresh',['git','update-index','--refresh'],30);s.need('four-candidate-checkout',['git','checkout','--detach',TARGET],60)
 cat=s.catalog(TARGET,'four-before');R['source_catalog']=cat;changed=subprocess.check_output(['git','diff','--name-only',BASE,TARGET],cwd=SOURCE,text=True).splitlines();assert changed==I['changed'];R['source_delta']=changed
 original=(BUILD/'build.ninja').read_bytes();text=original.decode().replace('\r\n','\n');a=text.index('build bin\\test_btx.exe:');b=text.index('\n\n',a);block=text[a:b];lines=block.splitlines();rule='CXX_EXECUTABLE_LINKER__test_btx_Release';old=lines[0];_,tail=old.split(' | ',1)
 objects=['src\\test\\CMakeFiles\\test_btx.dir\\main.cpp.obj']+['src\\test\\CMakeFiles\\test_btx.dir\\'+r['file']+'.obj'for r in I['baseline']]
 # Keep production implementation objects that the maintained unit link includes
 # outside src/test (e.g. lightwatch); these are not extra test suites.
 explicit=old.split(': '+rule+' ',1)[1].split(' | ',1)[0].split();objects += [x for x in explicit if x.endswith('\\__\\lightwatch.cpp.obj') or x.endswith('\\wallet\\test\\init_test_fixture.cpp.obj') or x.endswith('\\wallet\\test\\wallet_test_fixture.cpp.obj')]
 assert len(objects)==8 and len(set(objects))==8;assert all(x in explicit for x in objects);objects.append('src\\test\\CMakeFiles\\test_btx.dir\\util\\sdk_process.cpp.obj');lines[0]='build bin\\windows_fixture_boundaries.exe: '+rule+' '+' '.join(objects)+' | '+tail
 for n in range(1,len(lines)):
  lines[n]=lines[n].replace('bin/test_btx.exe','bin/windows_fixture_boundaries.exe').replace('bin\\test_btx.exe','bin\\windows_fixture_boundaries.exe').replace('lib\\test_btx.lib','lib\\windows_fixture_boundaries.lib').replace('bin\\test_btx.pdb','bin\\windows_fixture_boundaries.pdb').replace('CMakeFiles\\test_btx.rsp','CMakeFiles\\windows_fixture_boundaries.rsp')
 # The original graph is an immutable prefix. Append only the new helper compile
 # stanza (also registered by source CMake) and the explicit component link.
 sample='src\\test\\CMakeFiles\\test_btx.dir\\modelnet_cr12_sdk_tests.cpp.obj'
 start=text.index('build '+sample+':');end=text.index('\n\n',start)
 helper=text[start:end].replace('modelnet_cr12_sdk_tests.cpp','util\\sdk_process.cpp')
 helper=helper.replace('src/test/modelnet_cr12_sdk_tests.cpp','src/test/util/sdk_process.cpp')
 # Source spellings are forward slashes; output spellings use Ninja's native paths.
 helper=helper.replace('src/test/util\\sdk_process.cpp','src/test/util/sdk_process.cpp')
 graph=E/'four.ninja';graph.write_bytes(original+b'\n# Explicit helper/component; original full unit target unchanged.\n'+helper.encode()+b'\n\n'+'\n'.join(lines).encode()+b'\n');assert graph.read_bytes().startswith(original)
 R['helper_compile_block']=helper
 R['component_objects']=objects;R['component_link_block']='\n'.join(lines);R['graph_sha256']=sha(graph);R['status']='FOCUSED_READY';s.save()

def build():
 assert R['status']=='FOCUSED_READY';common=['ninja','-C',str(BUILD),'-f',str(E/'four.ninja')]
 s.need('four-plan',common+['-d','explain','-n','bin/windows_fixture_boundaries.exe'],120);t=(E/'four-plan.log').read_text(errors='replace');steps=re.findall(r'^\[(\d+)/(\d+)\]',t,re.M);R['planned_steps']=int(steps[-1][1])if steps else 0;assert 0<R['planned_steps']<=60,R['planned_steps'];assert 'command line changed for'not in t and 'Re-running CMake'not in t and 'Re-checking globbed directories'not in t
 R['initial_resources']=s.resources();assert R['initial_resources']['disk_free']>4*1024**3 and R['initial_resources']['available_ram']>2*1024**3;R['status']='FOCUSED_BUILDING';s.save()
 code=s.run('focused-build',common+['--verbose','-j','4','-k','1','bin/windows_fixture_boundaries.exe'],900);R['build_exit']=code
 if code:R['status']='FOCUSED_BUILD_FAILURE';raise RuntimeError('Actual scoped compiler/link barrier; original log retained')
 exe=BUILD/'bin/windows_fixture_boundaries.exe';R['binary_sha256']=sha(exe);R['build_info']=(BUILD/'src/bitcoin-build-info.h').read_text();assert TARGET[:7]in R['build_info'] and re.search(r'BUILD_GIT_DIRTY\s+0',R['build_info'])
 assert sha(BUILD/'lib/bitcoin_modelnet.lib')==R['modelnet_library_sha256']
 s.need('four-component-inventory',[str(exe),'--list_content'],60);R['status']='FOCUSED_LINKED';s.save()

def run():
 assert R['status']=='FOCUSED_LINKED';exe=BUILD/'bin/windows_fixture_boundaries.exe';data=Path('D:/fb'+os.environ['GITHUB_RUN_ID']);scratch=data/'temp';assert not data.exists();scratch.mkdir(parents=True);R['unit_data']=str(data);R['cases']=[]
 s.need('sdk-python-version',[sys.executable,'--version'],30)
 node=shutil.which('node')
 R['node_available']=bool(node)
 if node:s.need('sdk-node-version',[node,'--version'],30)
 old={k:os.environ.get(k)for k in ['TMP','TEMP']}
 try:
  os.environ['TMP']=os.environ['TEMP']=str(scratch)
  for n,case in enumerate(I['runtime_suites']):
   before=set(str(x.relative_to(scratch))for x in scratch.rglob('*'))
   code=s.run('four-case-'+str(n),[str(exe),'--run_test='+case,'--report_level=detailed','--log_level=test_suite','--','-testdatadir='+str(data/'node')],180)
   text=(E/('four-case-'+str(n)+'.log')).read_text(errors='replace');started=re.search(r'Running (\d+) test case',text);passed=re.search(r'(\d+) test cases? out of \d+ passed',text);assert started and int(started[1])>0,(case,'no actual cases')
   after=set(str(x.relative_to(scratch))for x in scratch.rglob('*'));R['cases'].append({'case':case,'exit':code,'cases_started':int(started[1]),'new_scratch_paths':sorted(after-before),'reported_pass':bool(passed and int(passed[1])==int(started[1]))});s.save()
   if code or not passed or int(passed[1])!=int(started[1]):R['status']='FOCUSED_CONTROL_FAILURE';raise RuntimeError('Selected maintained control failed: '+case)
   assert after==before,(case,'new scratch paths retained')
 finally:
  for k,v in old.items():
   if v is None:os.environ.pop(k,None)
   else:os.environ[k]=v
 assert sha(exe)==R['binary_sha256'];s.quiesce();R['status']='FOCUSED_PASS';shutil.rmtree(data);R['owned_unit_data_removed']=not data.exists();s.save()

def retain():
 assert not R['process_active']and R.get('cleanup_confirmed',True);assert R.get('source_catalog',{}).get('head')==TARGET;s.quiesce();cat=s.catalog(TARGET,'four-retained');assert cat==R['source_catalog']
 assert all(sha(BUILD/n)==h for n,h in R['original_config'].items()),'Original CMake graph/config changed'
 R['profile']={'source':TARGET,'actual_current_profile':R['actual_profile'],'input_checkpoint_sha256':I['checkpoint_sha256'],'cached_input_profile':R['cached_profile'],'source_bundle_sha256':I['bundle_sha256'],'controls_sha256':sha(P/'fixture.py'),'scope':I['scope'],'normal_ninja_dependencies':True,'configuration':R['original_config']};R['checkpoint_capture']=checkpoint.capture(ROOT,SOURCE,R['profile'],cat,{'status':R['status'],'component_build_exit':R.get('build_exit'),'full_test_btx_built':False});shutil.copyfile(BUILD/'btx-checkpoint.json',E/'four-checkpoint.json');cp=json.loads((BUILD/'btx-checkpoint.json').read_text());R['objects_retained']=sum(k.endswith('.obj')for k in cp['files']);key=hashlib.sha256(json.dumps(R['profile'],sort_keys=True).encode()).hexdigest();R['checkpoint_key']=key;s.save()
 with open(os.environ['GITHUB_OUTPUT'],'a')as f:f.write('checkpoint_valid=true\ncheckpoint_key='+key+'\n')

stage=sys.argv[1];failed=False
try:{'prepare':prepare,'build':build,'run':run,'retain':retain}[stage]()
except BaseException as e:failed=True;R.setdefault('failures',[]).append({'stage':stage,'error':str(e),'type':type(e).__name__});print(type(e).__name__,str(e),flush=True)
finally:s.save();print(json.dumps({k:R.get(k)for k in ['status','build_exit','planned_steps','cases','failures']},indent=2),flush=True)
raise SystemExit(1 if failed else 0)
