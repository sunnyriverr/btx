"""Execute the scoped stock-release unit campaign without rebuilding or mutating cache."""
from pathlib import Path
import json,os,sys,subprocess,time,shutil,stat,hashlib
import restore_support as h
from batch_results import classify
from job_tree import ProcessTree
s=h.s;R=h.R;E=h.E;B=h.B;ROOT=h.ROOT;SOURCE=h.SOURCE;P=Path(__file__).resolve().parent;M=json.loads((P/'plan.json').read_text())

def outcome(expected,log,xml,code,reason=None):
 r=classify(expected,log,xml,code,reason)
 if r['state']=='passed'and not all(int(r['cases'][k].get('assertions_passed',0))>0 for k in expected):r['state']='empty_body_not_qualified'
 return r

def remember():
 s.save();(E/'consolidated-results.json').write_text(json.dumps({k:R.get(k)for k in ['status','source','runtime_binary_sha256','preflight','batch_results','not_attempted','campaign_stop','test_wall_seconds','runtime_data_removed','cache_unchanged','cached_objects_unchanged','cached_files_unchanged','failures']},indent=2)+'\n')

def quiet(tree,limit=10):
 until=time.monotonic()+limit
 while tree.active()!=1 and time.monotonic()<until:time.sleep(.1)
 return tree.active()==1

def execute(tree,label,args,seconds,memory=1024**3,cwd=None):
 log=E/(label+'.log');begin=time.monotonic();peak=0;peak_processes=0;reason=None;samples=[]
 with log.open('wb')as f:
  proc=subprocess.Popen([str(a)for a in args],cwd=cwd or SOURCE,stdin=subprocess.DEVNULL,stdout=f,stderr=subprocess.STDOUT);R['active_command']=label;R['process_active']=True;remember();last=-1
  try:
   while proc.poll()is None:
    total,pids=tree.working_set();peak=max(peak,total);peak_processes=max(peak_processes,len(pids));elapsed=time.monotonic()-begin;resources=s.resources()
    if elapsed>seconds:reason='TIME_BUDGET'
    elif total>memory:reason='MEMORY_BUDGET'
    elif resources['disk_free']<1.25*1024**3 or resources['available_ram']<1024**3:reason='RESOURCE_BUDGET'
    if int(elapsed)//15!=last:
     last=int(elapsed)//15;samples.append({'seconds':round(elapsed,2),'working_set':total,'processes':pids,**resources});print(label,round(elapsed,1),total,flush=True)
    if reason:
     z=subprocess.run(['taskkill','/PID',str(proc.pid),'/T','/F'],capture_output=True);(E/(label+'-cleanup.log')).write_bytes(z.stdout+z.stderr);proc.wait(timeout=20);break
    time.sleep(.1)
  finally:
   if proc.poll()is None:subprocess.run(['taskkill','/PID',str(proc.pid),'/T','/F'],capture_output=True);proc.wait(timeout=20)
   R['process_active']=False;R['active_command']=None
 row={'label':label,'argv':[str(a)for a in args],'exit':proc.returncode,'seconds':round(time.monotonic()-begin,3),'budget_stop':reason,'peak_sampled_job_working_set':peak,'peak_sampled_job_processes':peak_processes,'samples':samples,'log_sha256':h.checkpoint.digest(log),'clean_tree':quiet(tree)};R['commands'].append(row);remember();assert row['clean_tree'],'Owned descendants remain after '+label
 return row

