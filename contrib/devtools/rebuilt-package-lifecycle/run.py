"""Qualify the untouched rebuilt archive using the existing positive case."""
from pathlib import Path
import hashlib, json, os, shutil, subprocess, sys, tarfile, urllib.request

W = Path(os.environ['GITHUB_WORKSPACE'])
P = W / 'product'
H = Path(__file__).parent
O = W / 'rebuilt-package-results'
O.mkdir()
EXPECTED = '796b9edd064272b1f443cf3e08646565936183f9f1e15339cad60e84e1014b32'
BASE = '2f3b574867c11ab79eba829123689b76e6137a38'
s = {'source_mapping': BASE, 'fixture': os.environ['GITHUB_SHA'], 'qualified': False,
     'overlay': False, 'source_build': False, 'manual_helper_or_guard': False}
def sha(p):
    h = hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda: f.read(1024*1024), b''): h.update(b)
    return h.hexdigest()
try:
    assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=P,text=True).strip()==BASE
    assert not subprocess.check_output(['git','status','--porcelain'],cwd=P)
    assert shutil.disk_usage(W).free > 3*1024**3
    archive = W/'rebuilt-official.tar.gz'
    with urllib.request.urlopen('https://github.com/btxchain/btx/releases/download/v0.34.16/btx-0.34.16-x86_64-linux-gnu.tar.gz',timeout=60) as r, archive.open('wb') as f:
        shutil.copyfileobj(r,f)
    assert sha(archive)==EXPECTED and archive.stat().st_size==158893566
    s['archive']={'asset_id':721231861,'sha256':EXPECTED,'bytes':archive.stat().st_size}
    dest=W/'rebuilt-official-installation';dest.mkdir()
    with tarfile.open(archive) as t:
        assert sum(m.size for m in t.getmembers()) < 2*1024**3
        t.extractall(dest,filter='data')
    archive.unlink()
    candidates=list(dest.rglob('bin/btxd'));assert len(candidates)==1
    package=candidates[0].parent.parent.resolve()
    before={str(f.relative_to(package)):sha(f) for f in package.rglob('*') if f.is_file()}
    guard=package/'libexec/btx-guardd'
    assert guard.is_file() and not guard.is_symlink() and os.access(guard,os.X_OK)
    assert guard.samefile(package/'libexec/btx-guardd.real')
    s['package_files_before']=before;s['guard_is_regular_executable_hardlink']=True
    s['case_sha256']=sha(H/'case.py')
    with (O/'case.log').open('wb') as log:
        r=subprocess.run([sys.executable,H/'case.py',package,O/'case','untouched'],env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1'),stdout=log,stderr=subprocess.STDOUT,timeout=180)
    s['case_exit']=r.returncode
    result=json.loads((O/'case/result.json').read_text())
    s['case_pass']=result['passed']
    assert r.returncode==0 and result['passed'] and result['guard_contract_pass']
    assert len(result['boots'])==2 and all(len(b['health'])==10 and len(b['guard_health'])==10 for b in result['boots'])
    assert all(x['pass'] for x in result['checks'])
    assert not result['cleanup_before'] and not result['cleanup_remaining'] and not result['cleanup_signals'] and result['runtime_removed']
    after={str(f.relative_to(package)):sha(f) for f in package.rglob('*') if f.is_file()}
    assert before==after==result['package_files_before']==result['package_files_after']
    assert not subprocess.check_output(['git','status','--porcelain'],cwd=P)
    s['package_files_after']=after;s['qualified']=True
except Exception as e:
    s['error']=repr(e)
    raise
finally:
    (O/'result.json').write_text(json.dumps(s,indent=2)+'\n')
assert s['qualified']
