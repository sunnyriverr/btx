from pathlib import Path
import os,sys,json,subprocess,hashlib,tarfile,shutil,platform,signal
w=Path(os.environ['GITHUB_WORKSPACE']);root=w/'.mac-retention-fixture';out=w/'retention-records';out.mkdir(exist_ok=True);payload=w/'retention-payload';payload.mkdir(exist_ok=True);env=dict(os.environ,RUSTUP_TOOLCHAIN='1.95.0',LC_ALL='C');state={'mode':sys.argv[1],'btx_built':False,'node_started':False,'checks':{}}
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save():(out/'fixture-result.json').write_text(json.dumps(state,indent=2)+'\n')
def run(args,label,cwd=None,limit=120):
 p=subprocess.Popen(list(map(str,args)),cwd=cwd,env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,start_new_session=True)
 timed=False
 try:stdout,stderr=p.communicate(timeout=limit)
 except subprocess.TimeoutExpired:
  timed=True
  try:os.killpg(p.pid,signal.SIGTERM)
  except ProcessLookupError:pass
  try:stdout,stderr=p.communicate(timeout=5)
  except subprocess.TimeoutExpired:
   try:os.killpg(p.pid,signal.SIGKILL)
   except ProcessLookupError:pass
   stdout,stderr=p.communicate()
 (out/(label+'.log')).write_text(stdout+stderr);assert not timed,(label,'timeout; owned group stopped');assert p.returncode==0,(label,stdout[-500:],stderr[-500:]);return stdout+stderr

def identity():return {'root':str(root),'image':os.getenv('ImageVersion'),'arch':platform.machine(),'cxx':run(['xcrun','clang++','--version'],'compiler'),'rust':run(['rustc','-Vv'],'rust'),'cargo':run(['cargo','-V'],'cargo'),'cmake':run(['cmake','--version'],'cmake'),'ninja':run(['ninja','--version'],'ninja')}
def snapshot():
 d={}
 for p in [root,*root.rglob('*')]:
  k=str(p.relative_to(root));st=p.lstat();v={'mode':st.st_mode&0o777,'mtime_ns':st.st_mtime_ns}
  if p.is_symlink():
   link=os.readlink(p);assert not Path(link).is_absolute() and p.resolve().is_relative_to(root.resolve()),'external symlink refused';v.update(kind='link',link=link)
  elif p.is_dir():v['kind']='dir'
  else:v.update(kind='file',sha256=sha(p),size=st.st_size)
  d[k]=v
 return d

def checkpoint(dest):
 meta=snapshot()
 with tarfile.open(dest,'w:gz') as t:t.add(root,arcname=root.name,recursive=True)
 return meta

def binary_paths():return [root/'cpp-build/fixture',root/'rust/target/aarch64-apple-darwin/release/retention_fixture']
def restore(meta,archive):
 assert not root.exists()
 with tarfile.open(archive) as t:
  members=t.getmembers();assert all(not Path(m.name).is_absolute() and '..' not in Path(m.name).parts and Path(m.name).parts[0]==root.name and (m.isfile() or m.isdir() or m.issym() or m.islnk()) for m in members)
  for m in members:
   if m.islnk():assert not Path(m.linkname).is_absolute() and '..' not in Path(m.linkname).parts and Path(m.linkname).parts[0]==root.name
   if m.issym():assert not Path(m.linkname).is_absolute() and (w/m.name).parent.joinpath(m.linkname).resolve().is_relative_to(root)
  t.extractall(w,filter='data')
 # Replay the exact recorded metadata, after checking content/type identity.
 for name,v in sorted(meta.items(),key=lambda x:len(Path(x[0]).parts),reverse=True):
  p=root/name
  if v['kind']=='file':assert p.is_file() and not p.is_symlink() and sha(p)==v['sha256']
  elif v['kind']=='link':assert p.is_symlink() and os.readlink(p)==v['link']
  else:assert p.is_dir() and not p.is_symlink()
  if not p.is_symlink():p.chmod(v['mode'])
  os.utime(p,ns=(v['mtime_ns'],v['mtime_ns']),follow_symlinks=False)
 assert snapshot()==meta

