from pathlib import Path
import json,os,subprocess,hashlib,shutil,time,re,sys
P=Path(__file__).resolve().parent;R=Path('D:/btx-native-035');B=R/'project-build';S=Path(os.environ['GITHUB_WORKSPACE'])/'btx';E=R/'unit-governor-evidence';STATE=E/'result.json';BACK=R/'governor-backup';r=json.loads(STATE.read_text());cp=json.loads((B/'btx-successor.json').read_text());review=json.loads((P/'review.json').read_text())
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def save():STATE.write_text(json.dumps(r,indent=2)+'\n')
def command(label,args,cap=180):
 st=time.monotonic();v=subprocess.run(args,cwd=B,capture_output=True,timeout=cap);out=v.stdout+v.stderr;(E/(label+'.log')).write_bytes(out);r.setdefault('diagnostic_commands',[]).append({'label':label,'exit':v.returncode,'seconds':round(time.monotonic()-st,3)});save();assert v.returncode==0,out[-4000:].decode(errors='replace');return out.decode(errors='replace')
def snapshot():
 assert not BACK.exists();BACK.mkdir();files=[]
 for n in cp['files']:
  path=Path(n);base=path.name
  if not n.replace('\\','/').startswith('project-build/'):continue
  if base.endswith('.obj') and base not in ['resource_governor_tests.cpp.obj','fs_helpers.cpp.obj']:continue
  if base.endswith('.lib') and 'bitcoin_util' not in base:continue
  if base.endswith('.exe') and base!='test_btx.exe':continue
  if base.endswith('.dll'):continue
  dest=BACK/n;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(R/n,dest);files.append(n)
 for name in ['.ninja_log','.ninja_deps']:
  path=B/name
  if path.exists():
   n=path.relative_to(R).as_posix()
   if n not in files:dest=BACK/n;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(path,dest);files.append(n)
 for source in review['files']:
  dest=BACK/'source'/source;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(S/source,dest)
 (BACK/'files.json').write_text(json.dumps(files));r['diagnostic_backup_files']=len(files);r['diagnostic_backup_complete']=True;save()
def build():
 assert r['status']=='RESTORED_VERIFIED';assert shutil.disk_usage(R).free>8*1024**3
 assert '20.1.8' in command('diagnostic-compiler',['clang-cl','--version'])
 assert os.environ['VCToolsVersion'].rstrip('\\')=='14.51.36231'
 assert os.environ['WindowsSDKVersion'].rstrip('\\')=='10.0.26100.0'
 baseline_imports=command('baseline-imports',['dumpbin','/imports',str(B/'bin/test_btx.exe')]);r['baseline_import_dlls']=sorted(set(re.findall(r'^\s+([A-Za-z0-9_.-]+\.dll)\s*$',baseline_imports,re.M|re.I)))
 assert r['baseline_import_dlls']
 snapshot()
 for n,info in cp['source_files'].items():
  path=S/n;assert sha(path)==info['sha256'];os.utime(path,ns=(path.stat().st_atime_ns,info['mtime_ns']))
 for source,info in review['files'].items():
  assert sha(S/source)==info['baseline_sha256'];candidate=P/info['candidate'];assert sha(candidate)==info['diagnostic_sha256'];shutil.copyfile(candidate,S/source)
 # Frozen graph avoids auto-configure; bounded dry-run is mandatory before compile.
 plan=E/'diagnostic.ninja'
 graph=(B/'build.ninja').read_text()
 wanted=['src/test/CMakeFiles/test_btx.dir/resource_governor_tests.cpp.obj','src/util/CMakeFiles/bitcoin_util.dir/fs_helpers.cpp.obj','lib/bitcoin_util.lib','bin/test_btx.exe']
 lines=graph.splitlines();edges=[]
 for target in wanted:
  matches=[i for i,line in enumerate(lines) if line.startswith('build '+target+':')];assert len(matches)==1,target
  i=matches[0];edge=[lines[i].split(' || ',1)[0]];j=i+1
  while j<len(lines) and lines[j].startswith('  '):edge.append(lines[j]);j+=1
  if target=='bin/test_btx.exe':
   assert any(line.startswith('  POST_BUILD = ') and 'vcpkg' in line for line in edge)
   edge=['  POST_BUILD = cd .' if line.startswith('  POST_BUILD = ') else line for line in edge]
  edges.append('\n'.join(edge))
 # Keep exact generated rules, flags and link inputs. Unchanged binaries/objects
 # are immutable leaf inputs; this is an instrumentation-only graph, not a full build.
 header='ninja_required_version = 1.8\nCONFIGURATION = Release\ninclude CMakeFiles/rules.ninja\ncmake_ninja_workdir = D$:/btx-native-035/project-build/\n'
 plan.write_text(header+'\n\n'.join(edges)+'\ndefault bin/test_btx.exe\n')
 r['diagnostic_graph_scope']='Four exact generated build edges; original order-only generator/helper rebuild edges omitted, cached inputs unchanged';save()
 out=command('diagnostic-dry-run',['ninja','-C',str(B),'-f',str(plan),'-n','bin/test_btx.exe'])
 actions=[x for x in out.splitlines() if re.match(r'^\[\d+/\d+\]',x)];r['diagnostic_plan']=actions;save()
 assert 1<=len(actions)<=4,actions
 for a in actions:
  assert any(s in a for s in ['resource_governor_tests.cpp.obj','fs_helpers.cpp.obj','bitcoin_util.lib','bin\\test_btx.exe','bin/test_btx.exe']),a
  assert 'Re-running CMake' not in a
 command('diagnostic-build',['ninja','-C',str(B),'-f',str(plan),'-j2','bin/test_btx.exe'],cap=480)
 diag_imports=command('diagnostic-imports',['dumpbin','/imports',str(B/'bin/test_btx.exe')]);r['diagnostic_import_dlls']=sorted(set(re.findall(r'^\s+([A-Za-z0-9_.-]+\.dll)\s*$',diag_imports,re.M|re.I)));assert r['diagnostic_import_dlls']==r['baseline_import_dlls']
 r['diagnostic_binary_sha256']=sha(B/'bin/test_btx.exe');assert r['diagnostic_binary_sha256']!=r['test_btx_sha256'];r['production_rule_change']=False;r['instrumentation_only']=True;save()
def restore():
 if not (BACK/'files.json').exists():r['diagnostic_restore']='NO_MUTATION';save();return
 for n in json.loads((BACK/'files.json').read_text()):shutil.copy2(BACK/n,R/n)
 for source in review['files']:shutil.copy2(BACK/'source'/source,S/source)
 for n,info in cp['files'].items():assert sha(R/n)==info['sha256'],n
 for n,info in cp['source_files'].items():assert sha(S/n)==info['sha256'],n
 r['diagnostic_restore']='ALL_ORIGINAL_CACHE_AND_SOURCE_HASHES_VERIFIED';r['baseline_binary_restored']=sha(B/'bin/test_btx.exe');shutil.rmtree(BACK);r['diagnostic_backup_removed']=True;save()
try:{'build':build,'restore':restore}[sys.argv[1]]()
except BaseException as e:r.setdefault('diagnostic_errors',[]).append({'stage':sys.argv[1],'error':repr(e)});save();raise
