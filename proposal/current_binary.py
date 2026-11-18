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
 archive=download(14379917861,15098153,'b85fd094d664a15d8a7c398887b927f48adad2da690fc4962b981e767314c23f','baseline-binary')
 binary=w/'current-helper/btx-modeld';binary.parent.mkdir()
 with zipfile.ZipFile(archive)as z:
  info=z.getinfo('baseline/btx-modeld');assert info.file_size<250*1024**2
  with z.open(info)as src,binary.open('wb')as dst:
   while b:=src.read(1<<20):dst.write(b)
 archive.unlink();binary.chmod(0o755);h=hashlib.sha256(binary.read_bytes()).hexdigest();assert h=='28d7ecb6c611e5676d85de7a64038bc7d07cd0b6b2fb2606390d5e6405838ad2'
 # Current-source applicability check, independent from binary provenance.
 headers={'Authorization':'Bearer '+os.environ['GH_TOKEN'],'User-Agent':'configured-acquisition'}
 def api(path):
  with urllib.request.urlopen(urllib.request.Request('https://api.github.com'+path,headers=headers),timeout=40)as f:return json.load(f)
 head=api('/repos/btxchain/btx/branches/release-0.34.17')['commit']['sha'];assert head=='a97af7b3f379e33e3ec65db948468d875ade2841','head moved; inspect before runtime'
 diff=api('/repos/btxchain/btx/compare/23ee567ea8a2d9cad8ca3264f8793e8371b3eb93...'+head)
 changed=[f['filename']for f in diff['files']];assert len(diff['files'])<300
 sensitive=('src/modelnet/','src/crypto/','src/util/','src/univalue/','src/modeld.cpp')
 assert not any(f.startswith(sensitive)for f in changed),'relevant source moved'
 r.update(complete=True,helper_sha256=h,producer_run=44198067492,binary_source='23ee567ea8a2d9cad8ca3264f8793e8371b3eb93',current_source=head,changed_files=changed,scope='Current relevant ModelNet source unchanged; retained23eehelper, not a freshcurrentbuild.')
finally:(out/'current-binary.json').write_text(json.dumps(r,indent=2)+'\n')
