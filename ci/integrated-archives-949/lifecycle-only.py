"""Finish only the missing producer-hidden lifecycle on the audited archive."""
from pathlib import Path
import json
import shutil
import sys
import tarfile
import traceback
import run as c
from archive_restore import restore

W,S,R,F=c.W,c.S,c.R,c.F
HEAD='949a98e34222cc4cdb5b1d5bd650aa3b7bcbff72'
c.EXECUTION_LIMIT=900
c.STATE.update(base=HEAD,producer_source=HEAD,scope='Only missing producer-hidden lifecycle on unchanged audited949archive',btx_compiled=False,reused_archive_audit_run=43679857514)

def main():
    assert shutil.disk_usage(W).free>15*1024**3
    _,head=c.cmd(['git','-C',S,'rev-parse','HEAD'],'source',30)
    assert head.strip()==HEAD
    archive=restore()
    c.cmd(['brew','install','--force-bottle','python@3.12'],'framework-prerequisite',300)
    _,prefix=c.cmd(['brew','--prefix','python@3.12'],'python-prefix',30)
    python=Path(prefix.strip())/'bin/python3.12'
    _,base=c.cmd([python,'-c','import sys;print(sys.base_prefix)'],'producer-framework-prefix',30)
    base=Path(base.strip()).resolve()
    framework=next(path for path in [base,*base.parents] if path.suffix=='.framework')
    assert framework.is_relative_to(Path('/opt/homebrew/Cellar/python@3.12'))
    assert framework.is_dir()
    relocated=W/'relocated current archive with spaces'
    relocated.mkdir()
    with tarfile.open(archive) as handle:
        handle.extractall(relocated,filter='data')
    roots=[path for path in relocated.iterdir() if path.is_dir()]
    assert len(roots)==1
    root=roots[0]
    allowed=['lib/Python.framework/Versions/3.12/Resources/Python.app']
    assert sorted(str(path.relative_to(root)) for path in root.rglob('*.app'))==allowed
    # These same bytes already passed the full archive and86image audit.
    # The existing lifecycle utility hides/restores the disposable framework.
    hidden_source=W/'producer-source-hidden'
    hidden_framework=framework.with_name(framework.name+'.producer-hidden')
    assert not hidden_source.exists() and not hidden_framework.exists()
    try:
        S.rename(hidden_source)
        c.cmd(['/usr/bin/python3',F/'archive-runtime.py',root,framework,R/'archive-runtime'],'producer-hidden-lifecycle',180)
    finally:
        if hidden_framework.exists() and not framework.exists():
            hidden_framework.rename(framework)
        if hidden_source.exists() and not S.exists():
            hidden_source.rename(S)
    assert framework.is_dir() and S.is_dir()
    c.STATE['producer_restored']=True
    c.STATE['lifecycle']=json.loads((R/'archive-runtime/lifecycle.json').read_text())
    _,dirty=c.cmd(['git','-C',S,'status','--porcelain'],'final-source-status',30)
    assert not dirty
    c.STATE['complete']=True
    c.save()

try:
    main()
except Exception as error:
    c.STATE['error']=str(error)
    (R/'exception.txt').write_text(traceback.format_exc())
finally:
    c.save()
sys.exit(0 if c.STATE['complete'] else 1)
