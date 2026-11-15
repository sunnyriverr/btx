from pathlib import Path
import json,os,sys,shutil,tarfile,zipfile,urllib.request,traceback,importlib.util
import run as c
W,S,B,R,F=c.W,c.S,c.B,c.R,c.F
HEAD='949a98e34222cc4cdb5b1d5bd650aa3b7bcbff72'
c.EXECUTION_LIMIT=1800;c.STATE.update(base=HEAD,producer_source='f40eb37a6fb8b665340fe92a2f248ff3f23ec7f6',scope='Exact integrated949 Mac command-line archive, no product changes; bounded cached build and native package lifecycle')
def restore():
 meta=json.loads((F/'artifact-14137836649.json').read_text());out=W/'checkpoint.zip'
 class Redirect(urllib.request.HTTPRedirectHandler):
  def redirect_request(self,req,fp,code,msg,headers,url):
   q=super().redirect_request(req,fp,code,msg,headers,url)
   if q:q.remove_header('Authorization')
   return q
 req=urllib.request.Request('https://api.github.com/repos/sunnyriverr/btx/actions/artifacts/14137836649/zip',headers={'Authorization':'Bearer '+os.environ['GH_TOKEN'],'User-Agent':'BTX-integrated-archive'})
 print('START restore verified checkpoint',flush=True)
 with urllib.request.build_opener(Redirect).open(req,timeout=90) as response,out.open('wb') as dest:
  shutil.copyfileobj(response,dest,1024**2)
 assert 'sha256:'+c.sha(out)==meta['digest']
 payload=W/'producer';payload.mkdir()
 with zipfile.ZipFile(out) as z:
  for n in ('receipt.json','inventory.json','checkpoint.tar.gz'):(payload/n).write_bytes(z.read(n))
 receipt=json.loads((payload/'receipt.json').read_text());assert c.sha(payload/'checkpoint.tar.gz')==receipt['sha256'];inv=json.loads((payload/'inventory.json').read_text())
 count=0
 with tarfile.open(payload/'checkpoint.tar.gz') as t:
  for member in t:
   if not member.name.startswith('mac-config-build/'):continue
   assert not Path(member.name).is_absolute() and '..' not in Path(member.name).parts
   dest=W/member.name;meta=inv[member.name];assert dest.parent.resolve().is_relative_to(W.resolve())
   if member.isdir():dest.mkdir(parents=True,exist_ok=True);continue
   dest.parent.mkdir(parents=True,exist_ok=True)
   if member.issym():
    assert member.linkname==meta['target'] and (dest.parent/member.linkname).resolve().is_relative_to(W.resolve());dest.symlink_to(member.linkname);continue
   assert member.isfile();data=t.extractfile(member).read();assert __import__('hashlib').sha256(data).hexdigest()==meta['sha256'];dest.write_bytes(data);dest.chmod(meta['mode']);os.utime(dest,ns=(meta['mtime_ns'],meta['mtime_ns']));count+=member.name.endswith('.o')
 matched=0
 for name,meta in inv.items():
  dest=W/name
  if name.startswith('product/') and meta['type']=='file' and dest.is_file() and not dest.is_symlink() and c.sha(dest)==meta['sha256']:
   os.utime(dest,ns=(meta['mtime_ns'],meta['mtime_ns']));matched+=1
 c.STATE['restore']={'artifact':14137836649,'receipt':receipt,'objects':count,'matched_source_mtimes':matched};c.save();print('END restore '+str(count)+' objects',flush=True)

