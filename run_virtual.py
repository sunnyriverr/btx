"""Bounded execution driver, prepared only. Compile separately after review."""
import hashlib,json,os,pathlib,resource,subprocess,sys,time
from validate_virtual import validate
p=pathlib.Path(__file__).resolve().parent
# Require the extracted method to be unchanged from traced production source.
identity=json.loads((p/'extraction.json').read_text())
assert hashlib.sha256((p/'putstream.inc').read_bytes()).hexdigest()==identity['method_sha256']
exe=pathlib.Path(sys.argv[1]).resolve()
assert exe.is_file()
def limits():
 resource.setrlimit(resource.RLIMIT_AS,(256*1024**2,256*1024**2))
 resource.setrlimit(resource.RLIMIT_CPU,(110,110))
 resource.setrlimit(resource.RLIMIT_FSIZE,(1024**2,1024**2))
out={'status':'INCOMPLETE','binary_sha256':hashlib.sha256(exe.read_bytes()).hexdigest(),'method_sha256':identity['method_sha256'],'logical_cap_bytes':83886080000,'network':False}
start=time.monotonic()
try:
 r=subprocess.run([str(exe)],capture_output=True,text=True,timeout=120,preexec_fn=limits)
 (p/'virtual-observations.jsonl').write_text(r.stdout);(p/'virtual-stderr.txt').write_text(r.stderr)
 out['returncode']=r.returncode;assert r.returncode==0
 rows=[json.loads(x) for x in r.stdout.splitlines()];validate(rows)
 out['status']='EXPECTED_BASELINE_OBSERVATIONS_VERIFIED'
except Exception as e:
 out['status']='FAIL_OR_BLOCKED';out['error']=str(e)
 if isinstance(e,subprocess.TimeoutExpired):
  (p/'virtual-partial-stdout.txt').write_bytes(e.stdout or b'')
 raise
finally:
 out['elapsed_seconds']=time.monotonic()-start
 (p/'virtual-execution.json').write_text(json.dumps(out,indent=2)+'\n')
