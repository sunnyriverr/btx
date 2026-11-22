"""Restore only exact retained binaries from a digest-pinned checkpoint; no build."""
import argparse,hashlib,json,os,shutil,tarfile,urllib.request,urllib.parse,zipfile
from pathlib import Path
ARTIFACT=14730598159
ZIP_BYTES=563328307
ZIP_SHA='2e87d1c890a04058c7f0dd0b12e7b5e27cbb34173e1b6db1c564f000678a3633'
INNER_SHA='64e9cd620d4567fe291f3f4e65497798358d975798348aec9c364f2c5596cbb7'
SOURCE='f9ba112822c0089ae2fc3bb5f71e1a28c7cf0302'
BINARY={'btxd':'4107e66f5122d69011337d342ebd30ff2eefdb4da3de75e6750fde099a750730',
        'btx-cli':'2db95cc3d8310876264eda6cfeed613173b7c8b60041db8e630b954e6af1a6b8'}
PREFIX='gui-pilot-runtime/qtbuild/bin/'

def digest(stream,target=None):
    h=hashlib.sha256();n=0
    for block in iter(lambda:stream.read(1024*1024),b''):
        h.update(block);n+=len(block)
        if target:target.write(block)
    return h.hexdigest(),n

class Redirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,req,fp,code,msg,headers,url):
        new=super().redirect_request(req,fp,code,msg,headers,url)
        if new and urllib.parse.urlparse(url).netloc!='api.github.com':new.remove_header('Authorization')
        return new

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True);parser.add_argument('--records',type=Path,required=True);a=parser.parse_args()
    a.output.mkdir(parents=True,exist_ok=False);a.records.mkdir(parents=True,exist_ok=True)
    assert shutil.disk_usage(a.output).free>3*1024**3
    token=os.environ['GH_TOKEN']
    opener=urllib.request.build_opener(Redirect)
    def request(suffix):
        return opener.open(urllib.request.Request('https://api.github.com/repos/sunnyriverr/btx/'+suffix,headers={'Authorization':'Bearer '+token,'User-Agent':'BTX-checkpoint-admission','Accept':'application/vnd.github+json'}),timeout=60)
    with request('actions/artifacts/'+str(ARTIFACT))as response:meta=json.load(response)
    assert meta['id']==ARTIFACT and not meta['expired'] and meta['size_in_bytes']==ZIP_BYTES and meta['digest']=='sha256:'+ZIP_SHA
    checkpoint=a.output/'checkpoint.zip'
    try:
        with request('actions/artifacts/'+str(ARTIFACT)+'/zip')as response,checkpoint.open('wb')as saved:
            h,size=digest(response,saved)
        assert (h,size)==(ZIP_SHA,ZIP_BYTES)
        with zipfile.ZipFile(checkpoint)as z:
            assert all(z.namelist().count(name)==1 for name in ['manifest.json','build-state.tar.gz'])
            manifest=json.loads(z.read('manifest.json'));assert manifest['archive_sha256']==INNER_SHA
            with z.open('build-state.tar.gz')as stream:assert digest(stream)[0]==INNER_SHA
            kept={}
            with z.open('build-state.tar.gz')as stream,tarfile.open(fileobj=stream,mode='r|gz')as archive:
                for member in archive:
                    if member.name not in {PREFIX+n for n in BINARY}:continue
                    assert member.isfile() and not member.issym() and not member.islnk()
                    name=Path(member.name).name;assert name not in kept
                    with archive.extractfile(member)as data,(a.output/name).open('wb')as dest:h,size=digest(data,dest)
                    assert h==BINARY[name];(a.output/name).chmod(0o755);kept[name]={'sha256':h,'bytes':size}
            assert set(kept)==set(BINARY)
        (a.records/'binary-restore.json').write_text(json.dumps({'status':'PASS','source':SOURCE,'artifact_id':ARTIFACT,'outer_sha256':ZIP_SHA,'inner_sha256':INNER_SHA,'binaries':kept,'compiled':False},indent=2)+'\n')
    finally:
        checkpoint.unlink(missing_ok=True)
if __name__=='__main__':main()
