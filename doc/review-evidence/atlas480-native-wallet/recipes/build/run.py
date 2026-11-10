"""Fresh candidate-only native Atlas build; immutable baseline and working node untouched."""
from pathlib import Path
import os,sys,json,subprocess,signal,time,shutil,hashlib,tarfile
from abi_inspect import inspect_binary
HEAD='f6b2ac8e606789d69c5d7a4edbf21ff11826b557';BASE='dac9aee53520bd49ed320ec7a49b9072fc7d88d9'
INPUTS=['Cargo.lock','Cargo.toml','src-tauri/Cargo.toml','src-tauri/build.rs','src-tauri/tauri.conf.json','src-tauri/src/main.rs']
def sha(f):return hashlib.sha256(f.read_bytes()).hexdigest()
def main():
 w=Path(os.environ['GITHUB_WORKSPACE']).resolve();src=w/'product';atlas=src/'gui/atlas';out=w/'atlas480-build-records';out.mkdir(exist_ok=False);outputs=w/'atlas480-binary';outputs.mkdir(exist_ok=False)
 target=w/'atlas480-target';cargo=w/'atlas480-cargo';assert not target.exists() and not cargo.exists()
 env=dict(os.environ,CARGO_TARGET_DIR=str(target),CARGO_HOME=str(cargo),CARGO_BUILD_JOBS='2');overall_start=time.monotonic();r={'source':HEAD,'base':BASE,'commands':[],'fresh_build':True,'original_cache_accessed':False,'working_node_accessed':False}
 def save():(out/'result.json').write_text(json.dumps(r,indent=2)+'\n')
 def run(args,label,limit=120):
  print('START',label,flush=True)
  with (out/(label+'.log')).open('wb') as f:
   stderr_log=(out/'metadata-stderr.log').open('wb') if label=='metadata' else None
   child=subprocess.Popen(list(map(str,args)),cwd=atlas,stdout=f,stderr=stderr_log if stderr_log else subprocess.STDOUT,env=env,start_new_session=True);start=time.monotonic();stop=None
   while child.poll() is None:
    if time.monotonic()-start>limit or time.monotonic()-overall_start>1200:stop='timeout'
    if shutil.disk_usage(w).free<2*1024**3:stop='disk_reserve'
    if stop:
     os.killpg(child.pid,signal.SIGTERM)
     try:child.wait(15)
     except subprocess.TimeoutExpired:os.killpg(child.pid,signal.SIGKILL);child.wait()
     break
    time.sleep(1)
  if stderr_log:stderr_log.close()
  r['commands'].append({'label':label,'exit':child.returncode,'seconds':time.monotonic()-start,'stop':stop,'args':list(map(str,args))});save();print('END',label,child.returncode,flush=True)
  assert child.returncode==0 and not stop,label
  return (out/(label+'.log')).read_text(errors='replace')
 try:
  assert shutil.disk_usage(w).free>10*1024**3
  assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=src,text=True).strip()==HEAD
  assert not subprocess.check_output(['git','status','--porcelain'],cwd=src)
  r['build_inputs']={x:sha(atlas/x) for x in INPUTS};r['native_inputs_unchanged']=all(sha(atlas/x)==sha(w/'accepted-source/gui/atlas'/x) for x in INPUTS);assert r['native_inputs_unchanged']
  r['web_inputs']={str(f.relative_to(atlas)):sha(f) for root in ('web','schemas') for f in (atlas/root).rglob('*') if f.is_file()}
  assert json.loads((atlas/'src-tauri/tauri.conf.json').read_text())['build']['frontendDist']=='../web'
  assert 'Repeat passphrase' in (atlas/'web/views/wallet.js').read_text()
  run(['rustup','toolchain','install','1.95.0','--profile','minimal'],'toolchain',300)
  assert 'rustc 1.95.0' in run(['rustc','+1.95.0','--version'],'rustc')
  run(['cargo','+1.95.0','--version'],'cargo')
  run(['pkg-config','--modversion','gtk+-3.0','webkit2gtk-4.1','javascriptcoregtk-4.1','ayatana-appindicator3-0.1'],'pkg-config')
  metadata=json.loads(run(['cargo','+1.95.0','metadata','--locked','--format-version','1','--no-deps'],'metadata'))
  packages={x['name']:x for x in metadata['packages']};assert set(packages)=={'btx-atlas','btx-atlas-core'}
  app=packages['btx-atlas'];assert any('bin' in x['kind'] and x['name']=='btx-atlas' for x in app['targets'])
  assert Path(metadata['target_directory'])==target and Path(metadata['workspace_root'])==atlas
  r['build_plan_verified']=True
  run(['cargo','+1.95.0','fetch','--locked'],'fetch',300)
  run(['cargo','+1.95.0','build','--locked','--release','-p','btx-atlas','-j2'],'compile',900)
  binary=target/'release/btx-atlas';assert binary.is_file();shutil.copy2(binary,outputs/'btx-atlas')
  r['binary_sha256']=sha(binary);r['compiled']=True
  inspect_binary(binary,out,r,run)
  assert r['build_inputs']=={x:sha(atlas/x) for x in INPUTS}
  assert r['web_inputs']=={str(f.relative_to(atlas)):sha(f) for root in ('web','schemas') for f in (atlas/root).rglob('*') if f.is_file()}
  r['source_clean']=not bool(subprocess.check_output(['git','status','--porcelain','--untracked-files=no'],cwd=src));assert r['source_clean']
 except Exception as e:r['error']=repr(e)
 finally:
  # Retain new task-owned objects and public registry input without replacing any old cache.
  if target.exists():
   try:
    cacheout=w/'atlas480-build-state';cacheout.mkdir(exist_ok=False);roots=[target]
    if cargo.exists():roots.append(cargo)
    assert not (cargo/'credentials').exists() and not (cargo/'credentials.toml').exists()
    rows={}
    for root in roots:
     for f in root.rglob('*'):
      if f.is_symlink():assert f.resolve().is_relative_to(w),'External checkpoint link'
      elif f.is_file():rows[str(f.relative_to(w))]={'sha256':sha(f),'mode':oct(f.stat().st_mode&0o777),'mtime_ns':f.stat().st_mtime_ns}
    archive=cacheout/'state.tar.gz'
    with tarfile.open(archive,'w:gz',compresslevel=1) as tar:
     for root in roots:tar.add(root,arcname=root.name)
    (cacheout/'manifest.json').write_text(json.dumps({'source':HEAD,'workspace':str(w),'toolchain':'1.95.0','archive_sha256':sha(archive),'files':rows,'restore_verified':False},indent=2)+'\n')
    r['retained_state']={'sha256':sha(archive),'files':len(rows),'restore_verified':False}
   except Exception as e:r['retention_error']=repr(e)
  r['pass']=r.get('compiled') is True and r.get('abi_pass') is True and r.get('source_clean') is True and not r.get('error');save()
 return 0 if r['pass'] else 1
if __name__=='__main__':sys.exit(main())
