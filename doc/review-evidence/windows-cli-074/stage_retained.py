from pathlib import Path
import os,sys,json,hashlib,zipfile,urllib.request,urllib.parse,io
W=Path(os.environ['GITHUB_WORKSPACE']);R=W/'records';R.mkdir();token=os.environ['GH_TOKEN']
class Redirect(urllib.request.HTTPRedirectHandler):
 def redirect_request(self,req,fp,code,msg,headers,url):
  q=super().redirect_request(req,fp,code,msg,headers,url)
  if q and urllib.parse.urlparse(url).netloc!='api.github.com':q.remove_header('Authorization')
  return q
req=urllib.request.Request('https://api.github.com/repos/sunnyriverr/btx/actions/artifacts/14151084362/zip',headers={'Authorization':'Bearer '+token,'User-Agent':'BTX-final-controls'})
with urllib.request.build_opener(Redirect).open(req,timeout=90) as f:b=f.read()
assert hashlib.sha256(b).hexdigest()=='05b406a64173d8aa1e45a93d660aa0990cd0f7e55022b84019871dfbf5d4e157'
z=zipfile.ZipFile(io.BytesIO(b));payload=z.read('archive/btx-0.34.16-x86_64-w64-mingw32.zip');assert hashlib.sha256(payload).hexdigest()=='e10c6c9432e28bebe392f931a1e10fe52dd2995878903be4e25e85b6e9475534'
root=W/'relocated archive';root.mkdir()
with zipfile.ZipFile(io.BytesIO(payload)) as a:
 for n in a.namelist():assert not Path(n).is_absolute() and '..' not in Path(n).parts
 a.extractall(root)
(R/'input-receipt.json').write_text(json.dumps({'artifact':14151084362,'outer_verified':True,'archive_sha256':hashlib.sha256(payload).hexdigest()},indent=2));print('Exact retained archive verified and extracted')
