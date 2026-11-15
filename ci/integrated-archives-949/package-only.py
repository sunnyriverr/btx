from pathlib import Path
import json,os,sys,shutil,tarfile,zipfile,urllib.request,traceback,importlib.util
import run as c
W,S,B,R,F=c.W,c.S,c.B,c.R,c.F
HEAD='949a98e34222cc4cdb5b1d5bd650aa3b7bcbff72'
c.EXECUTION_LIMIT=1800;c.STATE.update(base=HEAD,producer_source='f40eb37a6fb8b665340fe92a2f248ff3f23ec7f6',scope='Exact integrated949 Mac command-line archive, no product changes; bounded cached build and native package lifecycle')
c.STATE['btx_compiled']=False
c.STATE['scope']='Current949 exact saved binaries, incorporated packager with isolated CLI input inventory; no compile or GUI deployment'
def restore():
 meta=json.loads((F/'artifact-14146769329.json').read_text());out=W/'checkpoint.zip'
 class Redirect(urllib.request.HTTPRedirectHandler):
  def redirect_request(self,req,fp,code,msg,headers,url):
   q=super().redirect_request(req,fp,code,msg,headers,url)
   if q:q.remove_header('Authorization')
   return q
 req=urllib.request.Request('https://api.github.com/repos/sunnyriverr/btx/actions/artifacts/14146769329/zip',headers={'Authorization':'Bearer '+os.environ['GH_TOKEN'],'User-Agent':'BTX-integrated-archive'})
 print('START restore verified checkpoint',flush=True)
 with urllib.request.build_opener(Redirect).open(req,timeout=90) as response,out.open('wb') as dest:
  shutil.copyfileobj(response,dest,1024**2)
 assert 'sha256:'+c.sha(out)==meta['digest']
 payload=W/'producer';payload.mkdir()
 with zipfile.ZipFile(out) as z:
  for n in ('receipt.json','inventory.json','checkpoint.tar.gz'):(payload/n).write_bytes(z.read(n))
 receipt=json.loads((payload/'receipt.json').read_text());assert c.sha(payload/'checkpoint.tar.gz')==receipt['sha256'];inv=json.loads((payload/'inventory.json').read_text())
 inputs=W/'verified-current-inputs';inputs.mkdir()
 built=json.loads((F/'built949-manifest.json').read_text());assert built['source']==HEAD
 expected={'mac-config-build/bin/'+n:h for n,h in built['binaries'].items()};found=set();metal={}
 with tarfile.open(payload/'checkpoint.tar.gz') as t:
  for member in t:
   is_metal=member.name.startswith('mac-config-build/') and member.name.endswith('.metallib') and member.isfile()
   if member.name not in expected and not is_metal:continue
   assert member.isfile() and '..' not in Path(member.name).parts and not Path(member.name).is_absolute()
   data=t.extractfile(member).read();h=__import__('hashlib').sha256(data).hexdigest();assert h==inv[member.name]['sha256']
   if member.name in expected:
    assert h==expected[member.name];dest=inputs/'bin'/Path(member.name).name;found.add(member.name)
   else:
    name=Path(member.name).name;assert name not in metal or metal[name]==h;metal[name]=h;dest=inputs/'metal'/name
   dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(data);dest.chmod(member.mode)
 assert found==set(expected) and len(metal)>=7
 c.STATE['verified_inputs']={'source':HEAD,'producer_run':43678751599,'checkpoint':14146769329,'binary_hashes':built['binaries'],'metal':metal,'extracted_only_selected_commandline_files':True};c.save()
 return inputs

def main():
 assert shutil.disk_usage(W).free>15*1024**3
 _,head=c.cmd(['git','-C',S,'rev-parse','HEAD'],'source',30);assert head.strip()==HEAD
 c.cmd(['xcodebuild','-version'],'xcode',30);_,compiler=c.cmd(['xcrun','clang++','--version'],'compiler',30);assert 'Apple clang version 17.0.0' in compiler
 _,sdk=c.cmd(['xcrun','--sdk','macosx','--show-sdk-version'],'sdk',30);assert sdk.strip()=='15.5'
 inputs=restore()
 c.cmd(['brew','install','--force-bottle','python@3.12','libomp'],'package-prerequisites',480)
 _,prefix=c.cmd(['brew','--prefix','python@3.12'],'python-prefix',30);python=Path(prefix.strip())/'bin/python3.12'
 # Incorporated packager only; no candidate script overlay.
 c.cmd([python,'-m','pip','install','--break-system-packages','cryptography==46.0.4'],'package-framework-crypto',180)
 _,base=c.cmd([python,'-c','import sys;print(sys.base_prefix)'],'framework-prefix',30);base=Path(base.strip()).resolve();framework=next(x for x in [base,*base.parents] if x.suffix=='.framework');assert framework.is_relative_to(Path('/opt/homebrew/Cellar/python@3.12'))
 metal=inputs/'metal'
 out=W/'retained';out.mkdir(exist_ok=True)
 c.cmd([python,S/'scripts/release/package_release_archive.py','--output-dir',out,'--version','0.34.16','--platform-id','macos-arm64-metal','--btxd',inputs/'bin/btxd','--btx-cli',inputs/'bin/btx-cli','--btx-util',inputs/'bin/btx-util','--require-model-helpers','--metal-lib-dir',metal,'--source-root',S,'--python',python],'incorporated-archive-assembly',300)
 archive=next(out.glob('*.tar.gz'));c.STATE['archive']={'path':archive.name,'sha256':c.sha(archive),'bytes':archive.stat().st_size,'source':HEAD};c.save()
 relocated=W/'relocated current archive with spaces';relocated.mkdir()
 with tarfile.open(archive) as t:t.extractall(relocated,filter='data')
 root=next(x for x in relocated.iterdir() if x.is_dir())
 assert not list(root.rglob('*.app')), 'CLI profile unexpectedly contains a GUI app'
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
