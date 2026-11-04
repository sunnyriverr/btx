from pathlib import Path
import subprocess,json,sys,time,datetime,hashlib
P=Path(__file__).resolve().parent;identity=json.loads((P/'app-identity.json').read_text());app=Path(identity['bundle']);exe=app/'Contents/MacOS/btx-atlas';assert hashlib.sha256(exe.read_bytes()).hexdigest()==identity['binary_sha256']
case=sys.argv[1];cold=case.startswith('cold');uri=('btx:atlas-ls-'+case+'?amount=0.125')if case.endswith('btx')else('btx-p2p://atlas-ls-'+case+'.invalid:8333')
def pids():
 out=subprocess.check_output(['ps','-axo','pid=,command='],text=True);return [int(l.strip().split(None,1)[0])for l in out.splitlines()if l.strip().split(None,1)[-1].startswith(str(exe))]
before=pids();assert (not before)if cold else len(before)==1
cmd=['open','-a',str(app),uri];t=datetime.datetime.now(datetime.timezone.utc).isoformat();s=time.monotonic();r=subprocess.run(cmd,capture_output=True,text=True,timeout=20);time.sleep(2);after=pids();receipt={'case':case,'uri':uri,'cold':cold,'utc':t,'command':cmd,'exit':r.returncode,'elapsed_seconds':time.monotonic()-s,'before_pids':before,'after_pids':after,'binary_sha256':identity['binary_sha256'],'stdout':r.stdout,'stderr':r.stderr};(P/(case+'-launch.json')).write_text(json.dumps(receipt,indent=2));assert r.returncode==0 and len(after)==1;ifwarm=not cold
if ifwarm:assert before==after
print(json.dumps(receipt))