def preflight():
 assert R['status']=='RESTORED_VERIFIED'and h.checkpoint.digest(B/'bin/test_btx.exe')==M['binary_sha256'];assert not h.processes()
 tree=ProcessTree();globals()['tree']=tree
 row=execute(tree,'preflight-deadline',[sys.executable,'-c','import subprocess,sys,time;subprocess.Popen([sys.executable,"-c","import time;time.sleep(30)"]);time.sleep(30)'],3)
 assert row['budget_stop']=='TIME_BUDGET'and row['clean_tree'];assert row['peak_sampled_job_processes']>=3
 row=execute(tree,'preflight-memory',[sys.executable,'-c','import time;data=bytearray(16*1024*1024);time.sleep(30)'],5,memory=1)
 assert row['budget_stop']=='MEMORY_BUDGET'and row['peak_sampled_job_working_set']>0 and row['clean_tree']
 xml='<TestResult><TestSuite name="root"><TestSuite name="x"><TestCase name="a" result="passed" assertions_passed="1"/></TestSuite></TestSuite></TestResult>'
 assert outcome(['x/a'],'Running 1 test case...',xml,0)['state']=='passed'
 assert outcome(['x/b'],'Running 1 test case...',xml,0)['state']=='selection_or_report_incomplete'
 assert outcome(['x/a'],'Running 2 test cases...',xml,0)['state']=='selection_or_report_incomplete'
 assert outcome(['x/a'],'Running 1 test case...',xml.replace('assertions_passed="1"','assertions_passed="0"'),0)['state']=='empty_body_not_qualified'
 assert outcome(['x/a'],'Running 1 test case...',xml,0,'TIME_BUDGET')['state']=='timeout'
 assert outcome(['x/a'],'Running 1 test case...',xml[:-5],0)['state']=='selection_or_report_incomplete'
 row=execute(tree,'fresh-unit-inventory',[B/'bin/test_btx.exe','--list_content'],45);assert row['exit']==0 and not row['budget_stop'];lines=(E/'fresh-unit-inventory.log').read_text().splitlines();stack=[];registered=set()
 for i,line in enumerate(lines):
  if not line.strip():continue
  indent=len(line)-len(line.lstrip());name=line.strip().rstrip('*')
  while stack and stack[-1][0]>=indent:stack.pop()
  following=next((q for q in lines[i+1:]if q.strip()),'');nxt=len(following)-len(following.lstrip())if following else -1
  if nxt>indent:stack.append((indent,name))
  else:registered.add('/'.join([v for _,v in stack]+[name]))
 assert len(M['selectors'])==1==len(set(M['selectors']))and set(M['selectors'])<=registered
 assert h.checkpoint.digest(B/'bin/test_btx.exe')==M['binary_sha256']and not h.processes()
 R['preflight']={'passed':True,'deadline_child_and_grandchild_cleanup':True,'sampled_job_working_set_stop':True,'strict_xml_selection_and_assertion_controls':True,'registered_selectors':1,'registered_total':len(registered),'native_product_cases_run':0};R['status']='PREFLIGHT_PASS';remember()

def run():
 assert R['status']=='PREFLIGHT_PASS'and R['preflight']['passed'];assert h.checkpoint.digest(B/'bin/test_btx.exe')==M['binary_sha256'];tree=ProcessTree();globals()['tree']=tree
 data=Path('D:/dc'+os.environ['GITHUB_RUN_ID']);assert not data.exists()and not Path('S:/').exists();data.mkdir();R['unit_data']=str(data);R['batch_results']=[];R['not_attempted']=[];R['runtime_binary_sha256']=M['binary_sha256'];R['status']='CONSOLIDATED_RUNNING';prior=dict(os.environ);mapped=False;start=time.monotonic();index=0
 try:
  s.need('map-short-data',['subst','S:',str(data)],15);mapped=True
  for key in list(os.environ):
   if key.startswith('BTX_MATMUL_')or key in ['BTX_RUN_NATIVE_SAFE_V13_SHARD','BTX_EXTENDED_CHAINSTATE_TESTS']:os.environ.pop(key,None)
  os.environ.update(M['environment']);os.environ['PATH']='C:/Program Files/Git/bin'+os.pathsep+os.environ['PATH'];os.environ['CXX']='clang++';R['unit_environment']={k:v for k,v in os.environ.items()if k.startswith('BTX_MATMUL_')};remember()
  for group in M['groups']:
   group_start=time.monotonic();block=False
   for selector in group['selectors']:
    cap=min(M['per_case_hard_ceiling_seconds'],group['group_limit_seconds']-(time.monotonic()-group_start),M['whole_campaign_seconds']-(time.monotonic()-start))
    if cap<2 or block:
     R['not_attempted'].append({'selector':selector,'group':group['id'],'reason':'prior_case_same_fixture_failed'if block else'bounded_group_or_campaign_limit'});remember();continue
    index+=1;short=Path('S:/'+format(index,'x'));short.mkdir();(short/'t').mkdir();os.environ['TMP']=os.environ['TEMP']=str(short/'t');label='case-'+str(index).zfill(2);report=E/(label+'.xml');args=[B/'bin/test_btx.exe','--run_test='+selector,'--log_level=test_suite','--report_level=detailed','--report_format=XML','--report_sink='+str(report),'--catch_system_errors=yes','--','-testdatadir='+str(short)]
    row=execute(tree,label,args,cap);r=outcome([selector],(E/(label+'.log')).read_text(errors='replace'),report.read_text(errors='replace')if report.exists()else'',row['exit'],row['budget_stop']);r.update(selector=selector,group=group['id'],seconds=row['seconds'],log_sha256=row['log_sha256'],xml_sha256=h.checkpoint.digest(report)if report.exists()else None,peak_sampled_job_working_set=row['peak_sampled_job_working_set']);R['batch_results'].append(r);remember();print('RESULT',selector,r['state'],row['seconds'],flush=True)
    assert h.checkpoint.digest(B/'bin/test_btx.exe')==M['binary_sha256']
    if r['state']in ['selection_or_report_incomplete','resource_stop','incomplete']:raise RuntimeError('Runner/resource boundary: '+r['state'])
    if group['id']=='wallet-cheap100'and r['state']!='passed':block=True
  R['campaign_stop']='BOUNDED_MANIFEST_COMPLETED';R['status']='CONSOLIDATED_RESULTS_RECORDED'
 finally:
  R['test_wall_seconds']=round(time.monotonic()-start,3)
  os.environ.clear();os.environ.update(prior)
  if mapped:
   z=subprocess.run(['subst','S:','/D'],capture_output=True,timeout=15);assert z.returncode==0 and not Path('S:/').exists();R['short_drive_removed']=True
  remember()

