"""Hosted preparation only. Never launches a product executable or test case."""
import hashlib, io, json, os, pathlib, subprocess, sys, urllib.request, urllib.parse, zipfile, re
P=pathlib.Path
records=P('records');records.mkdir(exist_ok=True)
receipt={'native_execution':False,'artifacts':[],'imports':False,'status':'INCOMPLETE'}
def save():(records/'staging.json').write_text(json.dumps(receipt,indent=2)+'\n')
class SafeRedirect(urllib.request.HTTPRedirectHandler):
 def redirect_request(self,req,fp,code,msg,headers,url):
  out=super().redirect_request(req,fp,code,msg,headers,url)
  if urllib.parse.urlsplit(req.full_url).netloc!=urllib.parse.urlsplit(url).netloc:out.remove_header('Authorization')
  return out
try:
 for aid,digest,dest in [(14095850633,'60cdff188dcc6642125b7ebac17803c81c33bae21c109dfd41744198240305b7','.'),(14137827346,'295a95fb52da660bca4daeaf926805057d5af13641f95f5a1ae4cce6b80f250f','candidate')]:
  req=urllib.request.Request(f'https://api.github.com/repos/sunnyriverr/btx/actions/artifacts/{aid}/zip',headers={'Authorization':'Bearer '+os.environ['GH_TOKEN'],'User-Agent':'btx-staging'})
  data=urllib.request.build_opener(SafeRedirect()).open(req,timeout=60).read(80*1024**2);assert hashlib.sha256(data).hexdigest()==digest
  with zipfile.ZipFile(io.BytesIO(data)) as z:
   assert sum(i.file_size for i in z.infolist())<600*1024**2
   for i in z.infolist():
    name=P(i.filename);assert not name.is_absolute() and '..' not in name.parts and (i.external_attr>>16)&0o170000!=0o120000
   z.extractall(dest)
  receipt['artifacts'].append({'id':aid,'sha256':digest});save()
 import shutil,configparser
 shutil.copy2('candidate/btx-modeld','obj/bin/btx-modeld')
 for line in P('expected-binaries.sha256').read_text().splitlines():
  expected,name=line.split(None,1);assert hashlib.sha256(P(name).read_bytes()).hexdigest()==expected
 receipt['binary_hashes']='PASS';save()
 cfg=P('obj/test/config.ini');c=configparser.ConfigParser();c.read(cfg)
 c['environment']['SRCDIR']=str(P('product').resolve());c['environment']['BUILDDIR']=str(P('obj').resolve());c['environment']['RPCAUTH']=str(P('product/share/rpcauth/rpcauth.py').resolve())
 with cfg.open('w') as f:c.write(f)
 for name in ('source_files_cases.py','base_minio.py','validate_source_files.py'):shutil.copy2(name,'product/test/functional/'+name)
 # Import only: __main__ and all fixture methods remain uncalled.
 sys.path.insert(0,str(P('product/test/functional').resolve()))
 import source_files_cases
 assert source_files_cases.SourceFilesCases.__dict__.get('run_test') is not None
 assert source_files_cases.SourceFilesCases.__dict__.get('set_test_params') is not None
 receipt['imports']=True;save()
 # Inspect ELF headers/dependencies without invoking product executables or loader.
 for name in ('btxd','btx-cli','btx-modeld'):
  out=subprocess.run(['readelf','-d','obj/bin/'+name],capture_output=True,text=True,check=True,timeout=10)
  (records/(name+'-dynamic.txt')).write_text(out.stdout)
 needed=set()
 for file in records.glob('*-dynamic.txt'):needed.update(re.findall(r'\(NEEDED\)[^\n]*\[([^\]]+)\]',file.read_text()))
 cache=subprocess.run(['/sbin/ldconfig','-p'],capture_output=True,text=True,check=True,timeout=10).stdout
 for name in needed:
  matches=re.findall(r'=> (\S+)', '\n'.join(line for line in cache.splitlines() if line.strip().startswith(name+' ')))
  assert any(P(f).is_file() for f in matches), 'missing runtime library: '+name
 for name in ('btxd','btx-cli','btx-modeld'):
  path=P('obj/bin')/name;path.chmod(0o755);assert os.access(path,os.X_OK)
 receipt['runtime_libraries_resolved']=sorted(needed);receipt['execute_modes_prepared']=True
 receipt['status']='PASS';receipt['note']='No adapter/native method, BTX, MinIO, Docker container or validator tests executed.';save()
except Exception as exc:
 receipt['status']='FAIL_OR_BLOCKED';receipt['failure']=repr(exc);save();raise
