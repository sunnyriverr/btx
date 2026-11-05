"""Exact-source/profile checkpoint: validate bytes before restoring source mtimes."""
from pathlib import Path
import json,hashlib,os

def digest(path):
 h=hashlib.sha256()
 with Path(path).open('rb') as stream:
  for chunk in iter(lambda:stream.read(1024*1024),b''):h.update(chunk)
 return h.hexdigest()

def checked(root,name):
 path=Path(root)/name
 if Path(name).is_absolute() or '..' in Path(name).parts or not path.resolve().is_relative_to(Path(root).resolve()):raise ValueError('Unsafe checkpoint path')
 return path

def restore(root,source,profile,catalog):
 root=Path(root);source=Path(source);marker=root/'project-build/btx-checkpoint.json'
 if not marker.exists():
  if(root/'project-build/CMakeCache.txt').exists():raise ValueError('Restored build has no verified checkpoint')
  return {'restored':False,'reason':'No exact checkpoint'}
 j=json.loads(marker.read_text())
 if j['profile']!=profile or j['source_catalog']!=catalog:raise ValueError('Checkpoint source/profile mismatch')
 current={str(path.relative_to(root))for folder in ['project-build','vcpkg-installed']for path in(root/folder).rglob('*')if path.is_file()and not path.is_symlink()and path.name!='btx-checkpoint.json'}
 if current!=set(j['files']):raise ValueError('Checkpoint file set mismatch')
 for name,info in j['files'].items():
  path=checked(root,name)
  if not path.is_file()or digest(path)!=info['sha256']:raise ValueError('Checkpoint file mismatch: '+name)
 expected={name for name,info in catalog['files'].items()if info['git_mode']!='120000'}
 if set(j['source_mtimes'])!=expected:raise ValueError('Checkpoint source timestamps incomplete')
 for name,stamp in j['source_mtimes'].items():
  path=checked(source,name)
  if path.is_symlink()or digest(path)!=catalog['files'][name]['working_sha256']:raise ValueError('Checkout bytes differ: '+name)
 # All validation precedes the first timestamp mutation.
 for name,stamp in j['source_mtimes'].items():
  path=checked(source,name);os.utime(path,ns=(path.stat().st_atime_ns,stamp))
 return {'restored':True,'files_verified':len(j['files']),'source_timestamps_restored':len(j['source_mtimes']),'previous_result':j['result']}

def capture(root,source,profile,catalog,result):
 root=Path(root);source=Path(source);build=root/'project-build'
 if not(build/'CMakeCache.txt').exists():raise ValueError('No configured project checkpoint')
 files={}
 for folder in ['project-build','vcpkg-installed']:
  for path in (root/folder).rglob('*'):
   if path.is_file() and not path.is_symlink() and path.name!='btx-checkpoint.json':files[str(path.relative_to(root))]={'sha256':digest(path),'bytes':path.stat().st_size}
 mtimes={}
 for name,info in catalog['files'].items():
  if info['git_mode']=='120000':continue
  path=checked(source,name)
  if path.is_symlink()or digest(path)!=info['working_sha256']:raise ValueError('Source changed before checkpoint: '+name)
  mtimes[name]=path.stat().st_mtime_ns
 j={'profile':profile,'source_catalog':catalog,'source_mtimes':mtimes,'files':files,'result':result};marker=build/'btx-checkpoint.json';marker.write_text(json.dumps(j,indent=2)+'\n');return {'files':len(files),'bytes':sum(x['bytes']for x in files.values()),'manifest_sha256':digest(marker)}
