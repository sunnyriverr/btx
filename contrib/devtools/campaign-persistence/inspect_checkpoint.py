"""Hosted immutable checkpoint inspection only; never extract or execute its binaries."""
from pathlib import Path
import os,json,tarfile,hashlib,re
def main():
 w=Path(os.environ['GITHUB_WORKSPACE']);out=w/'campaign-plan-records';out.mkdir(exist_ok=True);s={'compiled':False,'product_executed':False,'original_cache_mutated':False}
 try:
  manifests=list((w/'saved-checkpoint').rglob('manifest.json'));assert len(manifests)==1
  m=json.loads(manifests[0].read_text());archive=manifests[0].parent/'build-state.tar.gz'
  h=hashlib.sha256()
  with archive.open('rb') as f:
   for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
  assert h.hexdigest()==m['archive_sha256'];s['archive_sha256']=h.hexdigest();s['identity']=m['identity'];rows=m['rows']
  assert m['identity']['source']=='dac9aee53520bd49ed320ec7a49b9072fc7d88d9'
  s['objects']=[n for n in rows if n.endswith('.o')];s['object_count']=len(s['objects'])
  s['helper_objects']=[n for n in s['objects'] if any(x in n for x in ('helper.cpp.o','release.cpp.o','modeld.cpp.o'))]
  s['helper_source_sha256']=rows['product/src/modelnet/helper.cpp']['sha256']
  names=['gui-pilot-runtime/qtbuild/CMakeCache.txt','gui-pilot-runtime/qtbuild/build.ninja']
  metadata={}
  with tarfile.open(archive) as tar:
   for member in tar:
    if member.name not in names:continue
    assert member.isfile() and member.size<15*1024**2
    data=tar.extractfile(member).read();assert hashlib.sha256(data).hexdigest()==rows[member.name]['sha256']
    metadata[member.name]=data.decode();(out/Path(member.name).name).write_bytes(data)
  assert len(metadata)==2
  cache=metadata[names[0]];ninja=metadata[names[1]]
  s['configuration']=[l for l in cache.splitlines() if re.match(r'(CMAKE_(BUILD_TYPE|CXX_COMPILER|C_COMPILER|MAKE_PROGRAM)|WITH_MODELNET|ENABLE_WALLET|BUILD_GUI|OPENSSL|WITH_SQLITE|WITH_ZMQ)',l)]
  assert 'WITH_MODELNET:BOOL=ON' in cache
  s['helper_graph']=[l for l in ninja.splitlines() if l.startswith('build ') and any(x in l for x in ('helper.cpp.o','modelnet/release.cpp.o','bin/btx-modeld:'))]
  assert s['helper_graph'],'Helper target absent from retained build graph'
  s['pass']=True
 except Exception as e:s['error']=repr(e);s['pass']=False
 finally:(out/'result.json').write_text(json.dumps(s,indent=2)+'\n')
 return 0 if s['pass'] else 1
if __name__=='__main__':raise SystemExit(main())
