import json,urllib.request,subprocess,re,hashlib,time
from pathlib import Path
R=Path(__file__).resolve().parent
H=R/'mingw-headers';H.mkdir(exist_ok=True)
commit='70d3f1ac8cffdb8ac48f4190da67aa295dddc8fd'
base='https://raw.githubusercontent.com/mingw-w64/mingw-w64/'+commit+'/mingw-w64-headers/'
manifest=[]
def fetch(name):
 if len(manifest)>=220: raise RuntimeError('220-header budget reached')
 for tree in ['include/','crt/','defaults/include/']:
  remote=('_mingw.h.in' if name=='_mingw.h' else name)
  url=base+tree+remote
  try:
   b=urllib.request.urlopen(url,timeout=12).read()
   if name=='_mingw.h':b=b.replace(b'@DEFAULT_MSVCRT_VERSION@',b'0xE00').replace(b'@DEFAULT_WIN32_WINNT@',b'0x0A00')
   if sum(x['bytes'] for x in manifest)+len(b)>20000000:raise RuntimeError('20MB budget')
   p=H/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b)
   manifest.append({'file':name,'url':url,'sha256':hashlib.sha256(b).hexdigest(),'bytes':len(b),'generated_defaults':name=='_mingw.h'})
   return
  except urllib.error.HTTPError as e:
   if e.code!=404:raise
 raise RuntimeError('No upstream header '+name)
shim=(R.parent/'toolchain-2026-10-31/source/src/compat/mingw/posix_extra.h').read_text()
# Exact Windows SDK preinclude + macro-removal section; omit later POSIX/C++ shims.
section=shim[shim.index('#ifndef WIN32_LEAN_AND_MEAN'):shim.index('#include <csignal>')]
probe=R/'probe.cpp';probe.write_text(section+'\n#include <mswsock.h>\nint main() { return 0; }\n')
cmd=['clang++','--target=x86_64-w64-windows-gnu','-std=c++20','-D_WIN32_WINNT=0x0A00','-DNOMINMAX','-fsyntax-only','-Wno-pragma-pack','-Wno-ignored-attributes','-I'+str(H),str(probe)]
results=[]
try:
 for i in range(221):
  p=subprocess.run(cmd,capture_output=True,text=True)
  m=re.search(r"fatal error: '([^']+)' file not found",p.stderr)
  if not m:
   results.append({'case':'late_header','exit':p.returncode,'stdout':p.stdout,'stderr':p.stderr});break
  name=m.group(1)
  if (H/name).exists():raise RuntimeError('existing missing header '+name)
  fetch(name)
  if i%15==0:print('Fetched',len(manifest),'genuine MinGW headers',flush=True)
 for label,body in [('no_new_header',section+'\nint main(){return 0;}\n'),('early_header',section.replace('#include <iphlpapi.h>','#include <iphlpapi.h>\n#include <mswsock.h>')+'\n#include <mswsock.h>\nint main(){return 0;}\n')]:
  f=R/(label+'.cpp');f.write_text(body);cp=cmd[:-1]+[str(f)]
  p=subprocess.run(cp,capture_output=True,text=True);results.append({'case':label,'exit':p.returncode,'stdout':p.stdout,'stderr':p.stderr})
except Exception as e:results.append({'error':str(e)})
(R/'header-probe-results.json').write_text(json.dumps({'commit':commit,'command':cmd,'scope':'Mac Clang Windows-target syntax-only against fetched genuine MinGW headers; exact SDK-prelude/undef slice of BTX shim. Not full shim/TU/link or native execution.','results':results},indent=2)+'\n')
(R/'downloaded-headers.json').write_text(json.dumps(manifest,indent=2)+'\n')
for x in results:print(json.dumps(x))
print('HEADERS',len(manifest),'BYTES',sum(x['bytes'] for x in manifest))
