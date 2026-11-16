"""Static ELF/SONAME/version closure, reused from the verified baseline reader."""
from pathlib import Path
import hashlib
import re
import subprocess

def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(2**20),b''):
            h.update(b)
    return h.hexdigest()

def read(argv):
    return subprocess.check_output(argv,text=True,timeout=120)

def inspect(binaries, r):
    ldc=read(['/sbin/ldconfig','-p']);(r/'ldconfig.log').write_text(ldc);libs={}
    for line in ldc.splitlines():
     m=re.match(r'\s*(\S+)\s+\(([^)]*)\)\s+=>\s+(\S+)',line)
     if m and 'x86-64' in m[2]:libs.setdefault(m[1],m[3])
    queue=[Path(p).resolve() for p in binaries];seen={};root_headers={};issues=[]
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
    return seen