try:
 if sys.argv[1]=='produce':
  assert not root.exists();(root/'cpp').mkdir(parents=True);(root/'rust/src').mkdir(parents=True)
  (root/'cpp/CMakeLists.txt').write_text('cmake_minimum_required(VERSION 3.22)\nproject(retention_fixture LANGUAGES CXX)\nadd_executable(fixture main.cpp)\n')
  (root/'cpp/main.cpp').write_text('#include <cstdio>\nint main(){puts("original");}\n');(root/'cpp/source-link').symlink_to('main.cpp')
  (root/'rust/Cargo.toml').write_text('[package]\nname="retention_fixture"\nversion="0.1.0"\nedition="2021"\n')
  (root/'rust/src/main.rs').write_text('fn main(){println!("original");}\n')
  run(['cmake','-S',root/'cpp','-B',root/'cpp-build','-G','Ninja','-DCMAKE_BUILD_TYPE=Release'],'cpp-config')
  run(['ninja','-C',root/'cpp-build'],'cpp-build')
  run(['cargo','generate-lockfile','--offline'],'rust-lock',root/'rust')
  run(['cargo','build','--release','--offline','--locked','--target','aarch64-apple-darwin'],'rust-build',root/'rust')
  for i,b in enumerate(binary_paths()):assert run([b],'execute-'+str(i)).strip()=='original';shutil.copy2(b,payload/('binary-'+str(i)))
  # Refuse external links instead of following arbitrary files into a checkpoint.
  (root/'external-link').symlink_to('/etc/hosts')
  try:snapshot();raise RuntimeError('external symlink was accepted')
  except AssertionError:state['checks']['external_symlink_refused']=True
  finally:(root/'external-link').unlink()
  os.link(root/'cpp/main.cpp',root/'cpp/main-hardlink.cpp');assert (root/'cpp/main.cpp').samefile(root/'cpp/main-hardlink.cpp')
  meta=checkpoint(payload/'checkpoint.tar.gz');record={'identity':identity(),'metadata':meta,'archive_sha256':sha(payload/'checkpoint.tar.gz'),'binaries':{p.name:sha(p) for p in payload.glob('binary-*')}}
  with tarfile.open(payload/'finished-binaries.tar.gz','w:gz') as bundle:
   for binary in payload.glob('binary-*'):bundle.add(binary,arcname=binary.name)
  record['binary_archive_sha256']=sha(payload/'finished-binaries.tar.gz')
  for binary in payload.glob('binary-*'):binary.unlink()
  (payload/'checkpoint.json').write_text(json.dumps(record,indent=2));state['checks']['produced']=True;state['injected_later_failure']=True;save();raise SystemExit(23)
 else:
  record=json.loads((payload/'checkpoint.json').read_text());assert identity()==record['identity'];assert sha(payload/'checkpoint.tar.gz')==record['archive_sha256'];restore(record['metadata'],payload/'checkpoint.tar.gz');assert (root/'cpp/main.cpp').samefile(root/'cpp/main-hardlink.cpp');state['checks']['internal_hardlink_preserved']=True
  assert sha(payload/'finished-binaries.tar.gz')==record['binary_archive_sha256']
  finished=w/'restored-finished-binaries';assert not finished.exists();finished.mkdir()
  with tarfile.open(payload/'finished-binaries.tar.gz') as bundle:
   assert all(m.isfile() and Path(m.name).name==m.name and m.name in record['binaries'] for m in bundle.getmembers());bundle.extractall(finished,filter='data')
  for name,digest in record['binaries'].items():assert sha(finished/name)==digest and (finished/name).stat().st_mode&0o111 and run([finished/name],'retained-'+name).strip()=='original'
  state['checks']['independent_binary_artifacts_verified']=True;state['checks']['restored_exact_content_and_metadata']=True
  binaries=binary_paths();before={str(p):(sha(p),p.stat().st_mtime_ns) for p in binaries}
  objects={str(p):p.stat().st_mtime_ns for p in (root/'cpp-build').rglob('*.o')}
  cpp=run(['ninja','-C',root/'cpp-build','-v'],'cpp-unchanged')
  rust=run(['cargo','build','--release','--offline','--locked','--target','aarch64-apple-darwin'],'rust-unchanged',root/'rust')
  assert 'no work to do' in cpp and 'Compiling retention_fixture' not in rust
  assert before=={str(p):(sha(p),p.stat().st_mtime_ns) for p in binaries};assert objects=={str(p):p.stat().st_mtime_ns for p in (root/'cpp-build').rglob('*.o')};state['checks']['unchanged_inputs_no_recompile']=True
  (root/'cpp/main.cpp').write_text('#include <cstdio>\nint main(){puts("changed");}\n');(root/'rust/src/main.rs').write_text('fn main(){println!("changed");}\n')
  run(['ninja','-C',root/'cpp-build','-v'],'cpp-changed');run(['cargo','build','--release','--offline','--locked','--target','aarch64-apple-darwin'],'rust-changed',root/'rust')
  for i,b in enumerate(binaries):assert run([b],'changed-execute-'+str(i)).strip()=='changed' and sha(b)!=before[str(b)][0]
  state['checks']['changed_inputs_rebuild']=True;state['complete']=True;shutil.rmtree(root);state['runtime_removed']=True
except SystemExit:raise
except Exception as e:
 import traceback
 state['error']=repr(e);state['traceback']=traceback.format_exc()
finally:save()
if not state.get('complete'):raise SystemExit(1)
