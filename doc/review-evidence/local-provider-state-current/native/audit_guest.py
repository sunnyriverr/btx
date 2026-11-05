from pathlib import Path
import subprocess,json,sys
sys.path.insert(0,'work/btx-review-tools/lan-linux-native');from vm import vm
S=Path('work/btx-lanes/session-2/mlkem-peer-key-validation/source');P=Path(__file__).resolve().parent
rows=subprocess.check_output(['git','ls-tree','-rz','--full-tree',sys.argv[1] if len(sys.argv)>1 else '666673a3153225ba264c7870e0e82e354df86765'],cwd=S).split(b'\0');expected={}
for row in rows:
 if row:
  meta,name=row.split(b'\t',1);mode,kind,sha=meta.decode().split();
  if kind=='blob':expected[name.decode()]=sha
code='''from pathlib import Path
import json,sys,hashlib,os
root=Path('/tmp/btx-session2-helper-restart-current/source');expected=json.load(sys.stdin);bad=[];absent=[]
for name,want in expected.items():
 p=root/name
 if not p.is_file():absent.append(name);continue
 data=os.readlink(p).encode() if p.is_symlink() else p.read_bytes();got=hashlib.sha1(b'blob '+str(len(data)).encode()+b'\\0'+data).hexdigest()
 if got!=want:bad.append(name)
print(json.dumps(dict(mismatches=bad,missing=absent,checked=len(expected)),indent=2))
'''
z=vm(['python3','-c',code],input=json.dumps(expected).encode(),capture_output=True,timeout=60,check=True);(P/'guest-source-audit.json').write_bytes(z.stdout);r=json.loads(z.stdout);print('checked',r['checked'],'mismatches',r['mismatches'],'missing',len(r['missing']));print('missing first',r['missing'][:20])
