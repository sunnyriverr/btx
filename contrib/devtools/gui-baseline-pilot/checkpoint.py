"""Checkpoint private build state; no product package, credentials or production paths."""
from pathlib import Path
import hashlib,json,os,shutil,tarfile
ROOTS=('product','gui-pilot-runtime/qtbuild','gui-pilot-runtime/openssl')
def sha(path):
 h=hashlib.sha256()
 with path.open('rb') as f:
  for block in iter(lambda:f.read(1024*1024),b''):h.update(block)
 return h.hexdigest()
def snapshot(workspace):
 rows={}
 for name in ROOTS:
  root=workspace/name
  if not root.exists():continue
  for p in [root,*root.rglob('*')]:
   rel=p.relative_to(workspace)
   if '.git' in rel.parts:continue
   st=p.lstat();row={'mtime_ns':st.st_mtime_ns,'mode':st.st_mode & 0o777}
   if p.is_symlink():
    target=os.readlink(p)
    assert not Path(target).is_absolute() and (p.parent/target).resolve().is_relative_to(workspace.resolve()),'Link escapes checkpoint workspace: '+str(rel)+' -> '+target
    row.update(kind='link',target=target)
   elif p.is_file():row.update(kind='file',sha256=sha(p),bytes=st.st_size)
   elif p.is_dir():row['kind']='directory'
   else:raise ValueError('Unexpected special file')
   rows[str(rel)]=row
 return rows

def create(workspace,output,identity,reserve=2*1024**3):
 workspace=workspace.resolve();output.mkdir(exist_ok=False)
 before=snapshot(workspace);assert before
 total=sum(x.get('bytes',0) for x in before.values())
 # Conservative uncompressed allowance; never assume a compression ratio.
 assert shutil.disk_usage(output).free>total+reserve,'Insufficient checkpoint headroom'
 archive=output/'build-state.tar.gz';manifest={'identity':identity,'workspace':str(workspace),'rows':before}
 def include(info):
  return None if '.git' in Path(info.name).parts else info
 with tarfile.open(archive,'w:gz',compresslevel=1,format=tarfile.PAX_FORMAT) as t:
  for name in ROOTS:
   if (workspace/name).exists():t.add(workspace/name,arcname=name,filter=include)
 assert snapshot(workspace)==before,'Build tree changed during checkpoint'
 manifest['archive_sha256']=sha(archive)
 (output/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
 return manifest

def verify_restored(workspace,manifest):
 assert snapshot(workspace)==manifest['rows'],'Checkpoint bytes/modes/links/timestamps differ'

def restore_timestamps(workspace,manifest):
 # Tar/PAX float timestamps can lose nanoseconds; first prove all other identity.
 actual=snapshot(workspace)
 assert set(actual)==set(manifest['rows'])
 for name,row in actual.items():
  assert {k:v for k,v in row.items() if k!='mtime_ns'}=={k:v for k,v in manifest['rows'][name].items() if k!='mtime_ns'}
 for name,row in sorted(manifest['rows'].items(),key=lambda item:len(Path(item[0]).parts),reverse=True):
  os.utime(workspace/name,ns=(row['mtime_ns'],row['mtime_ns']),follow_symlinks=False)
