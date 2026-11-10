"""Read-only hosted cache inventory. Does not extract or execute product binaries."""
import hashlib,json,os,tarfile,re
from pathlib import Path
ARCHIVE='c4b58e4ef14e93f8b257c18bc855a7d9e4079a4659c9e3266fd25acad50d66df'
def main():
 w=Path(os.environ['GITHUB_WORKSPACE']);out=w/'cloud-preflight-records';out.mkdir(exist_ok=True)
 r={'product_compiled':False,'product_executed':False,'archive_id':13750286693}
 try:
  manifests=list((w/'saved-checkpoint').rglob('manifest.json'));assert len(manifests)==1
  m=json.loads(manifests[0].read_text());a=manifests[0].parent/'build-state.tar.gz'
  with a.open('rb') as f:d=hashlib.file_digest(f,'sha256').hexdigest()
  assert d==ARCHIVE==m['archive_sha256'];r['archive_sha256']=d;r['identity']=m['identity']
  rows=m['rows'];r['object_count']=sum(n.endswith('.o') for n in rows)
  r['cloud_objects']=[n for n in rows if n.endswith(('/s3_store.cpp.o','/s3_client.cpp.o','/modelnet_cloud_tests.cpp.o'))]
  r['unit_test_objects']=[n for n in rows if n.endswith('.o') and ('/test/' in n or 'test_btx.dir/' in n)]
  wanted=['gui-pilot-runtime/qtbuild/CMakeCache.txt','gui-pilot-runtime/qtbuild/build.ninja']
  wanted+=['product/'+p for p in json.loads((Path(__file__).parent/'source-hashes.json').read_text())]
  data={}
  with tarfile.open(a) as t:
   for member in t:
    if member.name not in wanted:continue
    assert member.isfile() and member.size<20*1024**2
    b=t.extractfile(member).read();assert hashlib.sha256(b).hexdigest()==rows[member.name]['sha256']
    data[member.name]=b
  assert set(wanted)==set(data)
  expected=json.loads((Path(__file__).parent/'source-hashes.json').read_text())
  r['cloud_source_sha256']={p:hashlib.sha256(data['product/'+p]).hexdigest() for p in expected}
  assert r['cloud_source_sha256']==expected
  cache=data[wanted[0]].decode();ninja=data[wanted[1]].decode()
  r['configuration']=[l for l in cache.splitlines() if re.match(r'(BUILD_TEST|BUILD_GUI|ENABLE_WALLET|WITH_MODELNET|CMAKE_(BUILD_TYPE|CXX_COMPILER|C_COMPILER)|OPENSSL)',l)]
  r['unit_target_present']=any(l.startswith('build ') and ('test_btx:' in l or 'bin/test_btx:' in l) for l in ninja.splitlines())
  r['cloud_test_target_present']='modelnet_cloud_tests.cpp.o:' in ninja
  r['ready_for_existing_unit_target']=r['unit_target_present'] and r['cloud_test_target_present'] and bool(r['unit_test_objects'])
  r['next']='Inspect a small component consumer using the cached production objects; normal unit target is not retained.' if not r['ready_for_existing_unit_target'] else 'Restore isolated cache and dry-plan the unit target before compile.'
  r['inspection_pass']=True
 except Exception as e:r['inspection_pass']=False;r['error']=repr(e)
 finally:(out/'result.json').write_text(json.dumps(r,indent=2)+'\n')
 return 0 if r['inspection_pass'] else 1
if __name__=='__main__':raise SystemExit(main())
