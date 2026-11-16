"""Local receipt retrieval; credentials never written to evidence."""
import sys,json,pathlib,subprocess,urllib.request,urllib.parse,base64,hashlib,zipfile,io
sys.path.insert(0,'work/btx-review-tools/lan-linux-native/publication')
from api_util import api,REPO
run=int(sys.argv[1]);dest=pathlib.Path(sys.argv[2]);dest.mkdir(exist_ok=True)
a=next(x for x in api(f'/repos/sunnyriverr/btx/actions/runs/{run}/artifacts')['artifacts'] if x['name']=='modelnet-rehost-records')
(dest/'artifact.json').write_text(json.dumps(a,indent=2)+'\n')
c=subprocess.run(['git','credential','fill'],input='protocol=https\nhost=github.com\n\n',cwd=REPO,capture_output=True,text=True,check=True)
cred=dict(x.split('=',1) for x in c.stdout.splitlines() if '=' in x)
class Safe(urllib.request.HTTPRedirectHandler):
 def redirect_request(self,req,fp,code,msg,h,url):
  out=super().redirect_request(req,fp,code,msg,h,url)
  if urllib.parse.urlsplit(req.full_url).netloc!=urllib.parse.urlsplit(url).netloc:out.remove_header('Authorization')
  return out
req=urllib.request.Request(a['archive_download_url'],headers={'Authorization':'Basic '+base64.b64encode((cred['username']+':'+cred['password']).encode()).decode(),'User-Agent':'btx-review'})
data=urllib.request.build_opener(Safe()).open(req,timeout=60).read(8*1024**2)
assert 'sha256:'+hashlib.sha256(data).hexdigest()==a['digest']
with zipfile.ZipFile(io.BytesIO(data)) as z:
 assert sum(i.file_size for i in z.infolist())<16*1024**2
 for n in z.namelist():
  path=pathlib.Path(n);assert '..' not in path.parts and not path.is_absolute()
 z.extractall(dest)
print('Verified',a['id'],a['digest'])
for name in ('staging.json','virtual-execution.json','bounded-upload.json','framework-exit.txt'):
 if (dest/name).exists():print(name,(dest/name).read_text()[:5000])
