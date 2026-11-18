import json,hashlib,os,tarfile,zipfile,urllib.request,urllib.parse
from pathlib import Path
w=Path(os.environ['GITHUB_WORKSPACE']);out=w/'records';out.mkdir(exist_ok=True);r={'complete':False};expected=json.loads(Path('proposal/inputs.json').read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
class Redirect(urllib.request.HTTPRedirectHandler):
 def redirect_request(self,req,fp,code,msg,headers,url):
  x=super().redirect_request(req,fp,code,msg,headers,url)
  if urllib.parse.urlsplit(url).netloc!=urllib.parse.urlsplit(req.full_url).netloc:x.remove_header('Authorization')
  return x
try:
 archive=w/'saved.zip';req=urllib.request.Request(f"https://api.github.com/repos/sunnyriverr/btx/actions/artifacts/{expected['artifact']}/zip",headers={'Authorization':'Bearer '+os.environ['GH_TOKEN'],'User-Agent':'btx-funding-result-observation'})
 h=hashlib.sha256();size=0
 with urllib.request.build_opener(Redirect()).open(req,timeout=90)as src,archive.open('wb')as dst:
  while block:=src.read(1<<20):size+=len(block);assert size<=expected['zip_bytes'];h.update(block);dst.write(block)
 assert size==expected['zip_bytes']and h.hexdigest()==expected['zip_sha256']
 saved=w/'saved';saved.mkdir()
 with zipfile.ZipFile(archive)as z:
  assert set(z.namelist())=={'manifest.json','build-state.tar.gz'}
  z.extractall(saved)
 archive.unlink();m=json.loads((saved/'manifest.json').read_text());tar=saved/'build-state.tar.gz';assert sha(tar)==expected['archive_sha256'];assert m['identity']['source']==expected['source']
 from checkpoint import restore_timestamps,verify_restored
 with tarfile.open(tar)as t:t.extractall(w,filter='data')
 restore_timestamps(w,m);verify_restored(w,m)
 cache=(w/'gui-pilot-runtime/qtbuild/CMakeCache.txt').read_text();assert 'ENABLE_WALLET:BOOL=ON'in cache and 'WITH_MODELNET:BOOL=ON'in cache and 'WITH_SQLITE:BOOL=ON'in cache
 # Stored local source comparison was verified against live current refs before
 # dispatch; enforce the exact same GitHub blobs again at execution admission.
 hdr={'Authorization':'Bearer '+os.environ['GH_TOKEN'],'User-Agent':'btx-funding-source-admission'}
 def api(p):
  with urllib.request.urlopen(urllib.request.Request('https://api.github.com'+p,headers=hdr),timeout=40)as f:return json.load(f)
 head=api('/repos/btxchain/btx/branches/release-0.34.17')['commit']['sha'];assert head=='a97af7b3f379e33e3ec65db948468d875ade2841'
 rows={}
 for path in ['src/rpc/modelnet.cpp','src/wallet/rpc/transactions.cpp','src/rpc/util.cpp','src/rpc/util.h','src/wallet/model_funding.cpp','test/functional/wallet_modelnet_funding.py']:
  old=api('/repos/btxchain/btx/contents/'+path+'?ref='+expected['source'])['sha'];cur=api('/repos/btxchain/btx/contents/'+path+'?ref='+head)['sha'];assert old==cur;rows[path]=cur
 r.update(complete=True,source_files_match_current=True,source=expected['source'],current=head,blob_ids=rows,node_sha256=sha(w/'gui-pilot-runtime/qtbuild/bin/btxd'),artifact=expected['artifact'],profile_candidate=True,build=False)
finally:(out/'staging.json').write_text(json.dumps(r,indent=2)+'\n')
