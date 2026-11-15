from pathlib import Path
import hashlib,json,subprocess,os,urllib.request,zipfile,shutil
root=Path.cwd();r=root/'records'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
# The restoration verifier already checked every upstream source byte before overlays.
prod=json.loads((root/'saved/producer.json').read_text());assert prod['source_identity']=='1e2f8b5f12295002334d3390c12cac0bb4ae2aff'
shutil.copytree(root/'reference-source/.git',root/'source/.git')
files={}
for name in ['test_runner.py','wallet_seed_pruned_recovery.py']:
 src=root/'suite-inputs'/name;dst=root/'source/test/functional'/name
 dst.write_bytes(src.read_bytes());files[name]=sha(dst)
# Explicit normal configure creates the test symlink, without compiling BTX.
with (r/'suite-configure.log').open('w') as log:
 subprocess.run(['cmake','-S','source','-B','build'],stdout=log,stderr=subprocess.STDOUT,check=True,timeout=240)
for n,h in prod['binary_sha256'].items():assert sha(root/'build/bin'/n)==h
assert (root/'build/test/functional/wallet_seed_pruned_recovery.py').is_file()
# Old, independently qualified executable pair supplies an observational control only.
from importlib.machinery import SourceFileLoader
# Reuse the verifier's authenticated, redirect-safe download helper without importing its top-level execution.
class Redirect(urllib.request.HTTPRedirectHandler):
 def redirect_request(self,req,fp,code,msg,headers,url):
  v=super().redirect_request(req,fp,code,msg,headers,url)
  if v and urllib.parse.urlparse(url).netloc!='api.github.com':v.remove_header('Authorization')
  return v
req=urllib.request.Request('https://api.github.com/repos/sunnyriverr/btx/actions/artifacts/14162310743/zip',headers={'Authorization':'Bearer '+os.environ['GH_TOKEN'],'User-Agent':'BTX recovery qualification'})
with urllib.request.build_opener(Redirect).open(req,timeout=90) as response,(root/'old.zip').open('wb') as f:shutil.copyfileobj(response,f)
assert sha(root/'old.zip')=='e1722e43e66be27d99e66e76f8c8cc9f11b910956c61f10769cbf84e91c58ca8'
old=root/'old-bin';old.mkdir()
expected={'btxd':'92fc16404aa6021ab27757157771bbcaf0c595afba6d83e3daa63fc6ebbf644c','btx-cli':'ae63c2874a71ab213886d50f12fc6d4cfee7a3af40609feb5c377c4b2005dfcf'}
with zipfile.ZipFile(root/'old.zip') as z:
 for n,h in expected.items():
  p=old/n;p.write_bytes(z.read(n));assert sha(p)==h;p.chmod(0o755)
(root/'old.zip').unlink()
(r/'suite-inputs.json').write_text(json.dumps({'source':prod['source_identity'],'files':files,'current_binary_sha256':prod['binary_sha256'],'old_binary_sha256':expected,'configured_not_compiled':True},indent=2)+'\n')
