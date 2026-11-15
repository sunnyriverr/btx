"""Resume final gates on the exact produced archive; no rebuild or repack."""
from pathlib import Path
import os,sys,json,subprocess,shutil,tarfile,traceback
import run as c
W,S,R,F=c.W,c.S,c.R,c.F
c.EXECUTION_LIMIT=900;c.STATE.update(base='f40eb37a6fb8b665340fe92a2f248ff3f23ec7f6',producer_source='f40eb37a6fb8b665340fe92a2f248ff3f23ec7f6',scope='M3 resume audit and relocated offline lifecycle on exact saved archive; no compilation/repack/repeated valid tests')
def main():
 assert shutil.disk_usage(W).free>15*1024**3
 _,head=c.cmd(['git','-C',S,'rev-parse','HEAD'],'package-source',30);assert head.strip()==c.STATE['base']
 original=W/'producer-restore/btx-0.34.16-arm64-apple-darwin.tar.gz';assert original.stat().st_size==46406984 and c.sha(original)=='f1d531d160ac5b5b745dae99466b6ee952976fd163e5fe3574f0a2c4e31a77fa'
 archives=W/'retained';archives.mkdir(exist_ok=True);archive=archives/original.name;shutil.copy2(original,archive)
 c.STATE['archive']={'path':archive.name,'sha256':c.sha(archive),'bytes':archive.stat().st_size,'producer_run':43656330354,'producer_artifact':14137864644,'source_profile':'f40 plus bundle-order and standalone native-module mapping candidates'};c.save()
 c.cmd(['brew','install','--force-bottle','python@3.12'],'producer-absence-control-prerequisite',480)
 _,prefix=c.cmd(['brew','--prefix','python@3.12'],'producer-python-prefix',30);python=Path(prefix.strip())/'bin/python3.12'
 _,base=c.cmd([python,'-c','import sys;print(sys.base_prefix)'],'producer-python-base',30);base=Path(base.strip()).resolve();framework=next(p for p in [base,*base.parents] if p.suffix=='.framework');assert framework.is_relative_to(Path('/opt/homebrew/Cellar/python@3.12'))
 relocated=W/'relocated package with spaces';relocated.mkdir()
 with tarfile.open(archive) as tar:tar.extractall(relocated,filter='data')
 roots=[p for p in relocated.iterdir() if p.is_dir()];assert len(roots)==1;root=roots[0]
 c.cmd([python,F/'archive-audit.py',root,S,R],'all-image-audit-and-integrity-controls',240)
 source_hidden=W/'producer-source-hidden';assert not source_hidden.exists()
 try:
  S.rename(source_hidden)
  c.cmd(['/usr/bin/python3',F/'archive-runtime.py',root,framework,R/'archive-runtime'],'relocated-archive-lifecycle',180)
 finally:
  hidden=framework.with_name(framework.name+'.producer-hidden')
  if hidden.exists() and not framework.exists():hidden.rename(framework)
  if source_hidden.exists() and not S.exists():source_hidden.rename(S)
 assert framework.is_dir() and S.is_dir()
 c.STATE['producer_framework_restored']=True;c.STATE['producer_source_restored']=True
 c.STATE['audit']=json.loads((R/'archive-audit.json').read_text());c.STATE['lifecycle']=json.loads((R/'archive-runtime/lifecycle.json').read_text())
 c.cmd(['git','-C',S,'diff','--exit-code'],'source-unchanged',30)
 c.STATE['complete']=True;c.STATE['btx_compiled']=False;c.save()
try:main()
except Exception as e:c.STATE['error']=str(e);(R/'exception.txt').write_text(traceback.format_exc())
finally:c.save()
sys.exit(0 if c.STATE['complete'] else 1)
