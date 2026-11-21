"""Restore exact retained outputs. No compilation or product startup."""
import hashlib,json,os,subprocess,tarfile,urllib.request,urllib.parse,zipfile
from pathlib import Path
from checkpoint import restore_timestamps,verify_restored,sha
w=Path(os.environ['GITHUB_WORKSPACE']);out=w/'records';out.mkdir(exist_ok=True)
r={'complete':False,'native_execution':False,'artifact':14707154639}
def save():(out/'staging.json').write_text(json.dumps(r,indent=2)+'\n')
class SafeRedirect(urllib.request.HTTPRedirectHandler):
 def redirect_request(self,req,fp,code,msg,headers,url):
  x=super().redirect_request(req,fp,code,msg,headers,url)
  if urllib.parse.urlsplit(req.full_url).netloc!=urllib.parse.urlsplit(url).netloc:x.remove_header('Authorization')
  return x
try:
 req=urllib.request.Request('https://api.github.com/repos/sunnyriverr/btx/actions/artifacts/14707154639/zip',headers={'Authorization':'Bearer '+os.environ['GH_TOKEN'],'User-Agent':'btx-upload-staging'})
 assert not any((w/name).exists() for name in ('product','gui-pilot-runtime','saved','checkpoint.zip'))
 archive=w/'checkpoint.zip';size=0;h=hashlib.sha256()
 with urllib.request.build_opener(SafeRedirect()).open(req,timeout=90) as src,archive.open('wb') as dest:
  while chunk:=src.read(1024*1024):
   size+=len(chunk);assert size<=600*1024**2;h.update(chunk);dest.write(chunk)
 assert size==563352653 and h.hexdigest()=='f33df5cbed3f630d3cc331ad1f00446ec6a4a26a13dbb2deec2ac4f6a9076130'
 r['zip_sha256']=h.hexdigest();r['zip_bytes']=size;save()
 saved=w/'saved';saved.mkdir()
 with zipfile.ZipFile(archive) as z:
  assert sum(i.file_size for i in z.infolist())<3*1024**3
  for i in z.infolist():
   p=Path(i.filename);assert not p.is_absolute() and '..' not in p.parts and (i.external_attr>>16)&0o170000!=0o120000
  z.extractall(saved)
 archive.unlink()
 m=json.loads((saved/'manifest.json').read_text());tar=saved/'build-state.tar.gz'
 assert m['identity']['source']=='2c4da891f0089ebc0fb082e65d03a4efda4488a3'
 assert m['identity']['target_build_complete'] is True
 assert m['identity']['ninja_exit']==0 and m['identity']['targets']==['btxd','btx-cli']
 assert len(m['rows'])==23890
 assert sha(tar)==m['archive_sha256']=='9c982b364a708389c9edc503475feeae16ba9d93d83e1937b3e4efb554309df4'
 assert m['workspace']==str(w)
 with tarfile.open(tar) as t:t.extractall(w,filter='data')
 restore_timestamps(w,m);verify_restored(w,m)
 subprocess.run(['sha256sum','--check',str(w/'proposal/retained-binaries.sha256')],check=True)
 r['inner_sha256']=m['archive_sha256']
 r['retained_source']=m['identity']['source']
 r['retained_objects']=sum(n.endswith('.o') and row['kind']=='file' for n,row in m['rows'].items())
 assert r['retained_objects']==6001
 r['manifest_files_verified']=len(m['rows']);r['complete']=True;save()
except Exception as e:r['error']=repr(e);save();raise
