"""Restore only a new hosted copy, build only the two admitted helper targets."""
from pathlib import Path
import os,json,sys,subprocess,tarfile,shutil,time,re,signal
from checkpoint import sha,restore_timestamps,verify_restored,create
BASE='dac9aee53520bd49ed320ec7a49b9072fc7d88d9'
ARCHIVE='90391b49487f57e3c820200f28142e6873b0fecbb2a2d4b82091e48050437176'
def main():
 w=Path(os.environ['GITHUB_WORKSPACE']).resolve();out=w/'campaign-build-records';out.mkdir(exist_ok=True);r={'product_compiled':False,'product_executed':False,'commands':[]}
 def run(args,label,cwd=None,limit=180):
  start=time.monotonic()
  with (out/(label+'.log')).open('wb') as f:
   p=subprocess.Popen(list(map(str,args)),cwd=cwd,stdout=f,stderr=subprocess.STDOUT,start_new_session=True)
   while p.poll() is None:
    if time.monotonic()-start>limit or shutil.disk_usage(w).free<2*1024**3:
     os.killpg(p.pid,signal.SIGTERM)
     try:p.wait(10)
     except subprocess.TimeoutExpired:os.killpg(p.pid,signal.SIGKILL);p.wait()
     raise RuntimeError(label+' exceeded time or disk bound')
    time.sleep(.25)
  r['commands'].append({'label':label,'exit':p.returncode,'seconds':time.monotonic()-start});assert p.returncode==0,label
  return (out/(label+'.log')).read_text(errors='replace')
 try:
  assert shutil.disk_usage(w).free>10*1024**3
  saved=w/'saved-checkpoint';m=json.loads((saved/'manifest.json').read_text());archive=saved/'build-state.tar.gz'
  assert sha(archive)==ARCHIVE==m['archive_sha256'] and m['identity']['source']==BASE and Path(m['workspace'])==w
  assert not (w/'product').exists() and not (w/'gui-pilot-runtime').exists()
  with tarfile.open(archive) as t:t.extractall(w,filter='data')
  restore_timestamps(w,m);verify_restored(w,m);r['restore_verified']=True
  src=w/'product';build=w/'gui-pilot-runtime/qtbuild';git=w/'accepted-source/.git';assert git.is_dir()
  shutil.copytree(git,src/'.git');assert run(['git','rev-parse','HEAD'],'base-head',src).strip()==BASE
  assert not run(['git','status','--porcelain','--untracked-files=no'],'base-clean',src).strip()
  assert run(['g++','-dumpfullversion'],'compiler').strip()=='11.4.0'
  assert 'OpenSSL 3.5.9' in run([w/'gui-pilot-runtime/openssl/bin/openssl','version'],'openssl')
  before={str(f.relative_to(build)):sha(f) for f in build.rglob('*.o')};r['objects_before']=len(before)
  def plan(label):
   run(['cmake','-S',src,'-B',build],label+'-configure')
   cache=(build/'CMakeCache.txt').read_text();assert 'WITH_MODELNET:BOOL=ON' in cache and str(w/'gui-pilot-runtime/openssl/lib/libcrypto.a') in cache
   run(['cmake','-P',build/'CMakeFiles/VerifyGlobs.cmake'],label+'-globs',build)
   path=out/(label+'.ninja');shutil.copy2(build/'build.ninja',path)
   dry=run(['ninja','-C',build,'-f',path,'-d','explain','-n','btx-modeld'],label+'-plan')
   assert 'Re-running CMake' not in dry and 'Re-checking globbed' not in dry
   r[label+'_steps']=[l for l in dry.splitlines() if l.startswith('[')]
   run(['ninja','-C',build,'-t','commands','btx-modeld'],label+'-commands')
  expected=json.loads(Path(__file__).with_name('preparation-receipt.json').read_text())
  binaries=w/'campaign-helper-binaries';binaries.mkdir();r['binaries']={}
  def compile_helper(label):
   actions=lambda rows:{re.sub(r'^\[\d+/\d+\] ','',x) for x in rows}
   seen=actions(r[label+'_steps']);allowed=actions(expected[label+'_steps'])
   assert seen and seen<=allowed,(label,'unadmitted build actions',sorted(seen-allowed))
   assert 'Linking CXX executable bin/btx-modeld' in seen
   if label=='candidate':assert any('bitcoin_modelnet.dir/release.cpp.o' in x for x in seen)
   assert shutil.disk_usage(w).free>4*1024**3
   r['product_compiled']=True
   run(['cmake','--build',build,'--target','btx-modeld','--parallel','1'],label+'-compile',limit=720)
   b=binaries/label;shutil.copy2(build/'bin/btx-modeld',b);r['binaries'][label]=sha(b)
   run(['ldd',b],label+'-ldd')
   assert 'not found' not in (out/(label+'-ldd.log')).read_text()
  plan('base');compile_helper('base')
  patch=Path(__file__).with_name('candidate.patch');r['patch_sha256']=sha(patch)
  run(['git','apply','--check',patch],'patch-check',src);run(['git','apply',patch],'patch-apply',src)
  names=run(['git','diff','--name-only'],'changed-files',src).splitlines()
  # New untracked test is inspected explicitly in addition to the tracked diff.
  assert set(names)=={'src/modelnet/release.cpp','src/test/CMakeLists.txt'}
  assert (src/'src/test/modelnet_release_store_tests.cpp').is_file()
  assert sha(src/'src/modelnet/helper.cpp')==m['rows']['product/src/modelnet/helper.cpp']['sha256']
  run(['git','add','src/modelnet/release.cpp','src/test/CMakeLists.txt','src/test/modelnet_release_store_tests.cpp'],'integration-index',src)
  r['integration_tree']=run(['git','write-tree'],'integration-tree',src).strip();assert r['integration_tree']==expected['integration_tree'];assert r['patch_sha256']==expected['patch_sha256'];plan('candidate');compile_helper('candidate')
  r['objects_unchanged']=before=={str(f.relative_to(build)):sha(f) for f in build.rglob('*.o')}
  r['archive_unchanged']=sha(archive)==ARCHIVE;assert r['archive_unchanged'] and r['binaries']['base']!=r['binaries']['candidate']
  r['pass']=True
 except Exception as e:r['error']=repr(e);r['pass']=False
 finally:
  if r.get('restore_verified'):
   try:
    m=create(w,w/'campaign-build-state',{'base':BASE,'integration_tree':r.get('integration_tree'),'binaries':r.get('binaries',{})});r['new_state_sha256']=m['archive_sha256']
   except Exception as e:r['retention_error']=repr(e)
  (out/'result.json').write_text(json.dumps(r,indent=2)+'\n')
 return 0 if r['pass'] else 1
if __name__=='__main__':raise SystemExit(main())
