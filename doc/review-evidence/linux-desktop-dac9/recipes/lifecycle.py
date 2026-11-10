from pathlib import Path
import os,json,subprocess,tarfile,hashlib,signal
w=Path(os.environ['GITHUB_WORKSPACE']);out=w/'lifecycle-records';out.mkdir();runtime=w/'lifecycle-package';runtime.mkdir();a=w/'candidate-input/btx-linux-gui-candidate.tar.gz';p=json.loads((w/'candidate-input/provenance.json').read_text());assert hashlib.sha256(a.read_bytes()).hexdigest()==p['candidate_archive_sha256']
with tarfile.open(a) as t:t.extractall(runtime,filter='data')
root=runtime/'btx-0.34.16'
r=subprocess.Popen(list(map(str,['/usr/bin/python3',Path(__file__).with_name('case.py'),root,out,'current-candidate'])),start_new_session=True)
try:r.wait(timeout=240)
except subprocess.TimeoutExpired:
 os.killpg(r.pid,signal.SIGTERM)
 try:r.wait(timeout=10)
 except subprocess.TimeoutExpired:os.killpg(r.pid,signal.SIGKILL);r.wait()
 raise
assert r.returncode==0
s=json.loads((out/'result.json').read_text());assert s['passed'] and len(s['boots'])==2 and not s['cleanup_signals'] and not s['cleanup_remaining'];print('Packaged helper/guard restart qualification passed')
