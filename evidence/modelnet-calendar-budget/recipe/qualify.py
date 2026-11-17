from pathlib import Path
import os,json,hashlib,subprocess,shlex,re,time
w=Path(os.environ['GITHUB_WORKSPACE']);out=w/'records';p=w/'proposal';src=w/'product';build=w/'gui-pilot-runtime/qtbuild';r={'complete':False,'product_fix_files':['src/modelnet/s3_store.cpp'],'new_compiles':3,'full_helper_run':False};deadline=time.monotonic()+600
names=['cloud_12f_calendar_rollback_preserves_exhausted_allowance','cloud_12g_calendar_rollback_preserves_remaining_allowance','cloud_12b_calendar_day_budget_persists']
def sha(f):return hashlib.sha256(f.read_bytes()).hexdigest()
def save():(out/'qualification.json').write_text(json.dumps(r,indent=2)+'\n')
def run(cmd,label,cwd=None,limit=120,allowed=(0,),env=None):
 assert time.monotonic()<deadline
 z=subprocess.run([str(x)for x in cmd],cwd=cwd or w,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=limit,env=env);(out/(label+'.log')).write_bytes(z.stdout);print(label,z.returncode,flush=True);assert z.returncode in allowed,(label,z.returncode);return z.returncode,z.stdout.decode()
def observe(text,patched):
 rows=json.loads(text.splitlines()[-1]);assert len(rows)==4 and sum(s.startswith('clock-event ')for s in text.splitlines())==24
 want=[True,False,False,False,False,True]if patched else[True,False,True,True,False,True]
 counts=[1,1,1,1,1,2]if patched else[1,1,2,3,3,4]
 for row in rows:
  assert [e['allowed']for e in row['events']]==want
  assert [e['origin_gets_after']-e['origin_gets_before']for e in row['events']]==[int(x)for x in want]
  assert [e['health']['budget_used_gets']for e in row['events']]==counts
 return rows
try:
 assert json.loads((out/'staging.json').read_text())['complete'];assert sha(src/'src/modelnet/s3_store.cpp')=='b256fded8c1d823a38eb2b2dfcfa72d1cd4b3507e006bce04dfdecd54ee350f1'
 commands=run(['ninja','-C',build,'-t','commands','btx-modeld'],'commands')[1].splitlines();cc=[shlex.split(l)for l in commands if l.rstrip().endswith('-c '+str(src/'src/modelnet/s3_store.cpp'))];assert len(cc)==1;cc=cc[0];flags=[];i=1
 while i<len(cc):
  x=cc[i]
  if x in ('-MT','-MF','-o','-c'):i+=2;continue
  if x=='-MD':i+=1;continue
  flags.append(x);i+=1
 base=shlex.split(commands[-1]);assert base[:3]==[':','&&','/usr/bin/g++']and base[-2:]==['&&',':'];base=base[2:-2];ignored='-Wl,--unresolved-symbols=ignore-in-shared-libs'
 if ignored in base:base.remove(ignored)
 original='src/modelnet/CMakeFiles/btx-modeld.dir/__/modeld.cpp.o';assert base.count(original)==1
 objs={}
 for n in ['consumer','maintained_wrapper','candidate_s3_store']:
  objs[n]=w/(n+'.o');run([cc[0],*flags,'-o',objs[n],'-c',p/(n+'.cpp')],n+'-compile',build,limit=180)
 r['identities']={'baseline_source_sha256':sha(src/'src/modelnet/s3_store.cpp'),'candidate_source_sha256':sha(p/'candidate_s3_store.cpp'),'consumer_sha256':sha(p/'consumer.cpp'),'maintained_wrapper_sha256':sha(p/'maintained_wrapper.cpp'),'objects':{k:sha(v)for k,v in objs.items()}};save()
 for phase in ['baseline','candidate']:
  r[phase]={}
  for kind in ['consumer','maintained_wrapper']:
   binary=w/(phase+'-'+kind);link=list(base);link[link.index(original)]=str(objs[kind]);link[link.index('-o')+1]=str(binary)
   if phase=='candidate':link.insert(1,str(objs['candidate_s3_store']))
   run(link,phase+'-'+kind+'-link',build,limit=120);deps=run(['ldd',binary],phase+'-'+kind+'-ldd')[1];assert 'not found'not in deps
   if kind=='consumer':
    code,text=run([binary,w/(phase+'-runtime')],phase+'-observation',limit=30);rows=observe(text,phase=='candidate');(out/(phase+'-observations.json')).write_text(json.dumps(rows,indent=2)+'\n');r[phase]['consumer_rows']=len(rows)
   else:
    env=dict(os.environ,CLOUD_BUDGET_CASE_DIR=str(w/(phase+'-maintained-runtime')))
    code,text=run([binary,'--log_level=test_suite','--report_level=detailed'],phase+'-maintained',limit=60,allowed=(0,201)if phase=='baseline'else(0,),env=env)
    assert all('Entering test case "'+n+'"'in text and 'Leaving test case "'+n+'"'in text for n in names)
    if phase=='baseline':
     assert code==201
     assert 'fatal error:' not in text and 'uncaught exception' not in text
     errors=re.findall(r'error: in "modelnet_cloud_tests/([^"\n]+)": ([^\n]+)',text)
     assert len(errors)==32, ('unexpected baseline failure count',len(errors))
     for name in names[:2]:
      intended=[message for case,message in errors if case==name]
      assert len(intended)==16
      assert all(('check allowed == expected has failed' in message or ('check store.FakeForTests()->GetCount() - before ==' in message and 'has failed' in message)) for message in intended)
      block=text.split('Entering test case "'+name+'"',1)[1].split('Leaving test case "'+name+'"',1)[0]
      assert all('quota='+str(quota) in block for quota in range(4))
     assert all(case in names[:2] for case,_ in errors)
    else:assert code==0 and 'error: in 'not in text
    r[phase]['maintained_exit']=code;r[phase]['maintained_cases']=names
   r[phase][kind+'_sha256']=sha(binary);save()
 r['baseline_source_unchanged']=sha(src/'src/modelnet/s3_store.cpp')==r['identities']['baseline_source_sha256'];assert r['baseline_source_unchanged'];r['complete']=True
finally:save()
