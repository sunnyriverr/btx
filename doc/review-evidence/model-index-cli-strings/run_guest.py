from pathlib import Path
import subprocess,json,shlex,hashlib,os,time,signal,shutil
R=Path('/tmp/btx-session2-index-cli');T=R/'repair';B=Path('/tmp/btx-session2-helper-restart-current/build');P=json.loads((R/'native-preflight.json').read_text());old=json.loads((R/'build-result.json').read_text());result={'commands':[],'units':{},'workflows':{},'baseline_CLI_sha256':old['cli_sha256'],'baseline_client_object':old['objects'][str(R/'client.o')],'helper_sha256':old['helper_sha256']}
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(): (T/'result.json').write_text(json.dumps(result,indent=2)+'\n')
def run(args,label,timeout=120):
 print('START',label,flush=True);start=time.monotonic();stop=None
 with (T/(label+'.log')).open('wb') as f:
  proc=subprocess.Popen(args,cwd=B,stdout=f,stderr=subprocess.STDOUT,start_new_session=True)
  while proc.poll() is None:
   if time.monotonic()-start>timeout:stop='phase deadline'
   elif shutil.disk_usage('/tmp').free<32*1024**2:stop='guest reserve below32MiB'
   if stop:os.killpg(proc.pid,signal.SIGTERM);proc.wait(timeout=15);break
   time.sleep(.2)
 row={'label':label,'command':args,'exit':proc.returncode,'stop':stop,'seconds':round(time.monotonic()-start,2),'guest_free':shutil.disk_usage('/tmp').free};result['commands'].append(row);save();print('END',label,proc.returncode,flush=True);assert not stop;return proc.returncode

def compile(source,obj,label):
 entry=P['compile']['/rpc/client.cpp'];args=shlex.split(entry['command']);args=[str(source) if a==entry['file'] else a for a in args];args[args.index('-o')+1]=str(obj);assert run(args,label)==0
assert sha(R/'btx-cli')==old['cli_sha256'];assert sha(R/'client.o')==result['baseline_client_object'];assert {k:sha(k) for k in old['archive_hashes']}==old['archive_hashes']
result['harness_sha256']=sha(T/'paired_workflow.py');result['component_cpp_sha256']=sha(T/'component.cpp');result['candidate_cpp_sha256']=sha(T/'client.cpp');save()
compile(T/'component.cpp',T/'component.o','compile-regression')
compile(T/'client.cpp',T/'client.o','compile-candidate-converter')
# Both identical final unit bodies use unchanged Boost and UniValue.
for candidate in [False,True]:
 label='unit-candidate' if candidate else 'unit-baseline';obj=T/'client.o' if candidate else R/'client.o';exe=T/'unit'
 args=['/usr/bin/c++','-O1','-fPIE','-pie',str(T/'component.o'),str(obj),str(B/'src/univalue/libunivalue.a'),'-lboost_unit_test_framework','-s','-o',str(exe)]
 assert run(args,label+'-link')==0;identity=sha(exe);code=run([str(exe),'--report_level=detailed','--log_level=test_suite'],label)
 result['units'][label]={'exit':code,'binary_sha256':identity,'binary_after_sha256':sha(exe)};save();assert code==(0 if candidate else 201);exe.unlink()
# An also_string-only partial repair must not turn this string contract green.
original=(B.parent/'source/src/rpc/client.cpp').read_text()
for method in ['addmodelindex','removemodelindex']:
 a='    { "'+method+'", 0, "endpoint" },';b='    { "'+method+'", 0, "endpoint", /*also_string=*/true },';assert original.count(a)==1;original=original.replace(a,b)
(T/'client.weak.cpp').write_text(original);compile(T/'client.weak.cpp',T/'weak.o','compile-partial-control')
exe=T/'unit';assert run(['/usr/bin/c++','-O1','-fPIE','-pie',str(T/'component.o'),str(T/'weak.o'),str(B/'src/univalue/libunivalue.a'),'-lboost_unit_test_framework','-s','-o',str(exe)],'unit-partial-link')==0
identity=sha(exe);code=run([str(exe),'--report_level=detailed','--log_level=test_suite'],'unit-partial');result['units']['partial']={'exit':code,'binary_sha256':identity};save();assert code==201;exe.unlink();(T/'weak.o').unlink()
# Link only changed client object into the otherwise identical real CLI.
link=old['commands'][-1]['command'][2];assert ' -levent_core ' in link;assert link.count(str(R/'client.o'))==1;assert link.count(' -o '+str(R/'btx-cli')+' ')==1
link=link.replace(str(R/'client.o'),str(T/'client.o')).replace(' -o '+str(R/'btx-cli')+' ',' -o '+str(T/'btx-cli')+' ');assert run(['/bin/sh','-c',link],'link-candidate-cli')==0
result['candidate_CLI_sha256']=sha(T/'btx-cli');result['candidate_client_object_sha256']=sha(T/'client.o');save()
for candidate in [False,True]:
 label='workflow-candidate' if candidate else 'workflow-baseline';cli=T/'btx-cli' if candidate else R/'btx-cli';expected=result['candidate_CLI_sha256'] if candidate else old['cli_sha256'];output=T/(label+'.json')
 assert sha(T/'paired_workflow.py')==result['harness_sha256'];assert sha(cli)==expected
 code=run(['python3',str(T/'paired_workflow.py'),str(cli),str(output),expected],label,100);x=json.loads(output.read_text());assert x['suite_complete'] and all(v['passed'] for v in x['checks']);assert len(x['requirements'])==4
 assert code==(0 if candidate else 1);assert len(x['functional_failures'])==(0 if candidate else 4);assert x['cleanup']['helper_stop']=='SIGTERM, no kill fallback' and x['cleanup']['adapter_listener_closed']
 result['workflows'][label]={'exit':code,'requirements':x['requirements'],'failed_properties':len(x['functional_failures']),'guards':len(x['checks']),'CLI_sha256_before':x['cli_sha256_before'],'CLI_sha256_after':x['cli_sha256_after'],'harness_sha256':sha(T/'paired_workflow.py')};save()
result['old_archives_unchanged']={k:sha(k) for k in old['archive_hashes']}==old['archive_hashes'];assert result['old_archives_unchanged'];assert sha(R/'btx-cli')==old['cli_sha256'] and sha(R/'client.o')==result['baseline_client_object'];assert sha(B/'bin/btx-modeld')==old['helper_sha256'];result['complete']=True;save();print('PAIRED_COMPLETE',flush=True)
