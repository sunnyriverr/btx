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
 assert len(M['selectors'])==3==len(set(M['selectors']))and set(M['selectors'])<=registered
 assert h.checkpoint.digest(B/'bin/test_btx.exe')==M['binary_sha256']and not h.processes()
 R['preflight']={'passed':True,'deadline_child_and_grandchild_cleanup':True,'sampled_job_working_set_stop':True,'strict_xml_selection_and_assertion_controls':True,'registered_selectors':3,'registered_total':len(registered),'native_product_cases_run':0};R['status']='PREFLIGHT_PASS';remember()

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

def fixturefix():
 import re,ctypes
 assert R['status']=='PREFLIGHT_PASS';tree=ProcessTree();globals()['tree']=tree
 inputs=json.loads((P/'patch-inputs.json').read_text());file=SOURCE/inputs['file'];assert h.checkpoint.digest(file)==inputs['before_sha256'];source_bytes=file.read_bytes();source_mtime=file.stat().st_mtime_ns
 names=['project-build/src/test/CMakeFiles/test_btx.dir/matmul_v4_rc_tests.cpp.obj','project-build/bin/test_btx.exe','project-build/bin/test_btx.pdb','project-build/lib/test_btx.lib','project-build/lib/test_btx.exp'];backup=ROOT/'rc-fixture-originals';assert not backup.exists();backup.mkdir();saved={}
 for i,n in enumerate(names):
  f=ROOT/n;saved[n]={'exists':f.exists(),'mtime':f.stat().st_mtime_ns if f.exists()else None}
  if f.exists():shutil.copyfile(f,backup/str(i))
 def argv(command):
  argc=ctypes.c_int();parse=ctypes.windll.shell32.CommandLineToArgvW;parse.argtypes=[ctypes.c_wchar_p,ctypes.POINTER(ctypes.c_int)];parse.restype=ctypes.POINTER(ctypes.c_wchar_p);ptr=parse(command,ctypes.byref(argc));assert ptr
  try:return [ptr[i]for i in range(argc.value)]
  finally:ctypes.windll.kernel32.LocalFree(ptr)
 R['fixture_fix']={'compiled_objects':0,'relinks':0,'normal_optimized_link':True,'baseline_reused_run':42735908793,'controls':[]};remember()
 try:
  s.need('fixture-apply-check',['git','apply','--check',str(P/'fixture.patch')],30);s.need('fixture-apply',['git','apply',str(P/'fixture.patch')],30);assert h.checkpoint.digest(file)==inputs['after_sha256']
  s.need('fixture-diff-check',['git','diff','--check'],30);changed=subprocess.check_output(['git','diff','--name-only'],cwd=SOURCE,text=True).splitlines();assert changed==[inputs['file']]
  (E/'fixture.patch').write_bytes((P/'fixture.patch').read_bytes());(E/'patch-inputs.json').write_text(json.dumps(inputs,indent=2)+'\n')
  env=dict(os.environ);index=ROOT/'rc-fixture-index';assert not index.exists();env['GIT_INDEX_FILE']=str(index)
  try:
   subprocess.run(['git','read-tree',h.TARGET],cwd=SOURCE,env=env,check=True);subprocess.run(['git','add','--',inputs['file']],cwd=SOURCE,env=env,check=True);R['fixture_fix']['tested_tree']=subprocess.check_output(['git','write-tree'],cwd=SOURCE,env=env,text=True).strip()
  finally:
   if index.exists():index.unlink()
  commands=json.loads((B/'compile_commands.json').read_text());selected=[x for x in commands if x['file'].replace('\\','/').endswith('/src/test/matmul_v4_rc_tests.cpp')];assert len(selected)==1;compile_argv=argv(selected[0]['command']);assert Path(compile_argv[0]).name.lower()=='clang-cl.exe'and '/O2'in compile_argv and '-c'in compile_argv
  (E/'exact-compile-command.json').write_text(json.dumps(selected[0],indent=2)+'\n');row=execute(tree,'fixture-single-compile',compile_argv,240,memory=4*1024**3,cwd=B);assert row['exit']==0 and not row['budget_stop'];R['fixture_fix']['compiled_objects']=1;R['fixture_fix']['candidate_object_sha256']=h.checkpoint.digest(ROOT/names[0]);remember()
  manifest=(B/'build.ninja').read_text();match=re.search(r'(?m)^build bin/test_btx\.exe:.*?(?=\n\n)',manifest,re.S);assert match;rule=match.group().splitlines()[0].split(': ',1)[1].split()[0];assert rule.startswith('CXX_EXECUTABLE_LINKER__test_btx_')
  def database(expand):
   args=['ninja','-C',str(B),'-t','compdb']+(['-x']if expand else[])+[rule];raw=subprocess.check_output(args,text=True,timeout=45);(E/('normal-'+('expanded'if expand else'saved')+'-link-command.json')).write_text(raw);db=json.loads(raw);assert len(db)==1;return db[0]['command']
  command=database(False);expanded=database(True);assert '/OPT:NOICF'not in command.upper()and '/OPT:ICF'not in command.upper();tokens=list(re.finditer(r'@(?:"[^"]+"|[^\s"]+)',command));assert len(tokens)==1;t=tokens[0];prefix=command[:t.start()];suffix=command[t.end():];assert expanded.startswith(prefix)and expanded.endswith(suffix);response=E/'normal-link.rsp';response.write_text(expanded[len(prefix):len(expanded)-len(suffix)],encoding='utf-8');command=prefix+'@"'+str(response)+'"'+suffix
  link_argv=argv(command.split(' -- ',1)[1].split(' && ',1)[0]);assert Path(link_argv[0]).name.lower()=='lld-link.exe'and '/INCREMENTAL:NO'in link_argv;mapfile=E/'normal.map';link_argv+=['/MANIFEST:EMBED,ID=1','/MAP:'+str(mapfile)];(E/'normal-direct-link-argv.json').write_text(json.dumps(link_argv,indent=2)+'\n')
  row=execute(tree,'fixture-normal-link',link_argv,360,memory=4*1024**3,cwd=B);assert row['exit']==0 and not row['budget_stop'];R['fixture_fix']['relinks']=1;R['fixture_fix']['candidate_binary_sha256']=h.checkpoint.digest(B/'bin/test_btx.exe');R['fixture_fix']['map_sha256']=h.checkpoint.digest(mapfile)
  lines=[l for l in mapfile.read_text(errors='replace').splitlines()if 'OracleGemmS8S8@'in l];(E/'normal-callback-map.txt').write_text('\n'.join(lines)+'\n');addresses={}
  for line in lines:
   parts=line.split()
   if len(parts)>=3:
    kind='alternate'if '?IndependentOracleGemmS8S8@'in parts[1]else'primary'if '?OracleGemmS8S8@'in parts[1]else None
    if kind:assert kind not in addresses;addresses[kind]=parts[2]
  assert len(addresses)==2 and len(set(addresses.values()))==2;R['fixture_fix']['callback_addresses']=addresses;mapfile.unlink();remember()
  data=Path('D:/rf'+os.environ['GITHUB_RUN_ID']);assert not data.exists();data.mkdir();R['unit_data']=str(data);prior=dict(os.environ)
  try:
   for k in list(os.environ):
    if k.startswith('BTX_MATMUL_'):os.environ.pop(k,None)
   os.environ.update(M['environment'])
   for i,selector in enumerate(M['fixture_selectors'],1):
    root=data/str(i);root.mkdir();temp=root/'t';temp.mkdir();os.environ['TMP']=os.environ['TEMP']=str(temp);label='fixture-control-'+str(i);report=E/(label+'.xml');args=[B/'bin/test_btx.exe','--run_test='+selector,'--log_level=test_suite','--report_level=detailed','--report_format=XML','--report_sink='+str(report),'--catch_system_errors=yes','--','-testdatadir='+str(root)]
    row=execute(tree,label,args,60);result=outcome([selector],(E/(label+'.log')).read_text(errors='replace'),report.read_text(errors='replace')if report.exists()else'',row['exit'],row['budget_stop']);result.update(selector=selector,seconds=row['seconds'],xml_sha256=h.checkpoint.digest(report)if report.exists()else None,log_sha256=row['log_sha256']);R['fixture_fix']['controls'].append(result);remember();assert result['state']=='passed',result
  finally:
   os.environ.clear();os.environ.update(prior)
   if data.exists():shutil.rmtree(data)
   R.pop('unit_data',None);R['fixture_fix']['runtime_removed']=not data.exists()
 finally:
  assert not h.processes();file.write_bytes(source_bytes);os.utime(file,ns=(source_mtime,source_mtime))
  for i,n in enumerate(names):
   f=ROOT/n
   if saved[n]['exists']:shutil.copyfile(backup/str(i),f);os.utime(f,ns=(saved[n]['mtime'],saved[n]['mtime']))
   elif f.exists():f.unlink()
  shutil.rmtree(backup);R['fixture_fix']['source_and_outputs_restored']=True;remember()
 h.verify();R['status']='FIXTURE_REPAIR_QUALIFIED';remember();(E/'fixture-fix.json').write_text(json.dumps(R['fixture_fix'],indent=2)+'\n')

try:
 stage=sys.argv[1]
 if stage=='prepare':h.prepare()
 elif stage=='preflight':preflight()
 elif stage=='run':fixturefix()
 elif stage=='verify':verify()
 else:raise ValueError(stage)
except BaseException as e:R.setdefault('failures',[]).append({'stage':sys.argv[1],'error':repr(e)});remember();raise
finally:remember()
