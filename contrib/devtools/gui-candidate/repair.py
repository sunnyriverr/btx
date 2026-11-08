"""Repair archive metadata only; retain explicit gate findings for scoped runtime investigation."""
from pathlib import Path
import os,sys,json,tarfile,hashlib,subprocess
w=Path(os.environ['GITHUB_WORKSPACE']);out=w/'candidate-results';out.mkdir();dst=w/'candidate-output';dst.mkdir();r=w/'repair-runtime';r.mkdir()
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
s=json.loads((w/'prior-records/candidate-results/result.json').read_text());s['prior_fixture']=s['fixture'];s['fixture']=os.environ['GITHUB_SHA'];s.pop('error',None);s['prior_archive_problems']=s['archive_problems'];s['original_candidate_archive_sha256']=s['candidate_archive_sha256']
try:
 old=w/'prior-candidate/btx-linux-gui-candidate.tar.gz';assert sha(old)==s['candidate_archive_sha256']=='07a69d98ee644659fb7efdf1bce40841b6ef5530a5040bd7617abd439363f13d'
 with tarfile.open(old) as t:t.extractall(r,filter='data')
 root=r/'btx-0.34.16'
 actual={str(p.relative_to(root)):{'sha256':sha(p),'mode':p.stat().st_mode&0o777} for p in root.rglob('*') if p.is_file()}
 assert actual==s['candidate_files'],'Candidate changed during artifact/extraction'
 removed=[]
 for p in sorted(root.rglob('*'),key=lambda p:len(p.parts),reverse=True):
  if p.is_dir() and not any(p.iterdir()):removed.append(str(p.relative_to(root)));p.rmdir()
 s['empty_directories_removed']=removed
 a=dst/'btx-linux-gui-candidate.tar.gz'
 def metadata(info):info.uid=info.gid=0;info.uname=info.gname='root';return info
 with tarfile.open(a,'w:gz',compresslevel=1) as t:t.add(root,arcname=root.name,filter=metadata)
 s['candidate_archive_sha256']=sha(a)
 checker=Path(__file__).with_name('verify_release_btxd.py');assert sha(checker)==s['archive_checker_sha256']
 with (out/'archive-gate.log').open('wb') as f:run=subprocess.run([sys.executable,str(checker),'--archive',str(a),'--no-launch','--require-model-helpers'],stdout=f,stderr=subprocess.STDOUT,timeout=180)
 s['gate_exit']=run.returncode;s['archive_problems']=[x for x in (out/'archive-gate.log').read_text().splitlines() if x.startswith('  - ')]
 atlas="  - btx-0.34.16/libexec/btx-atlas.real: RUNPATH $ORIGIN/../lib does not reach btx-0.34.16/lib/qt-private, so the host's libglib-2.0.so.0, libdbus-1.so.3 load instead of the copies this archive ships"
 guard="  - btx-0.34.16/libexec/btx-guardd: no RUNPATH reaches btx-0.34.16/lib, btx-0.34.16/lib/qt-private, so the host's libsqlite3.so.0, libstdc++.so.6, libgcc_s.so.1 load instead of the copies this archive ships"
 assert s['archive_problems']==[atlas,guard] and s['gate_exit']!=0,'Unexpected remaining gate finding'
 s['full_archive_gate_pass']=False;s['only_unchanged_guard_diagnostic']=False
 s['remaining_gate_scope']='Inherited untouched guard plus deliberate Qt-private library isolation. Strict gate remains FAIL. Runtime test investigates actual Atlas host-library resolution; no release waiver.'
 s['gui_observation_allowed']=True;s['assembly_complete']=True;s['archive_metadata_repaired']=True
 (dst/'provenance.json').write_text(json.dumps(s,indent=2)+'\n')
except Exception as e:s['error']=repr(e)
finally:(out/'result.json').write_text(json.dumps(s,indent=2)+'\n')
raise SystemExit(0 if s.get('archive_metadata_repaired') and not s.get('error') else 1)
