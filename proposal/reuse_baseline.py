"""Reuse the verified current baseline binary and unchanged hydration controls."""
from pathlib import Path
import hashlib,json,os,urllib.request,urllib.parse,zipfile
w=Path(os.environ['GITHUB_WORKSPACE']);out=w/'records';r={'complete':False}
class SafeRedirect(urllib.request.HTTPRedirectHandler):
 def redirect_request(self,req,fp,code,msg,headers,url):
  new=super().redirect_request(req,fp,code,msg,headers,url)
  if urllib.parse.urlsplit(req.full_url).netloc!=urllib.parse.urlsplit(url).netloc:new.remove_header('Authorization')
  return new

def download(aid,size,expected,label):
 p=w/(label+'.zip');h=hashlib.sha256();n=0;req=urllib.request.Request(f'https://api.github.com/repos/sunnyriverr/btx/actions/artifacts/{aid}/zip',headers={'Authorization':'Bearer '+os.environ['GH_TOKEN'],'User-Agent':'btx-progress-reuse'})
 with urllib.request.build_opener(SafeRedirect()).open(req,timeout=90)as src,p.open('wb')as f:
  while b:=src.read(1<<20):n+=len(b);assert n<=size;h.update(b);f.write(b)
 assert n==size and h.hexdigest()==expected;return p
try:
 archive=download(14380831273,406012,'4debcdc3600584d63e890dad72a12119569ffe7f7d68424bdaf7011214db7835','prior-records')
 dest=out/'reused';dest.mkdir()
 with zipfile.ZipFile(archive)as z:
  assert sum(i.file_size for i in z.infolist())<25*1024**2
  for i in z.infolist():
   p=Path(i.filename);assert not p.is_absolute()and'..'not in p.parts and(i.external_attr>>16)&0o170000!=0o120000
  z.extractall(dest)
 archive.unlink();prior=json.loads((dest/'qualification.json').read_text());assert prior['source']=='23ee567ea8a2d9cad8ca3264f8793e8371b3eb93' and prior['tracked_current_verified']
 assert prior['retained_stream_controls']['executed']==23 and prior['retained_stream_controls']['exit']==0 and all(prior['retained_stream_source_matches'].values())
 assert prior['baseline_binaries']['btx-modeld']=='28d7ecb6c611e5676d85de7a64038bc7d07cd0b6b2fb2606390d5e6405838ad2'
 changes=json.loads((w/'proposal/repair-changes.json').read_text());assert prior['baseline_source']['src/modelnet/helper.cpp']==changes['src/modelnet/helper.cpp']['baseline_sha256']
 archive=download(14379917861,15098153,'b85fd094d664a15d8a7c398887b927f48adad2da690fc4962b981e767314c23f','prior-binary')
 binary=w/'baseline-helper/bin/btx-modeld';binary.parent.mkdir(parents=True)
 with zipfile.ZipFile(archive)as z:
  info=z.getinfo('baseline/btx-modeld');assert info.file_size<250*1024**2
  with z.open(info)as src,binary.open('wb')as f:
   while b:=src.read(1<<20):f.write(b)
 archive.unlink();binary.chmod(0o755);h=hashlib.sha256(binary.read_bytes()).hexdigest();assert h==prior['baseline_binaries']['btx-modeld']
 r.update(complete=True,helper_sha256=h,producer_run=44198067492,source=prior['source'],retained_stream_controls=prior['retained_stream_controls'],native_cases_reused=False)
finally:(out/'baseline-reuse.json').write_text(json.dumps(r,indent=2)+'\n')
