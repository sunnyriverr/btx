"""Maintained cases before/after native socket ownership repair; original graph kept."""
from pathlib import Path
import os,sys,json,hashlib,subprocess,shutil,base64,re,stat
import checkpoint
import integration_support as s
P=Path(__file__).resolve().parent;ROOT=s.ROOT;SOURCE=s.SOURCE;BUILD=s.BUILD;E=s.E
I=json.loads((P/'fixture-inputs.json').read_text());s.STATE=E/'sockets.json'
s.R=json.loads(s.STATE.read_text())if s.STATE.exists()else{'status':'SETUP','commands':[],'process_active':False,'scope':I['scope']};R=s.R;sha=checkpoint.digest

def diff(a,b,prefix=''):
 out={}
 for k in sorted(set(a)|set(b)):
  x,y=a.get(k),b.get(k)
  if isinstance(x,dict)and isinstance(y,dict):out.update(diff(x,y,prefix+k+'.'))
  elif x!=y:out[prefix+k]=[x,y]
 return out

def prepare():
 setup=json.loads((E/'result.json').read_text());assert setup['stages']['profile']=='COMPLETE'
 marker=BUILD/'btx-checkpoint.json';assert sha(marker)==I['checkpoint_sha256'];cp=json.loads(marker.read_text());assert cp['profile']['source']==I['cached_source']
 d=diff(cp['profile']['actual_current_profile'],setup['profile']);allowed=json.loads((P/'profile-transition.json').read_text())['allowed_differences'];assert d in[{},allowed,{k:list(reversed(v))for k,v in allowed.items()}],d
 assert subprocess.check_output(['ninja','--version'],text=True).strip()=='1.13.2'
 bundle=E/'socket-source.bundle';bundle.write_bytes(base64.b64decode((P/'fixture-source.bundle.base64').read_text()));assert sha(bundle)==I['bundle_sha256']
 s.need('public-parent-fetch',['git','fetch','--no-tags','--depth=2','https://github.com/sunnyriverr/btx.git',I['public_parent']],120)
 s.need('bundle-verify',['git','bundle','verify',str(bundle)],60);s.need('bundle-fetch',['git','fetch',str(bundle),I['bundle_ref']],60)
 s.need('cached-checkout',['git','checkout','--detach',I['cached_source']],60)
 cat=s.catalog(I['cached_source'],'cached');assert cat==cp['source_catalog'];R['restore']=checkpoint.restore(ROOT,SOURCE,cp['profile'],cat);assert R['restore']['restored']
 R['actual_profile']=setup['profile'];R['host_transition']=d;R['input_checkpoint_sha256']=I['checkpoint_sha256']
 R['original_config']={n:sha(BUILD/n)for n in['build.ninja','CMakeFiles/rules.ninja','CMakeCache.txt','compile_commands.json']}
 R['original_binary_sha256']=sha(BUILD/'bin/windows_fixture_boundaries.exe');assert R['original_binary_sha256']==I['cached_binary_sha256']
 for flag in['WITH_MODELNET:BOOL=ON','BUILD_TESTS:BOOL=ON','ENABLE_WALLET:BOOL=ON','WITH_ZMQ:BOOL=ON']:assert flag in(BUILD/'CMakeCache.txt').read_text()
 commands=json.loads((BUILD/'compile_commands.json').read_text())
 for row in I['baseline_compile_entries']:
  found=[x for x in commands if x['file'].replace('\\','/').endswith('/src/test/'+row['file'])and'/test_btx.dir/'in x['output'].replace('\\','/')];assert found==[row['command']]
 original=(BUILD/'build.ninja').read_bytes();graph=E/'sockets.ninja';graph.write_bytes(original+b'\n# Same maintained component link closure; original full target preserved.\n'+I['component_link_block'].encode()+b'\n');assert graph.read_bytes().startswith(original)
 R['graph_sha256']=sha(graph);s.need('baseline-checkout',['git','checkout','--detach',I['baseline_test']],60)
 changed=subprocess.check_output(['git','diff','--name-only',I['cached_source'],I['baseline_test']],cwd=SOURCE,text=True).splitlines();assert changed==I['test_delta'];s.catalog(I['baseline_test'],'baseline-before');R['status']='BASELINE_READY';s.save()

def build(which):
 target=I['baseline_test']if which=='baseline'else I['target'];assert R['status']==('BASELINE_READY'if which=='baseline'else'BASELINE_CLASSIFIED')
 if which=='candidate':
  s.need('candidate-checkout',['git','checkout','--detach',target],60);delta=subprocess.check_output(['git','diff','--name-only',I['baseline_test'],target],cwd=SOURCE,text=True).splitlines();assert delta==I['product_delta'];s.catalog(target,'candidate-before')
 common=['ninja','-C',str(BUILD),'-f',str(E/'sockets.ninja')];s.need(which+'-plan',common+['-n','-d','explain','bin/windows_fixture_boundaries.exe'],120)
 plan=(E/(which+'-plan.log')).read_text(errors='replace');steps=re.findall(r'^\[(\d+)/(\d+)\]',plan,re.M);n=int(steps[-1][1])if steps else 0;assert 0<n<=24,n
 assert 'command line changed for'not in plan and 'Re-running CMake'not in plan and 'Re-checking globbed'not in plan
 R[which+'_planned_steps']=n;assert s.resources()['disk_free']>3*1024**3;R['status']=which.upper()+'_BUILDING';s.save()
 code=s.run(which+'-build',common+['--verbose','-j','4','-k','1','bin/windows_fixture_boundaries.exe'],600);R[which+'_build_exit']=code;assert code==0,'Actual compiler/link barrier'
 R[which+'_binary_sha256']=sha(BUILD/'bin/windows_fixture_boundaries.exe');info=(BUILD/'src/bitcoin-build-info.h').read_text();assert target[:7]in info and re.search(r'BUILD_GIT_DIRTY\s+0',info);R[which+'_build_info']=info;R['status']=which.upper()+'_LINKED';s.save()

