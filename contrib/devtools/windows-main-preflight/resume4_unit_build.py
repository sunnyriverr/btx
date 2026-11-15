from pathlib import Path
import json,subprocess,time,shutil,ctypes,re,hashlib
R=Path('D:/btx-native-035');B=R/'project-build';E=R/'unit-plan-evidence';plan=json.loads((E/'result.json').read_text());assert plan['status']=='UNIT_CONFIGURE_DRYRUN_PASS'
r={'source':plan['source'],'source_patch':'746guard','status':'BUILD_RUNNING','tests_run':False,'jobs':4,'phases':[],'samples':[]};start=time.monotonic();logpath=E/'build.log';pos=0
class Mem(ctypes.Structure):_fields_=[('length',ctypes.c_ulong),('load',ctypes.c_ulong),('total',ctypes.c_ulonglong),('avail',ctypes.c_ulonglong),('page',ctypes.c_ulonglong),('pageavail',ctypes.c_ulonglong),('virt',ctypes.c_ulonglong),('virtavail',ctypes.c_ulonglong),('ext',ctypes.c_ulonglong)]
def memory():
 m=Mem();m.length=ctypes.sizeof(m);assert ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m));return m.avail
def save():(E/'build-result.json').write_text(json.dumps(r,indent=2)+'\n')
assert memory()>8*1024**3 and shutil.disk_usage(R).free>8*1024**3
try:
 for name,targets in [('previously-unbuilt-objects',plan['unrun_unit_object_targets']),('complete-unit-target',['test_btx'])]:
  if not targets:continue
  phase={'name':name,'targets':len(targets),'started_seconds':round(time.monotonic()-start,2)};r['phases'].append(phase);save()
  with logpath.open('a') as log:
   log.write('\nPHASE '+name+'\n');log.flush();p=subprocess.Popen(['ninja','-C',str(B),'-j4']+targets,stdout=log,stderr=subprocess.STDOUT)
   try:
    while p.poll() is None:
     time.sleep(15);elapsed=time.monotonic()-start;free=shutil.disk_usage(R).free;ram=memory();r['samples'].append({'seconds':round(elapsed),'disk_free':free,'memory_available':ram});save()
     with logpath.open() as f:f.seek(pos);text=f.read();pos=f.tell()
     print(text,flush=True);print('Resource sample',r['samples'][-1],flush=True)
     if elapsed>1800 or free<1342177280 or ram<512*1024**2:
      r['stop_reason']='time_budget' if elapsed>1800 else 'resource_reserve';subprocess.run(['taskkill','/PID',str(p.pid),'/T','/F']);p.wait();break
   finally:
    if p.poll() is None:subprocess.run(['taskkill','/PID',str(p.pid),'/T','/F']);p.wait()
  phase['exit']=p.returncode;phase['finished_seconds']=round(time.monotonic()-start,2);save()
  if p.returncode!=0:break
 r['exit']=p.returncode;r['seconds']=round(time.monotonic()-start,2);r['status']='UNIT_LINK_PASS' if p.returncode==0 and r['phases'][-1]['name']=='complete-unit-target' else 'UNIT_BUILD_INCOMPLETE'
 text=logpath.read_text(errors='replace');r['first_errors']=[l for l in text.splitlines() if 'error:' in l or 'fatal error' in l or l.startswith('FAILED:')][:12];r['last_progress']=re.findall(r'\[\d+/\d+\][^\n]*',text)[-6:]
 if r['status']=='UNIT_LINK_PASS':
  exe=B/'bin/test_btx.exe';r['test_btx_sha256']=hashlib.sha256(exe.read_bytes()).hexdigest()
  try:
   inv=subprocess.run([str(exe),'--list_content=HRF'],cwd=B,capture_output=True,timeout=90);raw=inv.stdout+inv.stderr;(E/'unit-inventory.log').write_bytes(raw);r['inventory_exit']=inv.returncode;r['inventory_sha256']=hashlib.sha256(raw).hexdigest();r['inventory_bytes']=len(raw)
  except subprocess.TimeoutExpired as e:r['inventory_timeout']=True;(E/'unit-inventory.log').write_bytes(e.stdout or b'')
finally:save()
print(json.dumps({k:v for k,v in r.items() if k!='samples'},indent=2),flush=True)
raise SystemExit(0 if r['status']=='UNIT_LINK_PASS' else 1)
