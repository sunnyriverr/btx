from pathlib import Path
import hashlib,json,subprocess,time,resource
p=Path.cwd();out=p/'records';out.mkdir(exist_ok=True)
C=8<<20;B=C*10000;L=400<<30
expected={
'known_over':(False,10000,B,B,1,0,C), 'known_exact':(True,10000,B,B,0,1,C),
'unknown_exact':(False,10000,B,B,1,0,C),'unknown_over':(False,10000,B,B,1,0,C),
'normal_two_parts':(True,2,2*C,2*C,0,1,C),'short_read':(False,1,C,C,1,0,C),
'backend_failure':(False,2,2*C,2*C,1,0,C),'normal_direct':(True,0,1024,1024,0,0,1024),
'large_400GiB':(False,10000,B,B,1,0,C),'maximum_plus_one':(False,10000,B,B,1,0,C),'uint64_max':(False,10000,B,B,1,0,C)}
def limits():
 resource.setrlimit(resource.RLIMIT_AS,(256<<20,256<<20));resource.setrlimit(resource.RLIMIT_CPU,(110,110));resource.setrlimit(resource.RLIMIT_FSIZE,(1<<20,1<<20))
r={'status':'INCOMPLETE','cases':11,'variants':{},'network':False}
try:
 for variant in ('baseline','candidate'):
  command=['g++','-std=c++20','-O2','-Wall','-Wextra','-Werror','virtual_stream.cpp','-o',variant+'-component']
  if variant=='candidate':command.insert(1,'-DCANDIDATE')
  c=subprocess.run(command,capture_output=True,text=True,timeout=60);(out/(variant+'-compile.log')).write_text(c.stdout+c.stderr);assert c.returncode==0
  start=time.monotonic();x=subprocess.run([str(p/(variant+'-component'))],capture_output=True,text=True,timeout=120,preexec_fn=limits)
  (out/(variant+'-observations.jsonl')).write_text(x.stdout);(out/(variant+'-stderr.txt')).write_text(x.stderr);assert x.returncode==0
  rows=[json.loads(l) for l in x.stdout.splitlines()];assert len(rows)==11 and len({x['case'] for x in rows})==11
  for row in rows:
   assert row['fake'] is False and row['branch']=='live-adapted'
   expect=expected[row['case']]
   if variant=='candidate':
    if row['case']=='known_over':expect=(True,5001,B+1,B+1,0,1,2*C)
    if row['case']=='large_400GiB':expect=(True,6400,L,L,0,1,8*C)
    if row['case'] in ('maximum_plus_one','uint64_max'):expect=(False,0,0,0,0,0,0)
   assert tuple(row[k] for k in ('ok','parts','bytes','consumed','aborts','completes','max_buffer'))==expect,row
   assert row['begins']==(0 if row['case']=='normal_direct' or (variant=='candidate' and row['case'] in ('maximum_plus_one','uint64_max')) else 1)
   assert row['direct']==(1 if row['case']=='normal_direct' else 0)
   if variant=='candidate' and row['case'] in ('maximum_plus_one','uint64_max'):assert row['error']=='s3 https multipart upload exceeds bounded capacity'
   if row['ok']:assert not row['error']
  r['variants'][variant]={'returncode':x.returncode,'seconds':time.monotonic()-start,'binary_sha256':hashlib.sha256((p/(variant+'-component')).read_bytes()).hexdigest(),'method_sha256':hashlib.sha256((p/(variant+'-putstream.inc')).read_bytes()).hexdigest(),'all11_cases_verified':True}
 r['status']='PASS'
finally:(out/'component-result.json').write_text(json.dumps(r,indent=2)+'\n')