def clean_owned(data,which):
 R[which+'_processes_before_cleanup']=s.owned_processes();s.quiesce();R[which+'_readonly_cleanup']=[]
 def denied(func,path,exc):
  f=Path(path);assert data in f.parents and not f.is_symlink();assert not f.lstat().st_file_attributes&stat.FILE_ATTRIBUTE_REPARSE_POINT
  os.chmod(f,stat.S_IREAD|stat.S_IWRITE);R[which+'_readonly_cleanup'].append(str(f.relative_to(data)));func(path)
 shutil.rmtree(data,onerror=denied);R[which+'_owned_data_removed']=not data.exists();s.save()

def run(which):
 assert R['status']==which.upper()+'_LINKED';exe=BUILD/'bin/windows_fixture_boundaries.exe';data=Path('D:/cs'+os.environ['GITHUB_RUN_ID']+which[0]);assert not data.exists();data.mkdir();R['unit_data']=str(data);R[which+'_cases']=[];s.save();old={k:os.environ.get(k)for k in['TMP','TEMP']}
 try:
  for n,case in enumerate(I['cases']):
   scratch=data/str(n)/'temp';scratch.mkdir(parents=True);os.environ['TMP']=os.environ['TEMP']=str(scratch)
   label=which+'-case-'+str(n);cmd=[str(exe),'--run_test='+case,'--report_level=detailed','--log_level=test_suite','--','-testdatadir='+str(data/str(n)/'node')]
   code=s.run(label,cmd,180);text=(E/(label+'.log')).read_text(errors='replace');entered=('Entering test case "'+case.split('/')[-1]+'"')in text
   assertions=re.search(r'(\d+) assertions? out of (\d+) passed',text);residual=[{'path':str(f.relative_to(scratch)),'attributes':getattr(f.lstat(),'st_file_attributes',None),'bytes':f.lstat().st_size}for f in scratch.rglob('*')]
   R[which+'_cases'].append({'case':case,'exit':code,'entered':entered,'pass':code==0 and bool(re.search(r'Test case \"'+re.escape(case)+r'\" has passed with:',text)),'assertions':list(map(int,assertions.groups()))if assertions else None,'residual_temp_paths':residual,'socket_entries':[x for x in residual if x['path'].endswith('.sock')],'owned_processes_after_case':s.owned_processes()});s.save()
 finally:
  for k,v in old.items():
   if v is None:os.environ.pop(k,None)
   else:os.environ[k]=v
  clean_owned(data,which)
 assert sha(exe)==R[which+'_binary_sha256'];assert not R[which+'_processes_before_cleanup'];assert all(x['entered']and not x['owned_processes_after_case']for x in R[which+'_cases'])
 if which=='baseline':
  assert all(x['exit']!=0 for x in R[which+'_cases']),'Baseline does not discriminate selected socket paths';R['status']='BASELINE_CLASSIFIED'
 else:
  assert all(x['pass']and not x['socket_entries']for x in R[which+'_cases']),'Relevant candidate control failure';R['status']='PAIRED_PASS'
 s.save()

def retain():
 assert not R['process_active'];assert R.get('candidate_build_exit')==0;s.quiesce();cat=s.catalog(I['target'],'candidate-retained');assert cat==json.loads((E/'candidate-before-candidate-source.json').read_text());assert all(sha(BUILD/n)==h for n,h in R['original_config'].items())
 # Flat profile references its predecessor hash/key without recursive histories.
 profile={'source':I['target'],'actual_current_profile':R['actual_profile'],'input_checkpoint_sha256':I['checkpoint_sha256'],'input_cache_key':I['cache_key'],'baseline_test_source':I['baseline_test'],'controls_sha256':sha(P/'paired.py'),'source_bundle_sha256':I['bundle_sha256'],'configuration':R['original_config'],'scope':I['scope'],'normal_ninja_dependencies':True}
 R['checkpoint_capture']=checkpoint.capture(ROOT,SOURCE,profile,cat,{'status':R['status'],'full_unit':False,'baseline_exit':[x['exit']for x in R.get('baseline_cases',[])],'candidate_exit':[x['exit']for x in R.get('candidate_cases',[])]});shutil.copyfile(BUILD/'btx-checkpoint.json',E/'sockets-checkpoint.json')
 cp=json.loads((BUILD/'btx-checkpoint.json').read_text());R['objects_retained']=sum(x.endswith('.obj')for x in cp['files']);key=hashlib.sha256(json.dumps(profile,sort_keys=True).encode()).hexdigest();R['checkpoint_key']=key;s.save()
 with open(os.environ['GITHUB_OUTPUT'],'a')as f:f.write('checkpoint_valid=true\ncheckpoint_key='+key+'\n')

stage=sys.argv[1];failed=False
try:{'prepare':prepare,'baseline-build':lambda:build('baseline'),'baseline-run':lambda:run('baseline'),'candidate-build':lambda:build('candidate'),'candidate-run':lambda:run('candidate'),'retain':retain}[stage]()
except BaseException as e:failed=True;R.setdefault('failures',[]).append({'stage':stage,'error':str(e),'type':type(e).__name__});print(type(e).__name__,str(e),flush=True)
finally:s.save();print(json.dumps({k:R.get(k)for k in['status','baseline_planned_steps','candidate_planned_steps','baseline_cases','candidate_cases','failures']},indent=2),flush=True)
raise SystemExit(1 if failed else 0)
