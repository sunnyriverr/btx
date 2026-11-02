from pathlib import Path
import json,sys,subprocess,time,datetime,hashlib,os
R=Path(__file__).resolve().parent
variant,case=sys.argv[1:3];s=json.loads((R/'state.json').read_text());v=json.loads((R/'variants.json').read_text())[variant]
app=Path(v['app']);assert hashlib.sha256(app.read_bytes()).hexdigest()==v['sha256']
os.kill(v['pid'],0)
uris={'sole':'btx:atlas-guard-sole?amount=0.125','mixed':'btx:atlas-guard-mixed?amount=0.2','file':'btx:atlas-guard-file?amount=0.3','mixed_file':'btx:atlas-guard-mixed-file?amount=0.4'}
f=Path(s['scratch'])/(case+'.btx');f.write_text(uris['mixed_file'] if case=='mixed' else uris['file'])
args=[str(app)]+{'sole':[uris['sole']],'mixed':[uris['mixed'],str(f)],'file':[str(f)],'none':[]}[case]
start=datetime.datetime.now(datetime.timezone.utc).isoformat();t=time.monotonic()
p=subprocess.Popen(args,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
try:out,err=p.communicate(timeout=15)
except subprocess.TimeoutExpired:p.terminate();out,err=p.communicate(timeout=5);raise
alive=True
try:os.kill(v['pid'],0)
except ProcessLookupError:alive=False
record={'variant':variant,'case':case,'start_utc':start,'original_pid':v['pid'],'original_alive_after':alive,'second_pid':p.pid,'exit':p.returncode,'elapsed':time.monotonic()-t,'argv':args,'stdout':out,'stderr':err,'fixture':f.read_text(),'app_sha256':v['sha256']}
(R/(variant+'-'+case+'-launch.json')).write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(record))
assert alive and p.returncode==0
