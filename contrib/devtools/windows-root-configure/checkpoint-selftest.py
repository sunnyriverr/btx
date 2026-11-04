from pathlib import Path
import tempfile,json,os
import checkpoint

def fixture(root):
 source=root/'source';source.mkdir();file=source/'a.cpp';file.write_text('const int value=3;\n');stamp=1600000000000000000;os.utime(file,ns=(stamp,stamp));build=root/'project-build';build.mkdir();(build/'CMakeCache.txt').write_text('source and profile\n');(build/'a.obj').write_bytes(b'object');installed=root/'vcpkg-installed';installed.mkdir();(installed/'dep.lib').write_bytes(b'library');profile={'source':'exact','compiler':'same','flags':['/MT']};catalog={'head':'exact','files':{'a.cpp':{'git_mode':'100644','git_blob':'fixed','working_sha256':checkpoint.digest(file)}}};checkpoint.capture(root,source,profile,catalog,{'status':'partial'});return source,file,profile,catalog,stamp
checks=[]
for case in ['restore','wrong-profile','wrong-catalog','source-change','object-change','missing-file','extra-file','unsafe-path']:
 with tempfile.TemporaryDirectory(prefix='btx-checkpoint-')as tmp:
  root=Path(tmp);source,file,profile,catalog,stamp=fixture(root);os.utime(file,ns=(stamp+1000000000,stamp+1000000000));before=file.stat().st_mtime_ns
  if case=='wrong-profile':profile={'source':'different'}
  elif case=='wrong-catalog':catalog={'head':'different','files':catalog['files']}
  elif case=='source-change':file.write_text('changed\n');before=file.stat().st_mtime_ns
  elif case=='object-change':(root/'project-build/a.obj').write_bytes(b'changed')
  elif case=='missing-file':(root/'project-build/a.obj').unlink()
  elif case=='extra-file':(root/'project-build/extra.obj').write_bytes(b'extra')
  elif case=='unsafe-path':
   marker=root/'project-build/btx-checkpoint.json';j=json.loads(marker.read_text());j['files']['../outside.obj']={'sha256':'bad'};marker.write_text(json.dumps(j))
  try:result=checkpoint.restore(root,source,profile,catalog);accepted=True
  except ValueError:accepted=False
  if case=='restore':assert accepted and result['restored'] and file.stat().st_mtime_ns==stamp
  else:assert not accepted and file.stat().st_mtime_ns==before,(case,accepted)
  checks.append(case)
print('CHECKPOINT_SELFTEST_PASS',len(checks),','.join(checks))
