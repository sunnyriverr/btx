"""Restore exact retained outputs. No compilation or product startup."""
import hashlib,json,os,subprocess,tarfile,urllib.request,urllib.parse,zipfile
from pathlib import Path
from checkpoint import restore_timestamps,verify_restored,sha
w=Path(os.environ['GITHUB_WORKSPACE']);out=w/'records';out.mkdir(exist_ok=True)
r={'complete':False,'native_execution':False,'artifact':14383717783}
def save():(out/'staging.json').write_text(json.dumps(r,indent=2)+'\n')
class SafeRedirect(urllib.request.HTTPRedirectHandler):
 def redirect_request(self,req,fp,code,msg,headers,url):
  x=super().redirect_request(req,fp,code,msg,headers,url)
  if urllib.parse.urlsplit(req.full_url).netloc!=urllib.parse.urlsplit(url).netloc:x.remove_header('Authorization')
  return x
try:
 req=urllib.request.Request('https://api.github.com/repos/sunnyriverr/btx/actions/artifacts/14383717783/zip',headers={'Authorization':'Bearer '+os.environ['GH_TOKEN'],'User-Agent':'btx-upload-staging'})
 archive=w/'checkpoint.zip';size=0;h=hashlib.sha256()
 with urllib.request.build_opener(SafeRedirect()).open(req,timeout=90) as src,archive.open('wb') as dest:
  while chunk:=src.read(1024*1024):
   size+=len(chunk);assert size<=600*1024**2;h.update(chunk);dest.write(chunk)
 assert size==525065268 and h.hexdigest()=='3b416cca7c48d49b2ec711521deddb8120d2bd1896614be1571aa9c28543f92d'
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
 assert r['helper_sha256']=='a56c7e2f6fd02acb055ba46983609c2b77bcd887b1d65fa96fe131634eb93ac2'
 r['composition']='retained23ee plus progress857 candidate; cache only, full exact23ee reconciliation before repair build; separate verified28d7 baseline reused'
 assert m['identity']['helper_progress_candidate'] is True
 assert m['archive_sha256']=='5651559ef682d598fcb170a761840327a7a3b59a3fd49c195771dbb34753c6b2'
 r['candidate_source_verified']=True
 r['manifest_files_verified']=len(m['rows']);r['complete']=True;save()
except Exception as e:r['error']=repr(e);save();raise
