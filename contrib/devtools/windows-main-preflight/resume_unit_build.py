from pathlib import Path
import subprocess,time,json,os,hashlib,shutil,re,ctypes
R=Path('D:/btx-native-035');B=R/'project-build';E=R/'unit-plan-evidence';plan=json.loads((E/'result.json').read_text());assert plan['status']=='UNIT_CONFIGURE_DRYRUN_PASS' and plan['source']=='a4d86d123a714956477dbe6a81abf506cd9bd89b';assert plan['units']['steps']<2748,plan['units']['steps']
assert shutil.disk_usage(R).free>8*1024**3
r={'source':plan['source'],'status':'BUILD_RUNNING','planned_steps':plan['units']['steps'],'tests_run':False,'samples':[]};st=time.monotonic();pos=0
class Mem(ctypes.Structure):_fields_=[('length',ctypes.c_ulong),('load',ctypes.c_ulong),('total',ctypes.c_ulonglong),('avail',ctypes.c_ulonglong),('page',ctypes.c_ulonglong),('pageavail',ctypes.c_ulonglong),('virt',ctypes.c_ulonglong),('virtavail',ctypes.c_ulonglong),('ext',ctypes.c_ulonglong)]
def save():(E/'build-result.json').write_text(json.dumps(r,indent=2))
m=Mem();m.length=ctypes.sizeof(m);assert ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m));assert m.avail>8*1024**3,'Need8GiB available before j4';r['admission_memory']=m.avail;r['jobs']=4;r['previous_completed_unit_objects_repeated']=plan['previous_completed_unit_objects_repeated']
with (E/'build.log').open('w') as log:
 p=subprocess.Popen(['ninja','-C',str(B),'-j4','test_btx'],stdout=log,stderr=subprocess.STDOUT)
 try:
  while p.poll() is None:
   time.sleep(15);elapsed=time.monotonic()-st;m=Mem();m.length=ctypes.sizeof(m);assert ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m));free=shutil.disk_usage(R).free;r['samples'].append({'seconds':round(elapsed),'disk_free':free,'memory_available':m.avail});save()
   with (E/'build.log').open() as f:f.seek(pos);new=f.read();pos=f.tell()
   print(new,flush=True);print('Resource sample:',r['samples'][-1],flush=True)
   if elapsed>1800 or free<1342177280 or m.avail<512*1024**2:
    r['stop_reason']='time_budget' if elapsed>1800 else 'resource_reserve';subprocess.run(['taskkill','/PID',str(p.pid),'/T','/F']);p.wait();break
 finally:
  if p.poll() is None:subprocess.run(['taskkill','/PID',str(p.pid),'/T','/F']);p.wait()
r['exit']=p.returncode;r['seconds']=round(time.monotonic()-st,2);text=(E/'build.log').read_text(errors='replace');r['status']='UNIT_LINK_PASS' if p.returncode==0 else 'UNIT_BUILD_INCOMPLETE';r['first_errors']=[l for l in text.splitlines() if 'error:' in l or 'fatal error' in l or l.startswith('FAILED:')][:8];r['last_progress']=re.findall(r'\[\d+/\d+\][^\n]*',text)[-5:];save()
if p.returncode==0:
 exe=B/'bin/test_btx.exe';r['test_btx_sha256']=hashlib.sha256(exe.read_bytes()).hexdigest();save()
 try:
  inventory=subprocess.run([str(exe),'--list_content=HRF'],cwd=B,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=90);(E/'unit-inventory.log').write_bytes(inventory.stdout);r['inventory_exit']=inventory.returncode;r['inventory_bytes']=len(inventory.stdout);r['inventory_sha256']=hashlib.sha256(inventory.stdout).hexdigest()
 except subprocess.TimeoutExpired as e:r['inventory_timeout']=True;(E/'unit-inventory.log').write_bytes(e.stdout or b'')
 save()
print(json.dumps(r,indent=2),flush=True)
raise SystemExit(0 if p.returncode==0 else 1)
