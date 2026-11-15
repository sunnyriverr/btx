from pathlib import Path
import json,subprocess,urllib.request,hashlib,tarfile,io,time,re
from datetime import datetime,timezone
r=Path(__file__).resolve().parent
def api(p):
 with urllib.request.urlopen(urllib.request.Request('https://api.github.com/'+p,headers={'User-Agent':'BTX-release-verification'}),timeout=30) as response:return json.load(response)
def signature(d):return [(x['id'],x['name'],x['size'],x.get('digest'),x['updated_at']) for x in d['assets']]
before=api('repos/btxchain/btx/releases/tags/v0.34.16');(r/'verification-release-before.json').write_text(json.dumps(before,indent=2)+'\n');assets={x['name']:x for x in before['assets']}
with urllib.request.urlopen(assets['SHA256SUMS']['browser_download_url'],timeout=30) as response:sums=response.read(65537)
assert len(sums)<=65536
mapping={}
for line in sums.decode().splitlines():
 m=re.fullmatch(r'([0-9a-f]{64})  ([A-Za-z0-9._-]+)',line);assert m,line;assert m[2] not in mapping;mapping[m[2]]=m[1]
assert set(mapping)=={n for n in assets if n.endswith('.tar.gz')}
(r/'verified-SHA256SUMS').write_bytes(sums)
class HashedReader:
 def __init__(self,stream):self.stream=stream;self.hash=hashlib.sha256();self.size=0
 def read(self,n=-1):
  b=self.stream.read(n);self.hash.update(b);self.size+=len(b);return b
results=[]
for name in ['btx-0.34.16-x86_64-linux-gnu.tar.gz','btx-0.34.16-x86_64-linux-gnu-cuda13.tar.gz']:
 a=assets[name];started=time.monotonic();inventory=[];metadata={};print('Reading '+name+' ('+str(a['size'])+' bytes)',flush=True)
 with urllib.request.urlopen(a['browser_download_url'],timeout=45) as response:
  stream=HashedReader(response)
  with tarfile.open(fileobj=stream,mode='r|gz',bufsize=65536) as archive:
   for member in archive:
    inventory.append({'path':member.name,'size':member.size,'type':member.type.decode('ascii',errors='replace'),'linkname':member.linkname})
    base=member.name.rsplit('/',1)[-1]
    if member.isfile() and base in ['btx-release-manifest.json','release-manifest.json','build-info.json','provenance.json','manifest.json','SHA256SUMS'] and len(metadata)<12:
     if member.size<=262144:metadata[member.name]=archive.extractfile(member).read().decode('utf-8',errors='replace')
  while stream.read(1024*1024):pass
 digest=stream.hash.hexdigest();assert stream.size==a['size'],(name,stream.size,a['size']);assert digest==mapping[name],name;assert a.get('digest')=='sha256:'+digest,name
 result={'asset':name,'asset_id':a['id'],'downloaded_bytes':stream.size,'sha256':digest,'matches_SHA256SUMS':True,'matches_github_digest':True,'elapsed_s':round(time.monotonic()-started,2),'tar_members':len(inventory),'embedded_metadata_paths':list(metadata)}
 (r/(name+'.inventory.json')).write_text(json.dumps(inventory,indent=2)+'\n');(r/(name+'.metadata.json')).write_text(json.dumps(metadata,indent=2)+'\n');results.append(result);print(json.dumps(result),flush=True)
 # Preserve each completed observation in case a later independent fetch fails.
 (r/'download-results-partial.json').write_text(json.dumps(results,indent=2)+'\n')
after=api('repos/btxchain/btx/releases/tags/v0.34.16');(r/'verification-release-after.json').write_text(json.dumps(after,indent=2)+'\n');assert signature(before)==signature(after),'Release assets changed during observation'
tag=api('repos/btxchain/btx/git/ref/tags/v0.34.16');obj=api('repos/btxchain/btx/git/tags/'+tag['object']['sha']) if tag['object']['type']=='tag' else tag;commit=obj['object']['sha'];assert commit=='074dac167c26c1e091198f691ed5727817dba88a'
receipt={'utc':datetime.now(timezone.utc).isoformat(),'results':results,'checksum_sha256':hashlib.sha256(sums).hexdigest(),'checksum_matches_github_digest':assets['SHA256SUMS'].get('digest')=='sha256:'+hashlib.sha256(sums).hexdigest(),'asset_metadata_stable_across_observation':True,'tag_commit':commit,'source_attribution':'Release notes and tag mapping; embedded metadata inspected separately. Not a reproducible-build proof.','signature_asset_present':any(x['name']=='SHA256SUMS.asc' for x in after['assets']),'binaries_executed':False,'archives_saved':False,'native_tests_run':False,'seed_work':False,'published':False};(r/'download-verification.json').write_text(json.dumps(receipt,indent=2)+'\n');print('COMPLETE',flush=True)
