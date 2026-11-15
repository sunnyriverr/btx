from pathlib import Path
import json,zipfile,urllib.request,shutil,os
import run as c
W,S,R,F=c.W,c.S,c.R,c.F
HEAD='949a98e34222cc4cdb5b1d5bd650aa3b7bcbff72'

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
