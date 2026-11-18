"""Restore exact retained outputs. No compilation or product startup."""
import hashlib,json,os,subprocess,tarfile,urllib.request,urllib.parse,zipfile
from pathlib import Path
from checkpoint import restore_timestamps,verify_restored,sha
w=Path(os.environ['GITHUB_WORKSPACE']);out=w/'records';out.mkdir(exist_ok=True)
r={'complete':False,'native_execution':False,'artifact':14307015983}
def save():(out/'staging.json').write_text(json.dumps(r,indent=2)+'\n')
class SafeRedirect(urllib.request.HTTPRedirectHandler):
 def redirect_request(self,req,fp,code,msg,headers,url):
  x=super().redirect_request(req,fp,code,msg,headers,url)
  if urllib.parse.urlsplit(req.full_url).netloc!=urllib.parse.urlsplit(url).netloc:x.remove_header('Authorization')
  return x
try:
 req=urllib.request.Request('https://api.github.com/repos/sunnyriverr/btx/actions/artifacts/14307015983/zip',headers={'Authorization':'Bearer '+os.environ['GH_TOKEN'],'User-Agent':'btx-upload-staging'})
 archive=w/'checkpoint.zip';size=0;h=hashlib.sha256()
 with urllib.request.build_opener(SafeRedirect()).open(req,timeout=90) as src,archive.open('wb') as dest:
  while chunk:=src.read(1024*1024):
   size+=len(chunk);assert size<=600*1024**2;h.update(chunk);dest.write(chunk)
 assert size==524117435 and h.hexdigest()=='3c95a174d999673a005cbe467cd5d9196016d4ddb0e4ba161757049861b3552a'
 r['zip_sha256']=h.hexdigest();r['zip_bytes']=size;save()
 saved=w/'saved';saved.mkdir()
 with zipfile.ZipFile(archive) as z:
  assert sum(i.file_size for i in z.infolist())<3*1024**3
  for i in z.infolist():
   p=Path(i.filename);assert not p.is_absolute() and '..' not in p.parts and (i.external_attr>>16)&0o170000!=0o120000
  z.extractall(saved)
 archive.unlink()
 m=json.loads((saved/'manifest.json').read_text());tar=saved/'build-state.tar.gz'
 assert m['identity']['source']=='bd847e2b986722c1723b4cd60988d4f4908452d4'
 assert sha(tar)==m['archive_sha256'];assert m['workspace']==str(w)
 with tarfile.open(tar) as t:t.extractall(w,filter='data')
 restore_timestamps(w,m);verify_restored(w,m)
 helper=w/'gui-pilot-runtime/qtbuild/bin/btx-modeld'
 r['helper_sha256']=sha(helper)
 assert r['helper_sha256']=='ddbdfdfacbbf305f1a4e85f9e2ffbabefb79e43e3c260452162b6a4d525e85bf'
 r['composition']='release bd847e2b plus six-file verified-piece upload candidate;43cloudcases passed, collector repaired offline'
 for name,v in json.loads((w/'proposal/changes.json').read_text()).items():assert sha(w/'product'/name)==v['candidate_sha256'],name
 r['candidate_source_verified']=True
 r['manifest_files_verified']=len(m['rows']);r['complete']=True;save()
except Exception as e:r['error']=repr(e);save();raise