def main():
 assert shutil.disk_usage(W).free>15*1024**3
 _,head=c.cmd(['git','-C',S,'rev-parse','HEAD'],'source',30);assert head.strip()==HEAD
 c.cmd(['xcodebuild','-version'],'xcode',30);_,compiler=c.cmd(['xcrun','clang++','--version'],'compiler',30);assert 'Apple clang version 17.0.0' in compiler
 _,sdk=c.cmd(['xcrun','--sdk','macosx','--show-sdk-version'],'sdk',30);assert sdk.strip()=='15.5'
 restore()
 c.cmd(['brew','install','--force-bottle','boost@1.85','libevent','zeromq','libomp','qt','qrencode','librsvg','libicns','python@3.12'],'cached-build-prerequisites',480)
 _,ssl=c.cmd(['brew','--prefix','openssl@3'],'openssl-prefix',30);ssl=Path(ssl.strip())
 for name,h in [('libssl.a','b1a96521d10e2ce59ece360814915ed33c0e65aa60f7a9844b8b94c5d048cc56'),('libcrypto.a','76304e70825b4522b15461ad29c9106db1eeb8d421a12a641c210dabb11ed375')]:assert c.sha(ssl/'lib'/name)==h,'Static dependency identity changed'
 _,prefix=c.cmd(['brew','--prefix','python@3.12'],'python-prefix',30);python=Path(prefix.strip())/'bin/python3.12'
 c.cmd([python,'-m','venv',W/'test-env'],'test-env',60);c.cmd([W/'test-env/bin/python','-m','pip','install','cryptography==46.0.4'],'fixture-crypto',180)
 c.cmd(['cmake','-S',S,'-B',B,'-DCMAKE_SUPPRESS_REGENERATION=ON','-DPython3_EXECUTABLE='+str(W/'test-env/bin/python')],'configure-current',180)
 targets=['btxd','btx-cli','btx-util','btx-modeld','btx-hcpd','btx-hosted','btx-open','btx-capability','btx-capabilityd','btx-modelcheck','btx-matmul-backend-info','btx-security','btx-guardd','btx-tx','btx-wallet','btx-native-qualify']
 _,plan=c.cmd(['ninja','-C',B,'-n',*targets],'actual-incremental-plan',120);assert 'Re-running CMake' not in plan
 edges=sum(x.startswith('[') for x in plan.splitlines());c.STATE['build_admission']={'actual_edges':edges,'cap':80,'seconds_cap':600,'targets':targets};c.save();assert edges<=80,'Cache plan exceeds admitted80edges; checkpoint preserved, no full rebuild'
 c.cmd(['ninja','-C',B,'-j3',*targets],'bounded-current-build',600);c.STATE['btx_compiled']=True;c.STATE['binary_manifest']={n:c.sha(B/'bin'/n) for n in targets};shutil.copy2(B/'CMakeCache.txt',R/'CMakeCache.txt');c.save()
 # Incorporated packager only; no candidate script overlay.
 c.cmd([python,'-m','pip','install','--break-system-packages','cryptography==46.0.4'],'package-framework-crypto',180)
 _,base=c.cmd([python,'-c','import sys;print(sys.base_prefix)'],'framework-prefix',30);base=Path(base.strip()).resolve();framework=next(x for x in [base,*base.parents] if x.suffix=='.framework');assert framework.is_relative_to(Path('/opt/homebrew/Cellar/python@3.12'))
 metal=W/'metal-inputs';metal.mkdir();hashes={}
 for f in B.rglob('*.metallib'):
  h=c.sha(f);assert f.name not in hashes or hashes[f.name]==h;hashes[f.name]=h;shutil.copy2(f,metal/f.name)
 assert len(hashes)>=7
 out=W/'retained';out.mkdir(exist_ok=True)
 c.cmd([python,S/'scripts/release/package_release_archive.py','--output-dir',out,'--version','0.34.16','--platform-id','macos-arm64-metal','--btxd',B/'bin/btxd','--btx-cli',B/'bin/btx-cli','--btx-util',B/'bin/btx-util','--require-model-helpers','--metal-lib-dir',metal,'--source-root',S,'--python',python],'incorporated-archive-assembly',300)
 archive=next(out.glob('*.tar.gz'));c.STATE['archive']={'path':archive.name,'sha256':c.sha(archive),'bytes':archive.stat().st_size,'source':HEAD};c.save()
 relocated=W/'relocated current archive with spaces';relocated.mkdir()
 with tarfile.open(archive) as t:t.extractall(relocated,filter='data')
 root=next(x for x in relocated.iterdir() if x.is_dir())
 c.cmd([python,S/'scripts/release/verify_release_btxd.py','--archive',archive],'actual-archive-release-gate',180)
 c.cmd([python,F/'clean-audit.py',root,S,R],'all-image-audit',180)
 hidden=W/'producer-source-hidden'
 try:
  S.rename(hidden);c.cmd(['/usr/bin/python3',F/'archive-runtime.py',root,framework,R/'archive-runtime'],'producer-hidden-lifecycle',180)
 finally:
  hp=framework.with_name(framework.name+'.producer-hidden')
  if hp.exists() and not framework.exists():hp.rename(framework)
  if hidden.exists() and not S.exists():hidden.rename(S)
 assert framework.is_dir() and S.is_dir();c.STATE['producer_restored']=True
 c.STATE['audit']=json.loads((R/'archive-audit.json').read_text());c.STATE['lifecycle']=json.loads((R/'archive-runtime/lifecycle.json').read_text());c.STATE['source_dirty']=c.cmd(['git','-C',S,'status','--porcelain'],'final-source-status',30)[1];assert not c.STATE['source_dirty'];c.STATE['complete']=True;c.save()
try:main()
except Exception as e:c.STATE['error']=str(e);(R/'exception.txt').write_text(traceback.format_exc())
finally:c.save()
sys.exit(0 if c.STATE['complete'] else 1)
