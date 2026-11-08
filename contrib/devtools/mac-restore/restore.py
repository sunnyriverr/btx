"""Restore the actual partial BTX checkpoint and inspect plans only; never compile."""
from pathlib import Path
import hashlib,json,os,tarfile,shutil,subprocess,time,sys,traceback
from process_tracker import OwnedProcesses
w=Path(os.environ['GITHUB_WORKSPACE']);out=w/'restore-records';out.mkdir(exist_ok=True)
payload=w/'restore-payload';src=w/'product';build=w/'mac-config-build'
state={'source':'ff5f3f04ea11f044594987fc6be043ff68b136ad','source_run':42476421106,'btx_compiled':False,'node_started':False,'checks':{}}
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
def save():(out/'restore-result.json').write_text(json.dumps(state,indent=2)+'\n')
def run(args,label,limit=120):
 with (out/(label+'.log')).open('w') as log:
  p=subprocess.Popen(list(map(str,args)),stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
  t=OwnedProcesses(p);end=time.monotonic()+limit
  try:
   while p.poll() is None:
    t.update()
    assert time.monotonic()<end,label+' timeout'
    time.sleep(.1)
   assert p.returncode==0,(label,p.returncode)
  finally:
   remaining=t.stop();assert remaining['processes']==[]
 return (out/(label+'.log')).read_text()
try:
 assert shutil.disk_usage(w).free>16*1024**3
 expected=json.loads(Path(__file__).with_name('expected.json').read_text())
 record=json.loads((payload/'after/receipt.json').read_text());invfile=payload/'after/inventory.json';inv=json.loads(invfile.read_text());archive=payload/'after/checkpoint.tar.gz'
 assert record==expected['checkpoint']
 assert sha(invfile)==record['inventory_sha256'] and sha(archive)==record['sha256'] and archive.stat().st_size==record['bytes']
 assert len(inv)==record['entries']
 assert run(['git','-C',src,'rev-parse','HEAD'],'fresh-source').strip()==state['source']
 assert not run(['git','-C',src,'status','--porcelain'],'fresh-clean').strip()
 # Fresh pinned configuration must agree with the original command graph before reuse.
 commands=w/'mac-config-records/generated-build-commands.log'
 assert sha(commands)==expected['commands_sha256'],'Generated command graph differs from saved producer'
 state['checks']['fresh_command_graph_matches']=True
 stage=w/'.restore-stage';assert not stage.exists();stage.mkdir()
 with tarfile.open(archive) as t:
  members=t.getmembers();assert len(members)==len(inv)
  assert len({m.name for m in members})==len(inv)
  for m in members:
   path=Path(m.name);assert m.name in inv and not path.is_absolute() and '..' not in path.parts and path.parts[0] in ['product','mac-config-build']
   assert m.isfile() or m.isdir() or m.issym() or m.islnk()
   if m.issym():
    assert not Path(m.linkname).is_absolute() and m.linkname==inv[m.name]['archive_target']
    assert any((stage/m.name).parent.joinpath(m.linkname).resolve().is_relative_to(stage/r) for r in ['product','mac-config-build'])
   if m.islnk():assert m.linkname in inv and not Path(m.linkname).is_absolute() and '..' not in Path(m.linkname).parts
  t.extractall(stage,filter='data')
 # Restore original recorded mtimes, including nanoseconds, only after content verification.
 for n,v in sorted(inv.items(),key=lambda x:len(Path(x[0]).parts),reverse=True):
  p=stage/n
  if v['type']=='file':assert p.is_file() and not p.is_symlink() and sha(p)==v['sha256'] and p.stat().st_size==v['bytes'];p.chmod(v['mode'])
  elif v['type']=='dir':assert p.is_dir() and not p.is_symlink();p.chmod(v['mode'])
  else:assert p.is_symlink() and os.readlink(p)==v['archive_target']
  os.utime(p,ns=(v['mtime_ns'],v['mtime_ns']),follow_symlinks=False)
 # Keep verified fresh Git metadata outside the tar, never restore credentials from an artifact.
 oldsource=w/'identity-checkout';src.rename(oldsource);shutil.rmtree(build)
 (stage/'product').rename(src);(stage/'mac-config-build').rename(build)
 (oldsource/'.git').rename(src/'.git')
 for n,v in sorted(inv.items(),key=lambda x:len(Path(x[0]).parts),reverse=True):
  p=w/n
  if v['type']=='symlink' and os.readlink(p)!=v['target']:
   p.unlink();p.symlink_to(v['target'])
   assert any(p.resolve().is_relative_to(w/r) for r in ['product','mac-config-build'])
  os.utime(p,ns=(v['mtime_ns'],v['mtime_ns']),follow_symlinks=False)
 for n,v in inv.items():
  p=w/n;st=p.lstat();assert st.st_mtime_ns==v['mtime_ns'] and st.st_mode&0o777==v['mode'],('metadata',n)
  if v['type']=='file':assert sha(p)==v['sha256']
  if v['type']=='symlink':assert os.readlink(p)==v['target']
 state['checks']['exact_content_modes_ns_mtimes_links_restored']=True
 assert not run(['git','-C',src,'status','--porcelain'],'restored-source-clean').strip()
 state['checks']['fresh_git_identity_preserved']=True
 objects={n:v for n,v in inv.items() if n.startswith('mac-config-build/') and n.endswith('.o')}
 state['retained_objects']=len(objects);assert len(objects)==2606
 # Configuration regeneration is permitted; no compiler/build command is executed.
 # Observe untouched dry-run first, then explicit configure-only regeneration to avoid stale generator timestamps.
 targets=json.loads(Path(__file__).with_name('targets.json').read_text())
 run(['ninja','-C',build,'-n','-d','explain',*targets],'restored-initial-dry-plan')
 run(['cmake','-S',src,'-B',build],'restored-configure-only',300)
 aftercommands=run(['ninja','-C',build,'-t','commands',*targets],'restored-command-graph')
 assert hashlib.sha256(aftercommands.encode()).hexdigest()==expected['commands_sha256'],'Restored commands changed after configure'
 plan=run(['ninja','-C',build,'-n','-d','explain',*targets],'restored-final-dry-plan')
 scheduled=[]
 for n,v in objects.items():
  relative=n.removeprefix('mac-config-build/')
  if 'Building CXX object '+relative in plan or 'Building C object '+relative in plan:scheduled.append(n)
 assert not scheduled,('Previously completed objects scheduled to rebuild',scheduled[:20])
 for n,v in objects.items():assert sha(w/n)==v['sha256'] and (w/n).stat().st_mtime_ns==v['mtime_ns']
 state['checks']['retained_objects_not_scheduled_or_modified']=True
 state['checks']['command_graph_matches_after_regeneration']=True
 state['remaining_dry_plan_build_lines']=sum('Building ' in x or 'Linking ' in x for x in plan.splitlines())
 state['final_dry_plan_tail']=plan[-1800:]
 assert state['remaining_dry_plan_build_lines']>0,'Incomplete build must retain real remaining work'
 state['complete']=True
except Exception as e:
 state['error']=repr(e);state['traceback']=traceback.format_exc()
finally:
 state['free_disk_bytes']=shutil.disk_usage(w).free;save()
sys.exit(0 if state.get('complete') else 1)
