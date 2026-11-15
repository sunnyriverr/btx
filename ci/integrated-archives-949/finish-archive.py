from pathlib import Path
import json,os,sys,shutil,tarfile,zipfile,urllib.request,traceback,importlib.util
import run as c
W,S,B,R,F=c.W,c.S,c.B,c.R,c.F
HEAD='949a98e34222cc4cdb5b1d5bd650aa3b7bcbff72'
c.EXECUTION_LIMIT=1800;c.STATE.update(base=HEAD,producer_source='f40eb37a6fb8b665340fe92a2f248ff3f23ec7f6',scope='Exact integrated949 Mac command-line archive, no product changes; bounded cached build and native package lifecycle')
c.STATE['btx_compiled']=False
c.STATE['scope']='Remaining gates on the exact current949 actual archive; no compile, repack or passed-control repetition'
def restore():
 meta=json.loads((F/'artifact-14147748488.json').read_text());out=W/'archive-artifact.zip'
 class Redirect(urllib.request.HTTPRedirectHandler):
  def redirect_request(self,req,fp,code,msg,headers,url):
   q=super().redirect_request(req,fp,code,msg,headers,url)
   if q:q.remove_header('Authorization')
   return q
 req=urllib.request.Request('https://api.github.com/repos/sunnyriverr/btx/actions/artifacts/14147748488/zip',headers={'Authorization':'Bearer '+os.environ['GH_TOKEN'],'User-Agent':'BTX-integrated-archive'})
 with urllib.request.build_opener(Redirect).open(req,timeout=90) as response,out.open('wb') as dest:shutil.copyfileobj(response,dest,1024**2)
 assert 'sha256:'+c.sha(out)==meta['digest']
 retained=W/'retained';retained.mkdir()
 with zipfile.ZipFile(out) as z:
  name='btx-0.34.16-arm64-apple-darwin.tar.gz';assert name in z.namelist();archive=retained/name;archive.write_bytes(z.read(name))
 assert archive.stat().st_size==46410625 and c.sha(archive)=='22ee49b866f7d1539387d7e30bc82b38174b0925e84a103f590d92485569de73'
 c.STATE['archive']={'path':name,'sha256':c.sha(archive),'bytes':archive.stat().st_size,'source':HEAD,'producer_run':43679603417,'unchanged_saved_archive':True};c.save();return archive

def main():
 assert shutil.disk_usage(W).free>15*1024**3
 _,head=c.cmd(['git','-C',S,'rev-parse','HEAD'],'source',30);assert head.strip()==HEAD
 c.cmd(['xcodebuild','-version'],'xcode',30);_,compiler=c.cmd(['xcrun','clang++','--version'],'compiler',30);assert 'Apple clang version 17.0.0' in compiler
 _,sdk=c.cmd(['xcrun','--sdk','macosx','--show-sdk-version'],'sdk',30);assert sdk.strip()=='15.5'
 archive=restore()
 c.cmd(['brew','install','--force-bottle','python@3.12','libomp'],'package-prerequisites',480)
 _,prefix=c.cmd(['brew','--prefix','python@3.12'],'python-prefix',30);python=Path(prefix.strip())/'bin/python3.12'
 relocated=W/'relocated current archive with spaces';relocated.mkdir()
 with tarfile.open(archive) as t:t.extractall(relocated,filter='data')
 root=next(x for x in relocated.iterdir() if x.is_dir())
 apps=[str(x.relative_to(root)) for x in root.rglob('*.app')]
 assert apps==['lib/Python.framework/Versions/3.12/Resources/Python.app'],apps
 assert not (root/'btx-qt.app').exists();c.STATE['allowed_framework_app_resources']=apps
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