def verify():
 survivors=h.processes();R['survivors_before_cleanup']=survivors;s.quiesce()
 if R.get('unit_data'):
  data=Path(R['unit_data']);assert data==Path('D:/dc'+os.environ['GITHUB_RUN_ID'])
  def readonly(fn,name,exc):
   p=Path(name);assert p.resolve().is_relative_to(data.resolve())
   if not isinstance(exc[1],PermissionError)or p.stat().st_mode&stat.S_IWRITE:raise exc[1]
   os.chmod(p,stat.S_IREAD|stat.S_IWRITE);fn(name)
  if data.exists():shutil.rmtree(data,onerror=readonly)
  R['runtime_data_removed']=not data.exists()
 h.verify();R['whole_cache_unchanged']=True;remember();assert not survivors

def pqcampaign():
 import re,ctypes
 from case_oracle import baseline_failure
 assert R['status']=='PREFLIGHT_PASS';tree=ProcessTree();globals()['tree']=tree;start=time.monotonic();meta=json.loads((P/'inputs478.json').read_text())
 sources={n:(SOURCE/n).read_bytes()for n in meta['files']};mtimes={n:(SOURCE/n).stat().st_mtime_ns for n in sources}
 names=['project-build/src/test/CMakeFiles/test_btx.dir/matmul_trusted_mirror_tests.cpp.obj','project-build/src/CMakeFiles/bitcoin_node.dir/node/matmul_trusted_attestations.cpp.obj','project-build/lib/bitcoin_node.lib','project-build/bin/test_btx.exe','project-build/bin/test_btx.pdb','project-build/lib/test_btx.lib','project-build/lib/test_btx.exp'];backup=ROOT/'pq478-originals';assert not backup.exists();backup.mkdir();saved={}
 for i,n in enumerate(names):
  f=ROOT/n;saved[n]={'exists':f.exists(),'mtime':f.stat().st_mtime_ns if f.exists()else None}
  if f.exists():shutil.copyfile(f,backup/str(i))
 def cap(limit):
  remaining=600-(time.monotonic()-start);assert remaining>5,'Whole campaign budget';return min(limit,remaining)
 def argv(command):
  argc=ctypes.c_int();fn=ctypes.windll.shell32.CommandLineToArgvW;fn.argtypes=[ctypes.c_wchar_p,ctypes.POINTER(ctypes.c_int)];fn.restype=ctypes.POINTER(ctypes.c_wchar_p);ptr=fn(command,ctypes.byref(argc));assert ptr
  try:return [ptr[i]for i in range(argc.value)]
  finally:ctypes.windll.kernel32.LocalFree(ptr)
 def compose():
  env=dict(os.environ);index=ROOT/'pq478-index';assert not index.exists();env['GIT_INDEX_FILE']=str(index)
  try:
   subprocess.run(['git','read-tree',h.TARGET],cwd=SOURCE,env=env,check=True);subprocess.run(['git','add','--',*sources],cwd=SOURCE,env=env,check=True);return subprocess.check_output(['git','write-tree'],cwd=SOURCE,env=env,text=True).strip()
  finally:
   if index.exists():index.unlink()
 commands=json.loads((B/'compile_commands.json').read_text())
 def compile_one(name,label):
  rows=[x for x in commands if x['file'].replace('\\','/').endswith('/'+name)];assert len(rows)==1;args=argv(rows[0]['command']);assert Path(args[0]).name.lower()=='clang-cl.exe'and '/O2'in args
  (E/(label+'-command.json')).write_text(json.dumps(rows[0],indent=2)+'\n');row=execute(tree,label,args,cap(180),memory=4*1024**3,cwd=B);assert row['exit']==0 and not row['budget_stop']
 def link_or_archive(target,label,kind):
  text=(B/'build.ninja').read_text();match=re.search(r'(?m)^build '+re.escape(target)+r':.*?(?=\n\n)',text,re.S);assert match;rule=match.group().splitlines()[0].split(': ',1)[1].split()[0]
  assert rule.startswith('CXX_STATIC_LIBRARY_LINKER__bitcoin_node_')if kind=='archive'else rule.startswith('CXX_EXECUTABLE_LINKER__test_btx_')
  def db(expand):
   raw=subprocess.check_output(['ninja','-C',str(B),'-t','compdb']+(['-x']if expand else[])+[rule],text=True,timeout=45);(E/(label+('-expanded'if expand else'-saved')+'.json')).write_text(raw);rows=json.loads(raw);assert len(rows)==1;return rows[0]['command']
  command=db(False);expanded=db(True);assert '/OPT:NOICF'not in command.upper();tokens=list(re.finditer(r'@(?:"[^"]+"|[^\s"]+)',command));assert len(tokens)==1;t=tokens[0];prefix=command[:t.start()];suffix=command[t.end():];assert expanded.startswith(prefix)and expanded.endswith(suffix);rsp=E/(label+'.rsp');rsp.write_text(expanded[len(prefix):len(expanded)-len(suffix)],encoding='utf-8');command=prefix+'@"'+str(rsp)+'"'+suffix
  if kind=='link':args=argv(command.split(' -- ',1)[1].split(' && ',1)[0]);assert Path(args[0]).name.lower()=='lld-link.exe';args.append('/MANIFEST:EMBED,ID=1')
  else:
   tool=re.search(r'(?i)("[^"\n]*(?:llvm-lib|lib)\.exe"|[^\s"]*(?:llvm-lib|lib)\.exe)\s+.*?(?=\s+&&|$)',command);assert tool,command;args=argv(tool.group());assert Path(args[0]).name.lower()in ['llvm-lib.exe','lib.exe'];assert any(x.lower().replace('\\','/')=='/out:lib/bitcoin_node.lib'for x in args)
  (E/(label+'-argv.json')).write_text(json.dumps(args,indent=2)+'\n');row=execute(tree,label,args,cap(120),memory=4*1024**3,cwd=B);assert row['exit']==0 and not row['budget_stop']
 R['pq478']={'phases':{},'same_test_source_sha256':meta['files']['src/test/matmul_trusted_mirror_tests.cpp']['candidate_sha256']};remember();data=Path('D:/pq'+os.environ['GITHUB_RUN_ID']);assert not data.exists();data.mkdir();R['unit_data']=str(data);prior=dict(os.environ)
 try:
  for n in sources:assert hashlib.sha256(sources[n]).hexdigest()==meta['files'][n]['base_sha256']
  test='src/test/matmul_trusted_mirror_tests.cpp';prod='src/node/matmul_trusted_attestations.cpp';newtest=(P/'test478.cpp').read_bytes();assert hashlib.sha256(newtest).hexdigest()==meta['files'][test]['candidate_sha256'];(SOURCE/test).write_bytes(newtest)
  compile_one(test,'baseline-test-compile');testhash=h.checkpoint.digest(ROOT/names[0]);assert testhash==meta['reused_test_object_sha256'];link_or_archive('bin/test_btx.exe','baseline-link','link')
  for k in list(os.environ):
   if k.startswith('BTX_MATMUL_'):os.environ.pop(k,None)
  os.environ.update(M['environment'])
  for phase in ['baseline','candidate']:
   if phase=='candidate':
    newprod=(P/'production478.cpp').read_bytes();assert hashlib.sha256(newprod).hexdigest()==meta['files'][prod]['candidate_sha256'];(SOURCE/prod).write_bytes(newprod);compile_one(prod,'candidate-node-compile');link_or_archive('lib/bitcoin_node.lib','candidate-node-archive','archive');assert h.checkpoint.digest(ROOT/names[0])==testhash;link_or_archive('bin/test_btx.exe','candidate-link','link')
   state={'tree':compose(),'binary_sha256':h.checkpoint.digest(B/'bin/test_btx.exe'),'test_object_sha256':testhash,'results':[]};R['pq478']['phases'][phase]=state;remember()
   if phase=='candidate':assert state['tree']==meta['candidate_tree']
   else:
    assert state['tree']==meta['reused_baseline_tree'];reuse=json.loads((P/'reuse478.json').read_text());state['results']=reuse['baseline']['results'];state['reused_from_run']=reuse['prior_run'];remember()
   for i,selector in enumerate(M['pq_selectors'],1):
    if phase=='baseline'and i<3:continue
    root=data/(phase+str(i));root.mkdir();temp=root/'t';temp.mkdir();os.environ['TMP']=os.environ['TEMP']=str(temp);label=phase+'-case-'+str(i);report=E/(label+'.xml');args=[B/'bin/test_btx.exe','--run_test='+selector,'--log_level=all','--report_level=detailed','--report_format=XML','--report_sink='+str(report),'--catch_system_errors=yes','--','-testdatadir='+str(root)];row=execute(tree,label,args,cap(45));log=(E/(label+'.log')).read_text(errors='replace');xml=report.read_text(errors='replace')if report.exists()else''
    if phase=='baseline'and i>1:result=baseline_failure(selector,log,xml,row['exit'],row['budget_stop'],meta['deadline_labels'][selector],meta['exception_checkpoints'][selector])
    else:result=outcome([selector],log,xml,row['exit'],row['budget_stop'])
    result.update(selector=selector,seconds=row['seconds'],exit=row['exit'],log_sha256=row['log_sha256'],xml_sha256=h.checkpoint.digest(report)if report.exists()else None);state['results'].append(result);remember();assert result['state']in (['expected_deadline_reproduced','expected_recursive_mutex_failure']if phase=='baseline'and i>1 else['passed']),result
  R['status']='PQ478_SCOPED_PASS'
 finally:
  os.environ.clear();os.environ.update(prior);assert not h.processes()
  if data.exists():shutil.rmtree(data)
  R.pop('unit_data',None);R['pq478']['runtime_removed']=not data.exists()
  for n,b in sources.items():(SOURCE/n).write_bytes(b);os.utime(SOURCE/n,ns=(mtimes[n],mtimes[n]))
  for i,n in enumerate(names):
   f=ROOT/n
   if saved[n]['exists']:shutil.copyfile(backup/str(i),f);os.utime(f,ns=(saved[n]['mtime'],saved[n]['mtime']))
   elif f.exists():f.unlink()
  shutil.rmtree(backup);R['pq478']['source_outputs_restored']=True;remember()
 h.verify();(E/'pq478.json').write_text(json.dumps(R['pq478'],indent=2)+'\n');remember()

try:
 stage=sys.argv[1]
 if stage=='prepare':h.prepare()
 elif stage=='preflight':preflight()
 elif stage=='run':pqcampaign()
 elif stage=='verify':verify()
 else:raise ValueError(stage)
except BaseException as e:R.setdefault('failures',[]).append({'stage':sys.argv[1],'error':repr(e)});remember();raise
finally:remember()
