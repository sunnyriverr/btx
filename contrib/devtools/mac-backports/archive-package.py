"""Assemble and qualify the actual current-source Mac daemon archive; no compilation."""
from pathlib import Path
import os,sys,json,subprocess,shutil,tarfile,traceback
import run as c
W,S,R,F=c.W,c.S,c.R,c.F
c.EXECUTION_LIMIT=1200;c.STATE.update(base='f40eb37a6fb8b665340fe92a2f248ff3f23ec7f6',producer_source='f40eb37a6fb8b665340fe92a2f248ff3f23ec7f6',scope='M3 actual current-source daemon archive, all-image audit, offline relocated lifecycle; no GUI or release signing')
def main():
 assert shutil.disk_usage(W).free>15*1024**3
 _,head=c.cmd(['git','-C',S,'rev-parse','HEAD'],'package-source',30);assert head.strip()==c.STATE['base']
 payload=W/'producer-restore';manifest=json.loads((payload/'current-executables-manifest.json').read_text());assert manifest['source']==c.STATE['base'];assert manifest['archive_sha256']=='20bf95d29b1d9950546ae0ff6e4694905a7d419be6a8615e990a54e859a91bcc';assert manifest['binaries']['btxd']=='a9d9bc54d745020edf3c3959517f52b84fe7a2373949a2755a8ceabcbb715a8e';assert c.sha(payload/'current-executables.tar.gz')==manifest['archive_sha256']
 inputs=W/'current-inputs';inputs.mkdir()
 expected={'bin/'+name:digest for name,digest in manifest['binaries'].items()};expected.update({'metal/'+name:row['sha256'] for name,row in manifest['metal'].items()})
 with tarfile.open(payload/'current-executables.tar.gz') as tar:
  members=tar.getmembers();assert {m.name for m in members}==set(expected)
  for m in members:
   assert m.isfile() and not Path(m.name).is_absolute() and '..' not in Path(m.name).parts
   p=inputs/m.name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(tar.extractfile(m).read());p.chmod(m.mode);assert c.sha(p)==expected[m.name]
 c.STATE['verified_producer']=manifest;c.save()
 # Test the same maintained regression on stock source and candidate. Native stock
 # assembly failure is retained in run43654912794; do not repeat that execution.
 repair=F/'package-release-candidate.py';tests=F/'package-release-tests.py'
 target=S/'scripts/release/package_release_archive.py';test_target=S/'test/util/package_release_archive_test.py'
 original=target.read_bytes();original_tests=test_target.read_bytes()
 test_target.write_bytes(tests.read_bytes())
 before,log=c.cmd(['/usr/bin/python3',test_target,'PackageReleaseArchiveTest.test_macos_checks_finished_images_after_runtime_bundling'],'order-regression-before',60,check=False)
 assert before!=0 and 'unrelocated producer dependency' in log and 'Ran 1 test' in log
 target.write_bytes(repair.read_bytes())
 c.STATE['repair']={'script_sha256':c.sha(target),'tests_sha256':c.sha(test_target),'baseline_native_run':43654912794};c.save()
 c.cmd(['/usr/bin/python3',test_target,'PackageReleaseArchiveTest.test_macos_checks_finished_images_after_runtime_bundling'],'order-regression-after',60)

 c.cmd(['brew','install','--force-bottle','python@3.12','libomp'],'package-runtime-prerequisites',480)
 _,prefix=c.cmd(['brew','--prefix','python@3.12'],'package-python-prefix',30);python=Path(prefix.strip())/'bin/python3.12'
 c.cmd([python,'-m','venv',W/'package-env'],'package-python-env',60);py=W/'package-env/bin/python';c.cmd([py,'-m','pip','install','cryptography==46.0.4'],'package-python-crypto',180)
 c.cmd([py,test_target],'maintained-package-tests',180)
 c.cmd([py,S/'test/util/bundle_macos_python_runtime_test.py'],'maintained-mac-python-tests',180)
 _,base=c.cmd([py,'-c','import sys;print(sys.base_prefix)'],'package-python-base',30);base=Path(base.strip()).resolve();framework=next(p for p in [base,*base.parents] if p.suffix=='.framework');assert framework.is_relative_to(Path('/opt/homebrew/Cellar/python@3.12'))
 archives=W/'retained';archives.mkdir(exist_ok=True)
 c.cmd([py,S/'scripts/release/package_release_archive.py','--output-dir',archives,'--version','0.34.16','--platform-id','macos-arm64-metal','--btxd',inputs/'bin/btxd','--btx-cli',inputs/'bin/btx-cli','--btx-util',inputs/'bin/btx-util','--require-model-helpers','--metal-lib-dir',inputs/'metal','--source-root',S,'--python',py],'assemble-current-daemon-archive',300)
 found=list(archives.glob('*.tar.gz'));assert len(found)==1;archive=found[0];c.STATE['archive']={'path':archive.name,'sha256':c.sha(archive),'bytes':archive.stat().st_size};c.save()
 relocated=W/'relocated package with spaces';relocated.mkdir()
 with tarfile.open(archive) as tar:tar.extractall(relocated,filter='data')
 roots=[p for p in relocated.iterdir() if p.is_dir()];assert len(roots)==1;root=roots[0]
 c.cmd([py,F/'archive-audit.py',root,S,R],'all-image-audit-and-integrity-controls',240)
 source_hidden=W/'producer-source-hidden'
 assert not source_hidden.exists()
 try:
  S.rename(source_hidden)
  c.cmd(['/usr/bin/python3',F/'archive-runtime.py',root,framework,R/'archive-runtime'],'relocated-archive-lifecycle',180)
 finally:
  hidden=framework.with_name(framework.name+'.producer-hidden')
  if hidden.exists() and not framework.exists():hidden.rename(framework)
  if source_hidden.exists() and not S.exists():source_hidden.rename(S)
 assert framework.is_dir();c.STATE['producer_framework_restored']=True;c.STATE['producer_source_restored']=S.is_dir();assert S.is_dir()
 c.STATE['audit']=json.loads((R/'archive-audit.json').read_text());c.STATE['lifecycle']=json.loads((R/'archive-runtime/lifecycle.json').read_text())
 assert c.sha(target)==c.STATE['repair']['script_sha256'] and c.sha(test_target)==c.STATE['repair']['tests_sha256']
 c.cmd(['git','-C',S,'diff','--stat'],'final-package-source-diff',30)
 target.write_bytes(original);test_target.write_bytes(original_tests)
 c.cmd(['git','-C',S,'diff','--exit-code'],'restored-package-source-unchanged',30)
 c.STATE['complete']=True;c.STATE['btx_compiled']=False;c.save()
try:main()
except Exception as e:c.STATE['error']=str(e);(R/'exception.txt').write_text(traceback.format_exc())
finally:c.save()
sys.exit(0 if c.STATE['complete'] else 1)
