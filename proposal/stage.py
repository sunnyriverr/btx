"""Restore exact retained outputs. No compilation or product startup."""
import hashlib,json,os,subprocess,tarfile,urllib.request,urllib.parse,zipfile
from pathlib import Path
from checkpoint import restore_timestamps,verify_restored,sha
w=Path(os.environ['GITHUB_WORKSPACE']);out=w/'records';out.mkdir(exist_ok=True)
r={'complete':False,'native_execution':False,'artifact':14415017081}
def save():(out/'staging.json').write_text(json.dumps(r,indent=2)+'\n')
class SafeRedirect(urllib.request.HTTPRedirectHandler):
 def redirect_request(self,req,fp,code,msg,headers,url):
  x=super().redirect_request(req,fp,code,msg,headers,url)
  if urllib.parse.urlsplit(req.full_url).netloc!=urllib.parse.urlsplit(url).netloc:x.remove_header('Authorization')
  return x
try:
 req=urllib.request.Request('https://api.github.com/repos/sunnyriverr/btx/actions/artifacts/14415017081/zip',headers={'Authorization':'Bearer '+os.environ['GH_TOKEN'],'User-Agent':'btx-upload-staging'})
 archive=w/'checkpoint.zip';size=0;h=hashlib.sha256()
 with urllib.request.build_opener(SafeRedirect()).open(req,timeout=90) as src,archive.open('wb') as dest:
  while chunk:=src.read(1024*1024):
   size+=len(chunk);assert size<=600*1024**2;h.update(chunk);dest.write(chunk)
 assert size==554182681 and h.hexdigest()=='47252f0bef545425e5a9a6a86b99bb61398507d91233e508f4945d32066d52b7'
 r['zip_sha256']=h.hexdigest();r['zip_bytes']=size;save()
 saved=w/'saved';saved.mkdir()
 with zipfile.ZipFile(archive) as z:
  assert sum(i.file_size for i in z.infolist())<3*1024**3
  for i in z.infolist():
   p=Path(i.filename);assert not p.is_absolute() and '..' not in p.parts and (i.external_attr>>16)&0o170000!=0o120000
  z.extractall(saved)
 archive.unlink()
 m=json.loads((saved/'manifest.json').read_text());tar=saved/'build-state.tar.gz'
 assert m['identity']['source']=='23ee567ea8a2d9cad8ca3264f8793e8371b3eb93'
 assert sha(tar)==m['archive_sha256'];assert m['workspace']==str(w)
 with tarfile.open(tar) as t:t.extractall(w,filter='data')
 restore_timestamps(w,m);verify_restored(w,m)
 helper=w/'gui-pilot-runtime/qtbuild/bin/btx-modeld'
 r['helper_sha256']=sha(helper)
 assert r['helper_sha256']=='1aab62ac116bbc765f065e8d7a427f661d524a1306e31ae73fa6f89e6eb25497'
 r['composition']='Retained 23ee plus exact #861 composition and existing isolated test target'
 assert m['identity']['cloud_control_candidate'] is True and m['identity']['qualification_complete'] is True
 assert m['archive_sha256']=='26689e4012f3b7916fbbd6d382d3a8e2862ab471f96c3549e72838c06db2613e'
 r['candidate_source_verified']=True
 r['manifest_files_verified']=len(m['rows']);r['complete']=True;save()
except Exception as e:r['error']=repr(e);save();raise
