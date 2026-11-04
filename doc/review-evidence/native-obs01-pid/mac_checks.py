from pathlib import Path
import subprocess,os,json,hashlib,re
P=Path(__file__).resolve().parent;out=P/'mac';out.mkdir(exist_ok=True);results=[]
for name in ['baseline','candidate','wrong']:
 src=P/(name+'-pid-check.cpp');exe=out/(name+'-pid-check');cmd=['clang++','-std=c++20','-O2','-I'+str(P/'include'),str(src),'-o',str(exe)];r=subprocess.run(cmd,capture_output=True);(out/(name+'-build.log')).write_bytes(r.stdout+r.stderr);assert r.returncode==0,(name,r.stderr.decode()[-2000:]);root=out/(name+'-tmp');root.mkdir();env=os.environ.copy();env['TMPDIR']=str(root);log=out/(name+'-run.log')
 with log.open('wb')as f:
  proc=subprocess.Popen([str(exe),str(root)],stdout=f,stderr=subprocess.STDOUT,env=env);rc=proc.wait(timeout=20)
 text=log.read_text();oracle=int(re.search(r'PID oracle=(\d+)',text).group(1));assert oracle==proc.pid
 if name=='wrong':assert rc==1 and 'FAIL PID-derived exact prefix/suffix'in text
 else:assert rc==0 and 'failures=0'in text
 assert not list(root.iterdir()),list(root.iterdir());root.rmdir();results.append({'variant':name,'command':cmd,'exit':rc,'launcher_pid':proc.pid,'observed_pid':oracle,'log':log.name,'log_sha256':hashlib.sha256(log.read_bytes()).hexdigest(),'binary_sha256':hashlib.sha256(exe.read_bytes()).hexdigest(),'result':text.strip(),'fixture_scope':'Extracted actual PID/path/TempTree seam with real util/fs.h, no Obs01 qualification gates'})
(out/'results.json').write_text(json.dumps(results,indent=2)+'\n');print(json.dumps(results,indent=2))
