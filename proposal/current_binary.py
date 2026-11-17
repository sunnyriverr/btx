"""Admit the exact current baseline helper from the completed qualification."""
from pathlib import Path
import hashlib,json,os,urllib.request,zipfile
import urllib.parse
class SafeRedirect(urllib.request.HTTPRedirectHandler):
 def redirect_request(self,req,fp,code,msg,headers,url):
  new=super().redirect_request(req,fp,code,msg,headers,url)
  if urllib.parse.urlsplit(req.full_url).netloc!=urllib.parse.urlsplit(url).netloc:new.remove_header('Authorization')
  return new
w=Path(os.environ['GITHUB_WORKSPACE']);out=w/'records';r={'complete':False,'artifact':14323625595};dest=w/'current-helper';dest.mkdir();zpath=w/'current-binaries.zip';h=hashlib.sha256();size=0
try:
 req=urllib.request.Request('https://api.github.com/repos/sunnyriverr/btx/actions/artifacts/14323625595/zip',headers={'Authorization':'Bearer '+os.environ['GH_TOKEN'],'User-Agent':'btx-progress-qualification'})
 with urllib.request.build_opener(SafeRedirect()).open(req,timeout=90)as src,zpath.open('wb')as f:
  while b:=src.read(1<<20):size+=len(b);assert size<=220*1024**2;h.update(b);f.write(b)
 assert size==212614116 and h.hexdigest()=='a8d145673094ac53ddcef159f55427a36e51d1e13ee25db78a96e717aff79f52'
 with zipfile.ZipFile(zpath)as z:
  names=z.namelist();assert 'baseline/btx-modeld'in names
  info=z.getinfo('baseline/btx-modeld');assert info.file_size<250*1024**2
  binary=dest/'btx-modeld'
  with z.open(info)as src,binary.open('wb')as f:
   while b:=src.read(1<<20):f.write(b)
 assert hashlib.sha256(binary.read_bytes()).hexdigest()=='adc65ed9645aa33ca4e6f067164ec824e3cc68ab59ef8c14084e6c989312b8dc';binary.chmod(0o755)
 r.update(complete=True,binary_sha256=hashlib.sha256(binary.read_bytes()).hexdigest(),artifact_zip_sha256=h.hexdigest(),source='cd3078e76398b20b7f500acd1348a5b5455f3d5e plus identical maintained cancellation regression; unpatched product helper')
finally:
 if zpath.exists():zpath.unlink()
 (out/'current-binary.json').write_text(json.dumps(r,indent=2)+'\n')
