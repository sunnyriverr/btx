from pathlib import Path
import subprocess,json,hashlib,resource,time,shutil,os
r=Path(__file__).resolve().parent;b=r/'build';results=[]
expected=b'native-memory-probe-ok\n'
for cap in [128,64]:
 for mb in [8,96]:
  for n in range(1,4):
   case=r/f'case-cap{cap}-probe{mb}-{n}';case.mkdir();root=case/'package';root.mkdir();shutil.copy2(b/f'probe{mb}',root/'probe')
   exe=(root/'probe').read_bytes();request={'probe':{'root':str(root),'executable':'probe','files':[{'path':'probe','sha384':hashlib.sha384(exe).hexdigest(),'bytes':len(exe)}],'output_relative_path':'result.txt','expected_output_sha384':hashlib.sha384(expected).hexdigest(),'expected_output_bytes':len(expected),'max_package_bytes':2*1024*1024,'wall_seconds':4}}
   req=case/'request.json';req.write_text(json.dumps(request))
   def limits():resource.setrlimit(resource.RLIMIT_AS,(cap*1024**2,cap*1024**2));resource.setrlimit(resource.RLIMIT_CPU,(6,6))
   t=time.monotonic();p=subprocess.run([str(b/'btx-native-qualify'),'tool',str(req)],preexec_fn=limits,capture_output=True,text=True,timeout=10)
   try:obj=json.loads(p.stdout)
   except Exception:obj={'unparsed_stdout':p.stdout}
   row={'address_cap_mib':cap,'probe_resident_mib':mb,'run':n,'elapsed_s':time.monotonic()-t,'returncode':p.returncode,'result':obj,'stderr':p.stderr,'output_exists':(root/'result.txt').exists()}
   (case/'result.json').write_text(json.dumps(row,indent=2)+'\n');results.append(row);print(json.dumps(row),flush=True)
   if cap==64 and mb==96:assert p.returncode==2 and obj.get('error')=='NATIVE_TOOL_EXIT' and not row['output_exists'],row
   else:assert p.returncode==0 and obj['success'] and obj['module_passed'] and (root/'result.txt').read_bytes()==expected,row
(r/'results.json').write_text(json.dumps(results,indent=2)+'\n')
(r/'guest-identity.json').write_text(json.dumps({'uname':subprocess.check_output(['uname','-a'],text=True),'compiler':subprocess.check_output(['c++','--version'],text=True),'uid':os.getuid(),'memory':Path('/proc/meminfo').read_text(),'binaries':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in [b/'btx-native-qualify',b/'probe8',b/'probe96']}},indent=2)+'\n')
print('FINAL',len(results),'cases matched expected outcome')
