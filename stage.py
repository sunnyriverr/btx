import json,os,urllib.request,urllib.parse,hashlib,io,zipfile
from pathlib import Path
p=Path('records');p.mkdir(exist_ok=True)
class Safe(urllib.request.HTTPRedirectHandler):
 def redirect_request(self,r,fp,code,msg,h,u):
  x=super().redirect_request(r,fp,code,msg,h,u)
  if x and urllib.parse.urlsplit(u).netloc!='api.github.com':x.remove_header('Authorization')
  return x
req=urllib.request.Request('https://api.github.com/repos/sunnyriverr/btx/actions/artifacts/14197632521/zip',headers={'Authorization':'Bearer '+os.environ['GH_TOKEN'],'User-Agent':'BTX737'})
b=urllib.request.build_opener(Safe()).open(req,timeout=90).read(40*1024**2)
assert hashlib.sha256(b).hexdigest()=='98cafbfe2451ae5cd94256a8f438775a063842c91c89549697911a4bac6aece3'
with zipfile.ZipFile(io.BytesIO(b)) as z:
 names=z.namelist();assert 'baseline/btx-modeld' in names,names
 data=z.read('baseline/btx-modeld')
 assert hashlib.sha256(data).hexdigest()=='cb783882585291c6ab7d5f0796129336d36dc3963be3db2310bbd25fe6737eae'
 out=Path('binary/baseline/btx-modeld');out.parent.mkdir(parents=True,exist_ok=True);out.write_bytes(data);out.chmod(0o755)
(p/'binary-identity.json').write_text(json.dumps({'artifact':14197632521,'artifact_sha256':hashlib.sha256(b).hexdigest(),'helper_sha256':hashlib.sha256(data).hexdigest(),'source':'1e2f8b5f12295002334d3390c12cac0bb4ae2aff','build_producer':'e92ff5d6f7590b4420f908e083f8f4200b7521e4','baseline_not_governor_candidate':True},indent=2))
