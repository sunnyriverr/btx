"""Hosted preparation only: restore successor, configure and dry-plan; never compile BTX."""
from pathlib import Path
import os,json,sys,subprocess,hashlib,shutil,tarfile,signal,time
from checkpoint import sha,restore_timestamps,verify_restored
OLD='ff5f3f04ea11f044594987fc6be043ff68b136ad'
NEW='dac9aee53520bd49ed320ec7a49b9072fc7d88d9'
TAR='f8d97a5e97a1610206c27171956fd5e6cec821b0918086d014f5b4a970833986'
LABELS={'accepted-head','accepted-clean','accepted-files','successor-head','successor-clean','gcc','qt','openssl','installed-packages','old-commands','configure','new-commands','dry-plan'}
REQUIRED=('archive_verified','restore_verified','source_updated','toolchain_verified','configured','plan_captured','preserved')
def verdict(r):
 if not LABELS.issubset({c.get('label') for c in r.get('commands',[])}): return 'INCOMPLETE'
 if r.get('error') or any(c.get('exit')!=0 or c.get('stop') for c in r.get('commands',[])): return 'INCOMPLETE'
 return 'PREPARATION_PASS' if all(r.get(k) is True for k in REQUIRED) and r.get('source')==NEW and r.get('product_compile_started') is False else 'INCOMPLETE'
def main():
 w=Path(os.environ['GITHUB_WORKSPACE']).resolve();out=w/'pilot-records';out.mkdir(exist_ok=False)
 r={'source':NEW,'commands':[],'product_compile_started':False}
 def save(): (out/'result.json').write_text(json.dumps(dict(r,verdict=verdict(r)),indent=2)+'\n')
 def run(args,label,limit=120,cwd=None):
  with (out/(label+'.log')).open('wb') as f:
   child=subprocess.Popen(list(map(str,args)),stdout=f,stderr=subprocess.STDOUT,cwd=cwd,start_new_session=True);start=time.monotonic();stop=None
   while child.poll() is None:
    if time.monotonic()-start>limit:stop='timeout'
    if shutil.disk_usage(w).free<2*1024**3:stop='disk_reserve'
    if stop:
     os.killpg(child.pid,signal.SIGTERM)
     try:child.wait(10)
     except subprocess.TimeoutExpired:os.killpg(child.pid,signal.SIGKILL);child.wait()
     break
    time.sleep(.5)
  r['commands'].append({'label':label,'exit':child.returncode,'stop':stop,'seconds':time.monotonic()-start});save()
  if child.returncode or stop:raise RuntimeError(label)
  return (out/(label+'.log')).read_text(errors='replace')
 try:
  assert sys.version_info>=(3,12)
  assert shutil.disk_usage(w).free>=10*1024**3
  assert (w/'product').exists() is False and not (w/'gui-pilot-runtime').exists()
  saved=w/'saved-checkpoint';tar=saved/'build-state.tar.gz';m=json.loads((saved/'manifest.json').read_text())
  assert sha(tar)==TAR==m['archive_sha256'] and m['identity']['source']==OLD
  assert Path(m['workspace'])==w,'Absolute build paths differ: do not relocate cache silently'
  r['archive_verified']=True
  # Use the already-qualified data-filter reader. Original uploaded archive stays immutable.
  with tarfile.open(tar) as t:t.extractall(w,filter='data')
  restore_timestamps(w,m);verify_restored(w,m);r['restore_verified']=True
  src=w/'product';target=w/'accepted-source';build=w/'gui-pilot-runtime/qtbuild'
  assert run(['git','rev-parse','HEAD'],'accepted-head',cwd=target).strip()==NEW
  assert not run(['git','status','--porcelain'],'accepted-clean',cwd=target).strip()
  oldfiles={k.removeprefix('product/'):v for k,v in m['rows'].items() if k.startswith('product/') and v['kind']!='directory'}
  names=run(['git','ls-files'],'accepted-files',cwd=target).splitlines();wanted=set(names);changed=[]
  for name in oldfiles.keys()-wanted:
   q=src/name
   if q.is_file() or q.is_symlink():q.unlink()
  for name in names:
   a=target/name;b=src/name;b.parent.mkdir(parents=True,exist_ok=True)
   if a.is_symlink():
    if b.is_symlink() and os.readlink(a)==os.readlink(b):continue
    if b.exists() or b.is_symlink():b.unlink()
    b.symlink_to(os.readlink(a));changed.append(name)
   elif not b.is_file() or b.is_symlink() or sha(a)!=sha(b) or a.stat().st_mode&0o777!=b.stat().st_mode&0o777:
    if b.is_symlink():b.unlink()
    shutil.copy2(a,b);changed.append(name)
  assert (target/'.git').is_dir() and not (src/'.git').exists()
  shutil.copytree(target/'.git',src/'.git')
  assert run(['git','rev-parse','HEAD'],'successor-head',cwd=src).strip()==NEW
  assert not run(['git','status','--porcelain','--untracked-files=no'],'successor-clean',cwd=src).strip()
  r['source_updated']=True;r['changed_source_files']=changed
  assert run(['g++','-dumpfullversion'],'gcc').strip()=='11.4.0'
  qtpaths=next((x for x in ['/usr/bin/qtpaths6','/usr/lib/qt6/bin/qtpaths','/usr/lib/qt6/bin/qtpaths6'] if Path(x).is_file()),None)
  assert qtpaths,'Qt paths tool absent'
  assert run([qtpaths,'--query','QT_VERSION'],'qt').strip()=='6.2.4'
  assert 'OpenSSL 3.5.9' in run([w/'gui-pilot-runtime/openssl/bin/openssl','version'],'openssl')
  run(['dpkg-query','-W'],'installed-packages');r['toolchain_verified']=True
  before={str(x.relative_to(build)):sha(x) for x in build.rglob('*.o')}
  oldcmd=run(['ninja','-C',build,'-t','commands','btx-qt'],'old-commands')
  run(['cmake','-S',src,'-B',build], 'configure',300)
  cache=(build/'CMakeCache.txt').read_text()
  for flag in ['BUILD_GUI:BOOL=ON','WITH_MODELNET:BOOL=ON','ENABLE_WALLET:BOOL=ON','WITH_ZMQ:BOOL=ON','WITH_SQLITE:BOOL=ON']:assert flag in cache,flag
  assert 'WITH_QT_VERSION:STRING=6' in cache
  r['configured']=True
  newcmd=run(['ninja','-C',build,'-t','commands','btx-qt'],'new-commands')
  dry=run(['ninja','-C',build,'-d','explain','-n','btx-qt'],'dry-plan',120)
  r['plan_captured']=True;r['planned_step_lines']=[s for s in dry.splitlines() if s.startswith('[')]
  r['compile_command_set_changed']=oldcmd!=newcmd
  r['objects_before']=len(before);r['objects_unchanged']=before=={str(x.relative_to(build)):sha(x) for x in build.rglob('*.o')}
  r['preserved']=r['objects_unchanged'] and sha(tar)==TAR
  assert r['preserved']
  for name in ['CMakeCache.txt','compile_commands.json','build.ninja']:shutil.copy2(build/name,out/name)
 except Exception as e:r['error']=repr(e)
 finally:save()
 return 0 if verdict(r)=='PREPARATION_PASS' else 1
if __name__=='__main__':sys.exit(main())
