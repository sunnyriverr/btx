from pathlib import Path
import urllib.request,urllib.parse,hashlib,json,zipfile,tarfile,re,subprocess,os,shutil,time
r=Path('records');r.mkdir(exist_ok=True);start=time.monotonic();result={'tests_run':False,'BTX_binaries_executed':False,'compiled':False,'source_pin':'61f13b8870ed98c7b10db2e32c04fb647023f4ef'}
class Redirect(urllib.request.HTTPRedirectHandler):
 def redirect_request(self,req,fp,code,msg,headers,url):
  v=super().redirect_request(req,fp,code,msg,headers,url)
  if v and urllib.parse.urlparse(url).netloc!='api.github.com':v.remove_header('Authorization')
  return v
opener=urllib.request.build_opener(Redirect)
def get(path):
 req=urllib.request.Request('https://api.github.com/'+path,headers={'Authorization':'Bearer '+os.environ['GH_TOKEN'],'Accept':'application/vnd.github+json','User-Agent':'BTX-retention-verification'})
 return opener.open(req,timeout=90)
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(2**20),b''):h.update(b)
 return h.hexdigest()
def read(args):return subprocess.check_output(args,text=True,timeout=120)
try:
 assert shutil.disk_usage('.').free>15*2**30
 with get('repos/sunnyriverr/btx/actions/artifacts/14162310743') as f:meta=json.load(f)
 assert not meta['expired'] and meta['workflow_run']['id']==43713295880 and meta['size_in_bytes']==215980593
 with get('repos/sunnyriverr/btx/actions/artifacts/14162310743/zip') as f,Path('checkpoint.zip').open('wb') as out:shutil.copyfileobj(f,out)
 assert sha(Path('checkpoint.zip'))=='e1722e43e66be27d99e66e76f8c8cc9f11b910956c61f10769cbf84e91c58ca8'
 saved=Path('saved');saved.mkdir()
 with zipfile.ZipFile('checkpoint.zip') as z:
  assert set(z.namelist())=={'btxd','btx-cli','checkpoint.tar.gz','producer.json'}
  for n in z.namelist():(saved/n).write_bytes(z.read(n))
 prod=json.loads((saved/'producer.json').read_text());assert prod['source_identity']==result['source_pin'] and prod['status']=='BUILD_PASS'
 assert sha(saved/'checkpoint.tar.gz')=='6c5a136395948f43ee49d06768c5dd684aa91643373ce4d0200bce2bcab47829'
 assert str(Path.cwd())==prod['checkpoint']['root'];assert not Path('source').exists() and not Path('build').exists()
 with tarfile.open(saved/'checkpoint.tar.gz') as t:
  assert all(Path(m.name).parts[0] in ['source','build'] for m in t.getmembers());t.extractall('.',filter='data')
 for n,h in prod['binary_sha256'].items():assert sha(saved/n)==h and sha(Path('build/bin')/n)==h
 result['binary_sha256']=prod['binary_sha256'];result['restored_objects']=sum(1 for p in Path('build').rglob('*.o'));assert result['restored_objects']==725
 result['source_manifest_verified']=0;excluded=[];extra=[]
 for name,h in prod['source_files_sha256'].items():
  if name.startswith('.github/'):excluded.append(name);continue
  f=Path('source')/name;assert f.is_file() and sha(f)==h,name;result['source_manifest_verified']+=1
  reference=Path('reference-source')/name
  if reference.is_file():assert sha(reference)==h,'upstream mismatch '+name
  else:extra.append(name)
 tracked=read(['git','-C','reference-source','ls-files','-z']).split('\0');tracked=[x for x in tracked if x and not x.startswith('.github/')];result['upstream_tracked_files_verified']=0
 for n in tracked:
  f=Path('source')/n;ref=Path('reference-source')/n
  if ref.is_symlink():assert f.is_symlink() and os.readlink(f)==os.readlink(ref),n
  else:assert f.is_file() and sha(f)==sha(ref),n
  result['upstream_tracked_files_verified']+=1
 result['intentional_archive_exclusions']={'source/.git':'not retained','source/.github':len(excluded)};result['producer_extra_source_files']=extra
 cache=Path('build/CMakeCache.txt').read_text();assert 'CMAKE_HOME_DIRECTORY:INTERNAL='+str(Path('source').resolve()) in cache;assert 'BUILD_TESTS:BOOL=OFF' in cache
 config=Path('build/test/config.ini');assert config.is_file();(r/'config.ini').write_bytes(config.read_bytes());(r/'CMakeCache.txt').write_text(cache)
 result['remaining_dry_run']=read(['ninja','-C','build','-n','btxd','btx-cli']);(r/'remaining-dry-run.log').write_text(result['remaining_dry_run'])
 # Static ELF inspection and dependency resolution only. Never ldd or launch a BTX binary.
 ldc=read(['/sbin/ldconfig','-p']);(r/'ldconfig.log').write_text(ldc);libs={}
 for line in ldc.splitlines():
  m=re.match(r'\s*(\S+)\s+\(([^)]*)\)\s+=>\s+(\S+)',line)
  if m and 'x86-64' in m[2]:libs.setdefault(m[1],m[3])
 queue=[Path('build/bin/btxd').resolve(),Path('build/bin/btx-cli').resolve()];seen={};root_headers={};issues=[]
 while queue:
  path=queue.pop(0);key=str(path)
  if key in seen:continue
  program=read(['readelf','-l',key]);interpreter=re.search(r'Requesting program interpreter: ([^\]]+)',program)
  if interpreter:assert Path(interpreter[1]).is_file(),interpreter[1]
  dynamic=read(['readelf','-d',key]);versions=read(['readelf','-V',key]);header=read(['readelf','-h',key]);assert 'Advanced Micro Devices X86-64' in header
  needed=re.findall(r'\(NEEDED\).*\[(.*?)\]',dynamic);paths=re.findall(r'\((?:RUNPATH|RPATH)\).*\[(.*?)\]',dynamic);resolved={}
  for n in needed:
   candidates=[Path(p.replace('$ORIGIN',str(path.parent)))/n for group in paths for p in group.split(':') if p];target=next((str(x) for x in candidates if x.is_file()),libs.get(n));assert target and Path(target).is_file(),(key,n);resolved[n]=target;queue.append(Path(target).resolve())
  # Verify every named version need against that dependency's actual definition table.
  current=None
  needs=versions.split('Version needs section',1)[1] if 'Version needs section' in versions else ''
  for line in needs.splitlines():
   match=re.search(r'File: (\S+)',line)
   if match:current=match[1]
   match=re.search(r'Name: (\S+)',line)
   if match and current:
    provider=resolved[current];v=read(['readelf','-V',provider]);defs=v.split('Version definition section',1)[1].split('Version needs section',1)[0] if 'Version definition section' in v else '';assert match[1] in re.findall(r'Name: (\S+)',defs),(key,current,match[1])
  seen[key]={'needed':needed,'resolved':resolved,'runpaths':paths,'sha256':sha(path)}
  if path.name in ['btxd','btx-cli']:
   (r/(path.name+'.elf.txt')).write_text(header+read(['readelf','-l',key])+dynamic+versions);root_headers[path.name]=seen[key]
 result['ELF_dependencies']=seen;result['root_dependencies']=root_headers;result['status']='RESTORE_AND_STATIC_DEPENDENCIES_PASS';(r/'packages.log').write_text(read(['dpkg-query','-W','libsqlite3-0','libevent-2.1-7t64','libevent-pthreads-2.1-7t64','libssl3t64','libstdc++6']))
except BaseException as e:result.update(status='VERIFICATION_FAILED',error=str(e));raise
finally:
 result['elapsed_s']=round(time.monotonic()-start,2);result['runtime_limit']='Static ELF/SONAME/version closure on provisioned Ubuntu only; no loader/startup/RPC/proof tests';(r/'verification-result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if k not in ['ELF_dependencies','remaining_dry_run']},indent=2))
